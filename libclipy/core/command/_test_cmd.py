import pytest
from .cmd import _Conditions

def test_condtion_parse():
    ''' unit test _Conditions.parse
    '''
    c = _Conditions()
    with pytest.raises(ValueError):
        c.parse(0, 'bob,cob,x', None)


@pytest.mark.skip('implement')
def test_stdin():
    ''' Simple write to stdin works correctly
    '''
    pass


@pytest.mark.skip('implement')
def test_stdin_close():
    ''' The subprocess closed while we are still trying to write to it.
    '''
    pass


@pytest.mark.skip('implement')
def test_env():
    ''' .env() and .env_set() work correctly
    '''
    pass
