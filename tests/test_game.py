"""Tests for boardbox.game."""
from datetime import datetime
from boardbox.game import Game, MechanicStub, MechanicStub, GameCatalog, parse_iso
from tests.helpers import make_game, make_mechanic, make_mechanic

def test_to_from_dict():
    r = make_game()
    r2 = Game.from_dict(r.to_dict())
    assert r2.title == r.title

def test_mechanic_names():
    assert make_game().mechanic_names()

def test_game_book():
    r = make_game()
    book = GameCatalog([r])
    assert book.get(r.id) is r

def test_parse_iso_z():
    dt = parse_iso('2020-01-01T00:00:00Z')
    assert isinstance(dt, datetime)

def test_game_roundtrip_0():
    r = make_game(title='T0')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_1():
    r = make_game(title='T1')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_2():
    r = make_game(title='T2')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_3():
    r = make_game(title='T3')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_4():
    r = make_game(title='T4')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_5():
    r = make_game(title='T5')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_6():
    r = make_game(title='T6')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_7():
    r = make_game(title='T7')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_8():
    r = make_game(title='T8')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_9():
    r = make_game(title='T9')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_10():
    r = make_game(title='T10')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_11():
    r = make_game(title='T11')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_12():
    r = make_game(title='T12')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_13():
    r = make_game(title='T13')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_14():
    r = make_game(title='T14')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_15():
    r = make_game(title='T15')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_16():
    r = make_game(title='T16')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_17():
    r = make_game(title='T17')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_18():
    r = make_game(title='T18')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_19():
    r = make_game(title='T19')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_20():
    r = make_game(title='T20')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_21():
    r = make_game(title='T21')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_22():
    r = make_game(title='T22')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_23():
    r = make_game(title='T23')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_24():
    r = make_game(title='T24')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_25():
    r = make_game(title='T25')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_26():
    r = make_game(title='T26')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_27():
    r = make_game(title='T27')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_28():
    r = make_game(title='T28')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_29():
    r = make_game(title='T29')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_30():
    r = make_game(title='T30')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_31():
    r = make_game(title='T31')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_32():
    r = make_game(title='T32')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_33():
    r = make_game(title='T33')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_34():
    r = make_game(title='T34')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_35():
    r = make_game(title='T35')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_36():
    r = make_game(title='T36')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_37():
    r = make_game(title='T37')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_38():
    r = make_game(title='T38')
    assert Game.from_dict(r.to_dict()).id == r.id

def test_game_roundtrip_39():
    r = make_game(title='T39')
    assert Game.from_dict(r.to_dict()).id == r.id

