from iconservice import * 

TAG = 'stablecoin'

# An interface of ICON Token Standard, IRC-2
class TokenStandard(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def symbol(self) -> str:
        pass

    @abstractmethod
    def decimals(self) -> int:
        pass

    @abstractmethod
    def totalSupply(self) -> int:
        pass

    @abstractmethod
    def balanceOf(self, _owner: Address) -> int:
        pass

    @abstractmethod
    def transfer(self, _to: Address, _value: int, _data: bytes = None):
        pass
        
# An interface of tokenFallback.
# Receiving SCORE that has implemented this interface can handle
# the receiving or further routine.
class TokenFallbackInterface(InterfaceScore):
    @interface
    def tokenFallback(self, _from: Address, _value: int, _data: bytes):
        pass

class stablecoin(IconScoreBase):

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._total_supply = VarDB('total_supply', db, value_type=int)
        self._decimals = VarDB('decimals', db, value_type=int)
        self._balances = DictDB('balances', db, value_type=int)

    def on_install(self, _initialSupply: int, _decimals: int) -> None:
        super().on_install()
        if _initialSupply < 0:
            revert("Initial supply cannot be less than zero")

        if _decimals < 0:
            revert("Decimals cannot be less than zero")
        
        total_supply = _initialSupply * 10 ** _decimals
        self._total_supply.set(total_supply)
        self._decimals.set(_decimals)
        self._balances[self.msg.sender] = total_supply

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def name(self) -> str:
        return 'MY TOKEN'

    @external(readonly=True)
    def symbol(self) -> str:
        return 'MYT'
    
    @external(readonly=True)
    def decimals(self) -> int:
        return self._decimals.get()

    @external(readonly=True)
    def totalSupply(self) -> int:
        return self._total_supply.get()

    @external(readonly=True)
    def balanceOf(self, _owner: Address) -> int:
        return self._balances[_owner]
    
    @external
    def transfer(self, _to: Address, _value: int, _data: bytes = None):
        if _data is None:
            _data = b'None'
        self._transfer(self.msg.sender, _to, _value, _data)
    
    def ownerCheck(func):
        @wraps(func)
        def __wrapper(self, *args, **kwargs):
            if(self.msg.sender != self.owner):
                revert(f"You have to be the creator to interact with this contract.. You tried with {self.msg.sender}")
            else:
                return func(self,*args, **kwargs)
        return __wrapper

    @eventlog(indexed=1)
    def Mint(self,  _amount: int):
        pass

    @external
    @ownerCheck 
    def mint(self, _amount: int) -> None:
        self._total_supply.set(self._total_supply.get() + _amount)
        self._balances[self.msg.sender] += _amount
        self.Mint(_amount)
        Logger.debug(f'Minted ({_amount}, to treasury ({self.msg.sender},) ', TAG)
    
    @eventlog(indexed=1)
    def Burn(self,  _amount: int):
        pass

    @external
    @ownerCheck 
    def burn(self, _amount: int) -> None:
        self._total_supply.set(self._total_supply.get() - _amount)
        self._balances[self.msg.sender] -= _amount
        self.Burn(_amount)
        Logger.debug(f'Burned ({_amount}, from treasury ({self.msg.sender},) ', TAG)

    def _transfer(self, _from: Address, _to: Address, _value: int, _data: bytes):
        if _value < 0:
           revert("Transferring value cannot be less than zero")
           
        if self._balances[_from] < _value:
           revert("Out of balance")

        self._balances[_from] = self._balances[_from] - _value
        self._balances[_to] = self._balances[_to] + _value

        if _to.is_contract:
           recipient_score = self.create_interface_score(_to, TokenFallbackInterface)		              
           recipient_score.tokenFallback(_from, _value, _data)

        self.Transfer(_from, _to, _value, _data)
        Logger.debug(f'Transfer({_from}, {_to}, {_value}, {_data})', TAG)