#!/bin/env python3

import dragoman

def get_type_name (t: dragoman.DefinedType) -> str:
	if isinstance(t, dragoman.ObjectType):
		return "#" + t.get_name().lower() + "{}"
	else:
		return t.get_name().lower() + "()"

def entry_name_converter (s: str) -> str:
	return s.lower()

def add_record (
	cw: dragoman.CodeWriter,
	object_type: dragoman.ObjectType
):
	cw.line("-record")
	cw.line("(")
	cw.increase_indent()
	cw.line(object_type.get_name().lower() + ",")
	cw.line("{")
	cw.increase_indent()

	for e in object_type.get_entries():
		cw.start_line(entry_name_converter(e.get_name()))
		cw.append(" :: ")
		cw.append(get_type_name(e.get_type()))
		cw.set_buffer(",")
		cw.mark_buffer_as_ending_line()

	cw.discard_buffer()
	cw.newline()
	cw.decrease_indent()
	cw.line("}")
	cw.decrease_indent()
	cw.line(").")
	cw.newline()

def add_enum_type (
	cw: dragoman.CodeWriter,
	enum_type: dragoman.EnumType
):
	cw.start_line("-type ")
	cw.append(get_type_name(enum_type))
	cw.append(" :: ")

	for e in enum_type.get_entries():
		cw.append("'")
		cw.append(entry_name_converter(e.get_name()))
		cw.append("'")
		cw.set_buffer(" | ")

	cw.discard_buffer()
	cw.append(".")
	cw.newline()
	cw.newline()

def add_polymorph_type (
	cw: dragoman.CodeWriter,
	polymorph_type: dragoman.PolymorphType
):
	cw.start_line("-type ")
	cw.append(get_type_name(polymorph_type))
	cw.append(" :: ")

	for e in polymorph_type.get_cases().values():
		cw.append(get_type_name(e.get_type()))
		cw.set_buffer(" | ")

	cw.discard_buffer()
	cw.append(".")
	cw.newline()
	cw.newline()

if __name__ == '__main__':
	t0 = dragoman.DefinedType("string")
	t0.register()

	t0 = dragoman.DefinedType("integer")
	t0.register()

	dragoman.DragomanParser.parse_file('test')

	code_writer = dragoman.CodeWriter("test_drago.erl")
	code_writer.line("-module(test_drago).")

	for e in dragoman.EnumType.get_all():
		add_enum_type(code_writer, e)

	for e in dragoman.ObjectType.get_all():
		add_record(code_writer, e)

	for e in dragoman.PolymorphType.get_all():
		add_polymorph_type(code_writer, e)

	code_writer.finalize()
