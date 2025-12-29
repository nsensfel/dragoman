#!/bin/env python3

import dragoman

class NameConverter:
	def type_to_module_name (t: dragoman.DefinedType) -> str:
		return "dgn_" + t.get_name().lower()

	def type_to_record_name (t: dragoman.DefinedType) -> str:
		return t.get_name().lower()

	def object_entry_to_variable (o: dragoman.ObjectTypeEntry) -> str:
		name = o.get_name().lower()
		return name[0].upper() + name[1:]

	def object_entry_to_record_member (o: dragoman.ObjectTypeEntry) -> str:
		return o.get_name().lower()

	def object_entry_to_tag (o: dragoman.ObjectTypeEntry) -> str:
		return "<<\"" + o.get_tag() + "\">>"

	def enum_entry_to_atom (o: dragoman.EnumTypeEntry) -> str:
		return o.get_name().lower()

	def enum_entry_to_value (o: dragoman.EnumTypeEntry) -> str:
		return "<<\"" + o.get_tag() + "\">>"

	def polymorph_case_to_atom (o: dragoman.PolymorphTypeCase) -> str:
		return o.get_name().lower()

	def type_to_type_reference (t: dragoman.DefinedType) -> str:
		if isinstance(t, dragoman.UserDefinedType):
			return NameConverter.type_to_module_name(t) + ":type()"
		else:
			return t.get_name().lower()

	def type_to_type_export (t: dragoman.DefinedType) -> str:
		return t.get_name().lower()

	def type_to_record_reference (t: dragoman.DefinedType) -> str:
		return "#" + t.get_name().lower()

class ObjectTypeConverter:

	def add_record (
		cw: dragoman.CodeWriter,
		object_type: dragoman.ObjectType
	):
		cw.line("-record")
		cw.line("(")
		cw.increase_indent()
		cw.start_line(NameConverter.type_to_record_name(object_type))
		cw.append(",")
		cw.newline()
		cw.line("{")
		cw.increase_indent()

		for e in object_type.get_entries():
			cw.start_line(NameConverter.object_entry_to_record_member(e))
			cw.append(" :: ")
			cw.append(NameConverter.type_to_type_reference(e.get_type()))
			cw.set_buffer(",")
			cw.mark_buffer_as_ending_line()

		cw.discard_buffer()
		cw.newline()
		cw.decrease_indent()
		cw.line("}")
		cw.decrease_indent()
		cw.line(").")
		cw.newline()

		cw.start_line("-type type() :: ")
		cw.append(NameConverter.type_to_record_reference(object_type))
		cw.append( "{}.")
		cw.newline()

	def add_exports (
		cw: dragoman.CodeWriter,
		object_type: dragoman.ObjectType
	):
		cw.line("-export_type([ type/0 ]).")
		cw.newline()

		cw.line("-export")
		cw.line("(")
		cw.increase_indent()
		cw.line("[")
		cw.increase_indent()

		cw.line("json_export/1,")
		cw.line("json_import/1,")

		cw.start_line("new/")
		cw.append(str(len(object_type.get_entries())))
		cw.append(",")
		cw.newline()

		for e in object_type.get_entries():
			entry_name = NameConverter.object_entry_to_record_member(e)

			cw.newline()
			cw.start_line("get_")
			cw.append(entry_name)
			cw.append("/1,")
			cw.newline()

			cw.start_line("set_")
			cw.append(entry_name)
			cw.append("/2")
			cw.set_buffer(",")
			cw.mark_buffer_as_ending_line()

		cw.discard_buffer()
		cw.decrease_indent()
		cw.newline()
		cw.line("]")
		cw.decrease_indent()
		cw.line(").")
		cw.newline()

	def add_builder (
		cw: dragoman.CodeWriter,
		object_type: dragoman.ObjectType
	):
		cw.line("-spec new")
		cw.line("(")
		cw.increase_indent()

		for e in object_type.get_entries():
			cw.start_line(NameConverter.type_to_type_reference(e.get_type()))
			cw.set_buffer(",")
			cw.mark_buffer_as_ending_line()

		cw.discard_buffer()
		cw.decrease_indent()
		cw.newline()
		cw.line(") -> type().")

		cw.line("new")
		cw.line("(")
		cw.increase_indent()

		for e in object_type.get_entries():
			cw.start_line(NameConverter.object_entry_to_variable(e))
			cw.set_buffer(",")
			cw.mark_buffer_as_ending_line()

		cw.discard_buffer()
		cw.decrease_indent()
		cw.newline()
		cw.line(") ->")

		cw.increase_indent()
		cw.line(NameConverter.type_to_record_reference(object_type))
		cw.line("{")
		cw.increase_indent()

		for e in object_type.get_entries():
			et = e.get_type()

			cw.start_line(NameConverter.object_entry_to_record_member(e))
			cw.append(" = ")
			cw.append(NameConverter.object_entry_to_variable(e))

			cw.set_buffer(",")
			cw.mark_buffer_as_ending_line()

		cw.discard_buffer()
		cw.newline()
		cw.decrease_indent()
		cw.line("}.")
		cw.decrease_indent()

		cw.newline()

	def add_set_function (
		cw: dragoman.CodeWriter,
		ot: dragoman.ObjectType,
		ote: dragoman.ObjectTypeEntry
	):
		entry_name = NameConverter.object_entry_to_record_member(ote)

		cw.start_line("-spec ")
		cw.append("set_")
		cw.append(entry_name)
		cw.append(" (")
		cw.append(NameConverter.type_to_type_reference(ote.get_type()))
		cw.append(", type()) -> type().")
		cw.newline()

		cw.start_line("set_")
		cw.append(entry_name)
		cw.append(" (V, E) -> ")
		cw.append("E")
		cw.append(NameConverter.type_to_record_reference(ot))
		cw.append("{ ")
		cw.append(entry_name)
		cw.append(" = V }.")
		cw.newline()
		cw.newline()

	def add_get_function (
		cw: dragoman.CodeWriter,
		ot: dragoman.ObjectType,
		ote: dragoman.ObjectTypeEntry
	):
		entry_name = NameConverter.object_entry_to_record_member(ote)

		cw.start_line("-spec ")
		cw.append("get_")
		cw.append(entry_name)
		cw.append(" (type()) -> ")
		cw.append(NameConverter.type_to_type_reference(ote.get_type()))
		cw.append(".")
		cw.newline()

		cw.start_line("get_")
		cw.append(entry_name)
		cw.append("(")
		cw.append(NameConverter.type_to_record_reference(ot))
		cw.append("{ ")
		cw.append(entry_name)
		cw.append(" = V }) -> V.")
		cw.newline()
		cw.newline()

	def add_json_export_function (
		cw: dragoman.CodeWriter,
		object_type: dragoman.ObjectType
	):
		cw.line("-spec json_export (type()) -> {[{binary(), any()}]}.")
		cw.line("json_export (E) ->")
		cw.increase_indent()
		cw.line("{")
		cw.increase_indent()
		cw.line("[")
		cw.increase_indent()

		for e in object_type.get_entries():
			et = e.get_type()

			cw.start_line("{ ")
			cw.append(NameConverter.object_entry_to_tag(e))
			cw.append(", ")

			value_access = (
				"E"
				+ NameConverter.type_to_record_reference(object_type)
				+ "."
				+ NameConverter.object_entry_to_record_member(e)
			)

			if (isinstance(et, dragoman.ArrayOfDefinedType)):
				cw.append("[]") # TODO: implement
			elif (isinstance(et, dragoman.UserDefinedType)):
				cw.append(NameConverter.type_to_module_name(et))
				cw.append(":json_export(")
				cw.append(value_access)
				cw.append(")")
			else:
				cw.append(value_access)

			cw.append(" }")
			cw.set_buffer(",")
			cw.mark_buffer_as_ending_line()

		cw.discard_buffer()
		cw.newline()
		cw.decrease_indent()
		cw.line("]")
		cw.decrease_indent()
		cw.line("}.")
		cw.decrease_indent()
		cw.newline()

	def add_json_import_function (
		cw: dragoman.CodeWriter,
		object_type: dragoman.ObjectType
	):
		cw.line("-spec json_import (dict:dict()) -> type().")
		cw.line("json_import (D) ->")
		cw.increase_indent()
		cw.line(NameConverter.type_to_record_reference(object_type))
		cw.line("{")
		cw.increase_indent()

		for e in object_type.get_entries():
			et = e.get_type()

			cw.start_line(NameConverter.object_entry_to_record_member(e))
			cw.append(" = ")

			value_access = (
				"dict:get("
				+ NameConverter.object_entry_to_tag(e)
				+ ", D)"
			)

			if (isinstance(et, dragoman.ArrayOfDefinedType)):
				cw.append("[]") # TODO: implement
			elif (isinstance(et, dragoman.UserDefinedType)):
				cw.append(NameConverter.type_to_module_name(et))
				cw.append(":json_import(")
				cw.append(value_access)
				cw.append(")")
			else:
				cw.append(value_access)

			cw.set_buffer(",")
			cw.mark_buffer_as_ending_line()

		cw.discard_buffer()
		cw.newline()
		cw.decrease_indent()
		cw.line("}.")
		cw.decrease_indent()
		cw.newline()

	def convert (e: dragoman.ObjectType):
		code_writer = dragoman.CodeWriter(
			NameConverter.type_to_module_name(e)
			+ ".erl"
		)

		code_writer.start_line("-module(")
		code_writer.append(NameConverter.type_to_module_name(e))
		code_writer.append(").")
		code_writer.newline()

		ObjectTypeConverter.add_record(code_writer, e)
		ObjectTypeConverter.add_exports(code_writer, e)

		ObjectTypeConverter.add_json_export_function(code_writer, e)
		ObjectTypeConverter.add_json_import_function(code_writer, e)

		ObjectTypeConverter.add_builder(code_writer, e)

		for i in e.get_entries():
			ObjectTypeConverter.add_get_function(code_writer, e, i)
			ObjectTypeConverter.add_set_function(code_writer, e, i)

		code_writer.finalize()

class EnumTypeConverter:
	def add_type (
		cw: dragoman.CodeWriter,
		enum_type: dragoman.EnumType
	):
		cw.start_line("-type type() :: ")

		for e in enum_type.get_entries():
			cw.append("'")
			cw.append(NameConverter.enum_entry_to_atom(e))
			cw.append("'")
			cw.set_buffer(" | ")

		cw.discard_buffer()
		cw.append(".")
		cw.newline()
		cw.newline()

	def add_exports (
		cw: dragoman.CodeWriter,
		enum_type: dragoman.EnumType
	):
		cw.line("-export_type([ type/0 ]).")
		cw.newline()

		cw.line("-export")
		cw.line("(")
		cw.increase_indent()
		cw.line("[")
		cw.increase_indent()

		cw.line("json_export/1,")
		cw.line("json_import/1,")

		for e in enum_type.get_entries():
			entry_name = NameConverter.enum_entry_to_atom(e)

			cw.start_line(entry_name)
			cw.append("/0")
			cw.set_buffer(",")
			cw.mark_buffer_as_ending_line()

		cw.discard_buffer()
		cw.newline()
		cw.decrease_indent()
		cw.line("]")
		cw.decrease_indent()
		cw.line(").")
		cw.newline()

	def add_function (
		cw: dragoman.CodeWriter,
		ot: dragoman.EnumType,
		ote: dragoman.EnumTypeEntry
	):
		entry_name = NameConverter.enum_entry_to_atom(ote)

		cw.start_line("-spec ")
		cw.append(entry_name)
		cw.append(" () -> '")
		cw.append(entry_name)
		cw.append("'.")
		cw.newline()

		cw.start_line(entry_name)
		cw.append("() -> ")
		cw.append("'")
		cw.append(entry_name)
		cw.append("'.")
		cw.newline()
		cw.newline()

	def add_json_export_function (
		cw: dragoman.CodeWriter,
		enum_type: dragoman.EnumType
	):
		cw.line("-spec json_export (type()) -> binary().")

		for e in enum_type.get_entries():
			name = NameConverter.enum_entry_to_atom(e)

			cw.start_line("json_export (")
			cw.append(name)
			cw.append(") -> ")
			cw.append(NameConverter.enum_entry_to_value(e))
			cw.set_buffer(";")
			cw.mark_buffer_as_ending_line()

		cw.discard_buffer()
		cw.append(".")
		cw.newline()
		cw.newline()

	def add_json_import_function (
		cw: dragoman.CodeWriter,
		enum_type: dragoman.EnumType
	):
		cw.line("-spec json_import (binary()) -> type().")

		for e in enum_type.get_entries():
			name = NameConverter.enum_entry_to_atom(e)

			cw.start_line("json_import (")
			cw.append(NameConverter.enum_entry_to_value(e))
			cw.append(") -> ")
			cw.append(name)
			cw.set_buffer(";")
			cw.mark_buffer_as_ending_line()

		cw.discard_buffer()
		cw.append(".")
		cw.newline()
		cw.newline()

	def convert (e: dragoman.EnumType):
		code_writer = dragoman.CodeWriter(
			NameConverter.type_to_module_name(e)
			+ ".erl"
		)

		code_writer.start_line("-module(")
		code_writer.append(NameConverter.type_to_module_name(e))
		code_writer.append(").")
		code_writer.newline()

		EnumTypeConverter.add_type(code_writer, e)
		EnumTypeConverter.add_exports(code_writer, e)

		EnumTypeConverter.add_json_export_function(code_writer, e)
		EnumTypeConverter.add_json_import_function(code_writer, e)

		for i in e.get_entries():
			EnumTypeConverter.add_function(code_writer, e, i)

		code_writer.finalize()

class PolymorphTypeConverter:
	def add_type (
		cw: dragoman.CodeWriter,
		polymorph_type: dragoman.PolymorphType
	):
		cw.start_line("-type type() :: ")

		for e in polymorph_type.get_cases():
			cw.append(NameConverter.type_to_type_reference(e.get_type()))
			cw.set_buffer(" | ")

		cw.discard_buffer()
		cw.append(".")
		cw.newline()
		cw.newline()

	def add_builds (
		cw: dragoman.CodeWriter,
		polymorph_type: dragoman.PolymorphType,
	):
		for pcase in polymorph_type.get_cases():
			name = NameConverter.polymorph_case_to_atom(pcase)

			cw.start_line("-spec ")
			cw.append(name)
			cw.newline()
			cw.line("(")
			cw.increase_indent()

			for build_param in pcase.get_type().get_entries():
				if (build_param.get_tag() == polymorph_type.get_tag()):
					# This is a constant, at this level.
					continue

				cw.start_line(
					NameConverter.type_to_type_reference(build_param.get_type())
				)
				cw.set_buffer(",")
				cw.mark_buffer_as_ending_line()

			cw.discard_buffer()
			cw.decrease_indent()
			cw.newline()
			cw.start_line(") -> ")
			cw.append(NameConverter.type_to_type_reference(pcase.get_type()))
			cw.append(".")
			cw.newline()

			cw.line(name)
			cw.line("(")
			cw.increase_indent()

			for build_param in pcase.get_type().get_entries():
				if (build_param.get_tag() == polymorph_type.get_tag()):
					# This is a constant, at this level.
					continue

				cw.start_line(NameConverter.object_entry_to_variable(build_param))
				cw.set_buffer(",")
				cw.mark_buffer_as_ending_line()

			cw.discard_buffer()
			cw.decrease_indent()
			cw.newline()
			cw.line(") ->")

			cw.increase_indent()
			cw.start_line(NameConverter.type_to_module_name(pcase.get_type()))
			cw.append(":new")
			cw.newline()
			cw.line("(")
			cw.increase_indent()

			for build_param in pcase.get_type().get_entries():
				if (build_param.get_tag() == polymorph_type.get_tag()):
					cw.start_line(
						NameConverter.enum_entry_to_atom(
							polymorph_type.get_enum_type().get_entry_from_name(
								pcase.get_name()
							)
						)
					)
				else:
					cw.start_line(NameConverter.object_entry_to_variable(build_param))

				cw.set_buffer(",")
				cw.mark_buffer_as_ending_line()

			cw.discard_buffer()
			cw.newline()
			cw.decrease_indent()
			cw.line(").")
			cw.decrease_indent()
			cw.newline()

	def add_exports (
		cw: dragoman.CodeWriter,
		polymorph_type: dragoman.PolymorphType
	):
		cw.line("-export_type([ type/0 ]).")
		cw.newline()

		cw.line("-export")
		cw.line("(")
		cw.increase_indent()
		cw.line("[")
		cw.increase_indent()

		cw.line("json_export/1,")
		cw.line("json_import/1,")

		for pcase in polymorph_type.get_cases():
			name = NameConverter.polymorph_case_to_atom(pcase)

			cw.start_line(name)
			cw.append("/")
			cw.append(str(len(pcase.get_type().get_entries()) - 1))
			cw.set_buffer(",")
			cw.mark_buffer_as_ending_line()

		cw.discard_buffer()
		cw.newline()
		cw.decrease_indent()
		cw.line("]")
		cw.decrease_indent()
		cw.line(").")
		cw.newline()

	def add_json_export_function (
		cw: dragoman.CodeWriter,
		polymorph_type: dragoman.PolymorphType
	):
		cw.line("-spec json_export (type()) -> {[{binary(), any()}]}.")

		for pcase in polymorph_type.get_cases():
			name = NameConverter.polymorph_case_to_atom(pcase)

			cw.start_line("json_export (E) when is_record(E, ")
			cw.append(NameConverter.type_to_record_name(pcase.get_type()))
			cw.append(", ")
			cw.append(str(len(pcase.get_type().get_entries())))
			cw.append(") -> ")
			cw.append(NameConverter.type_to_module_name(pcase.get_type()))
			cw.append(":json_export(E)")
			cw.set_buffer(";")
			cw.mark_buffer_as_ending_line()

		cw.discard_buffer()
		cw.append(".")
		cw.newline()
		cw.newline()

	def add_json_import_function (
		cw: dragoman.CodeWriter,
		polymorph_type: dragoman.PolymorphType
	):
		cw.line("-spec json_import (dict:dict()) -> type().")
		cw.line("json_import (D) ->")
		cw.increase_indent()
		cw.start_line("V = dict:get(<<\"")
		cw.append(polymorph_type.get_tag())
		cw.append("\">>, D),")
		cw.newline()
		cw.line("if")

		cw.increase_indent()

		for pcase in polymorph_type.get_cases():
			eentry = pcase.get_enum_entry()
			cw.start_line("(V == ")
			cw.append(NameConverter.enum_entry_to_value(eentry))
			cw.append(") -> ")
			cw.append(NameConverter.type_to_module_name(pcase.get_type()))
			cw.append(":json_import(D)")
			cw.set_buffer(";")
			cw.mark_buffer_as_ending_line()

		cw.discard_buffer()
		cw.decrease_indent()
		cw.newline()
		cw.line("end.")
		cw.decrease_indent()
		cw.newline()
		cw.newline()

	def convert (e: dragoman.PolymorphType):
		code_writer = dragoman.CodeWriter(
			NameConverter.type_to_module_name(e)
			+ ".erl"
		)

		code_writer.start_line("-module(")
		code_writer.append(NameConverter.type_to_module_name(e))
		code_writer.append(").")
		code_writer.newline()

		PolymorphTypeConverter.add_type(code_writer, e)
		PolymorphTypeConverter.add_exports(code_writer, e)

		PolymorphTypeConverter.add_json_export_function(code_writer, e)
		PolymorphTypeConverter.add_json_import_function(code_writer, e)

		PolymorphTypeConverter.add_builds(code_writer, e)

		code_writer.finalize()


if __name__ == '__main__':
	t0 = dragoman.DefinedType("string")
	t0.register()

	t0 = dragoman.DefinedType("integer")
	t0.register()

	dragoman.DragomanParser.parse_file('test')


	for e in dragoman.EnumType.get_all():
		EnumTypeConverter.convert(e)

	for e in dragoman.ObjectType.get_all():
		ObjectTypeConverter.convert(e)

	for e in dragoman.PolymorphType.get_all():
		PolymorphTypeConverter.convert(e)
