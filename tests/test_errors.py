"""Tests for boardbox.errors."""
import pytest
from boardbox.errors import *

def test_boardboxerror_0():
    exc = BoardboxError('x')
    assert exc.code == 'BOARDBOX_ERROR'
    assert str(exc)

def test_storageerror_1():
    exc = StorageError('fail', path='/p')
    assert exc.code == 'STORAGE_ERROR'
    assert str(exc)

def test_validationerror_2():
    exc = ValidationError('bad', field='title')
    assert exc.code == 'VALIDATION_ERROR'
    assert str(exc)

def test_notfounderror_3():
    exc = NotFoundError('game', 'id1')
    assert exc.code == 'NOT_FOUND'
    assert str(exc)

def test_importpipelineerror_4():
    exc = ImportPipelineError('csv', 'row')
    assert exc.code == 'IMPORT_ERROR'
    assert str(exc)

def test_exporterror_5():
    exc = ExportError('out.csv', 'disk')
    assert exc.code == 'EXPORT_ERROR'
    assert str(exc)

def test_migrationerror_6():
    exc = MigrationError(0, 1, 'bad')
    assert exc.code == 'MIGRATION_ERROR'
    assert str(exc)

def test_conflicterror_7():
    exc = ConflictError('dup', key='k')
    assert exc.code == 'CONFLICT'
    assert str(exc)

def test_parseerror_8():
    exc = ParseError('parse', raw='1x')
    assert exc.code == 'PARSE_ERROR'
    assert str(exc)

def test_conversionerror_9():
    exc = ConversionError('cup', 'g')
    assert exc.code == 'CONVERSION_ERROR'
    assert str(exc)

def test_duplicateerror_10():
    exc = DuplicateError('tag', 'quick')
    assert exc.code == 'DUPLICATE_ERROR'
    assert str(exc)

def test_mealplanerror_11():
    exc = SessionLogError('slot', day='Mon')
    assert exc.code == 'MEAL_PLAN_ERROR'
    assert str(exc)

def test_wishlistlisterror_12():
    exc = WishlistError('merge')
    assert exc.code == 'WANT_LIST_ERROR'
    assert str(exc)

def test_is_not_found_true():
    assert is_not_found(NotFoundError('r', '1'))

def test_is_not_found_false():
    assert not is_not_found(ValueError('n'))

def test_format_error():
    exc = ValidationError('x', field='t')
    assert 'VALIDATION_ERROR' in format_error(exc)

def test_import_pipeline_error_helper():
    exc = import_pipeline_error('csv', 3, 'bad')
    assert 'line 3' in str(exc)

def test_format_roundtrip_0():
    exc = BoardboxError('msg0', code='C0')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_1():
    exc = BoardboxError('msg1', code='C1')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_2():
    exc = BoardboxError('msg2', code='C2')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_3():
    exc = BoardboxError('msg3', code='C3')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_4():
    exc = BoardboxError('msg4', code='C4')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_5():
    exc = BoardboxError('msg5', code='C0')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_6():
    exc = BoardboxError('msg6', code='C1')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_7():
    exc = BoardboxError('msg7', code='C2')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_8():
    exc = BoardboxError('msg8', code='C3')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_9():
    exc = BoardboxError('msg9', code='C4')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_10():
    exc = BoardboxError('msg10', code='C0')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_11():
    exc = BoardboxError('msg11', code='C1')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_12():
    exc = BoardboxError('msg12', code='C2')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_13():
    exc = BoardboxError('msg13', code='C3')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_14():
    exc = BoardboxError('msg14', code='C4')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_15():
    exc = BoardboxError('msg15', code='C0')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_16():
    exc = BoardboxError('msg16', code='C1')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_17():
    exc = BoardboxError('msg17', code='C2')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_18():
    exc = BoardboxError('msg18', code='C3')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_19():
    exc = BoardboxError('msg19', code='C4')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_20():
    exc = BoardboxError('msg20', code='C0')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_21():
    exc = BoardboxError('msg21', code='C1')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_22():
    exc = BoardboxError('msg22', code='C2')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_23():
    exc = BoardboxError('msg23', code='C3')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_24():
    exc = BoardboxError('msg24', code='C4')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_25():
    exc = BoardboxError('msg25', code='C0')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_26():
    exc = BoardboxError('msg26', code='C1')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_27():
    exc = BoardboxError('msg27', code='C2')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_28():
    exc = BoardboxError('msg28', code='C3')
    assert format_error(exc).startswith('C')

def test_format_roundtrip_29():
    exc = BoardboxError('msg29', code='C4')
    assert format_error(exc).startswith('C')

