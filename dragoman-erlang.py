#!/bin/env python3

from pathlib import Path

import dragoman

class NameConverter:
	MODULE_NAMES = dict()
	RECORD_NAMES = dict()
	VARIABLE_NAMES = dict()
	RECORD_MEMBER_NAMES = dict()
	ATOM_NAMES = dict()

	def type_to_module_name (t: dragoman.DefinedType) -> str:
		result = NameConverter.MODULE_NAMES.get(t)

		if result is None:
			split_name = dragoman.NameSplitter.split(t.get_name())

			result = "dgn_" + ("_".join(split_name))
			NameConverter.MODULE_NAMES[t] = result

		return result

	def type_to_record_name (t: dragoman.DefinedType) -> str:
		result = NameConverter.RECORD_NAMES.get(t)

		if result is None:
			split_name = dragoman.NameSplitter.split(t.get_name())

			result = "_".join(split_name)
			NameConverter.RECORD_NAMES[t] = result

		return result

	def object_entry_to_variable (o: dragoman.ObjectTypeEntry) -> str:
		result = NameConverter.VARIABLE_NAMES.get(o)

		if result is None:
			split_name = dragoman.NameSplitter.split(o.get_name())

			result = "".join([(a[0].upper() + a[1:]) for a in split_name])
			NameConverter.VARIABLE_NAMES[o] = result

		return result

	def object_entry_to_record_member (o: dragoman.ObjectTypeEntry) -> str:
		result = NameConverter.RECORD_MEMBER_NAMES.get(o)

		if result is None:
			split_name = dragoman.NameSplitter.split(o.get_name())

			result = "_".join(split_name)
			NameConverter.RECORD_MEMBER_NAMES[o] = result

		return result

	def object_entry_to_tag (o: dragoman.ObjectTypeEntry) -> str:
		return "<<\"" + o.get_tag() + "\">>"

	def enum_entry_to_atom (o: dragoman.EnumTypeEntry) -> str:
		result = NameConverter.ATOM_NAMES.get(o)

		if result is None:
			split_name = dragoman.NameSplitter.split(o.get_name())

			result = "_".join(split_name)
			NameConverter.RECORD_MEMBER_NAMES[o] = result

		return result

	def enum_entry_to_value (o: dragoman.EnumTypeEntry) -> str:
		return "<<\"" + o.get_tag() + "\">>"

	def polymorph_case_to_atom (o: dragoman.PolymorphTypeCase) -> str:
		result = NameConverter.ATOM_NAMES.get(o)

		if result is None:
			split_name = dragoman.NameSplitter.split(o.get_name())

			result = "_".join(split_name)
			NameConverter.RECORD_MEMBER_NAMES[o] = result

		return result

	def type_to_type_reference (t: dragoman.DefinedType) -> str:
		if isinstance(t, dragoman.UserDefinedType):
			return NameConverter.type_to_module_name(t) + ":type()"
		elif isinstance(t, dragoman.ArrayOfDefinedType):
			return (
				"list("
				+ NameConverter.type_to_type_reference(t.get_parent())
				+ ")"
			)
		elif isinstance(t, dragoman.DictOfDefinedType):
			return (
				"#{"
				+ NameConverter.type_to_type_reference(t.get_field_type())
				+ " => "
				+ NameConverter.type_to_type_reference(t.get_parent())
				+ "}"
			)
		else:
			name = t.get_name().lower()

			if (name == "string"):
				return "binary()"
			else:
				return name + "()"

	def type_to_record_reference (t: dragoman.DefinedType) -> str:
		return "#" + NameConverter.type_to_record_name(t)

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

			if (Dragoman2Erlang.ENABLE_ATAXIA):
				cw.append(",")
				cw.newline()
				cw.start_line("get_")
				cw.append(entry_name)
				cw.append("_field/0,")
				cw.newline()

				cw.start_line("ataxia_set_")
				cw.append(entry_name)
				cw.append("/2")

				if (
					isinstance(e.get_type(), dragoman.UserDefinedType)
					or isinstance(e.get_type(), dragoman.ArrayOfDefinedType)
					or isinstance(e.get_type(), dragoman.DictOfDefinedType)
				):
					cw.append(",")
					cw.newline()
					cw.start_line("ataxia_update_")
					cw.append(entry_name)
					cw.append("/3")

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

	def add_ataxia_set_function (
		cw: dragoman.CodeWriter,
		ot: dragoman.ObjectType,
		ote: dragoman.ObjectTypeEntry
	):
		entry_name = NameConverter.object_entry_to_record_member(ote)

		cw.start_line("-spec ")
		cw.append("ataxia_set_")
		cw.append(entry_name)
		cw.append(" (")
		cw.append(NameConverter.type_to_type_reference(ote.get_type()))
		cw.append(", type()) -> {ataxic:type(), type()}.")
		cw.newline()

		cw.start_line("ataxia_set_")
		cw.append(entry_name)
		cw.append(" (V, E) ->")
		cw.newline()
		cw.increase_indent()
		cw.line("{")
		cw.increase_indent()
		cw.start_line("ataxic:update_field(")
		cw.append(NameConverter.type_to_record_reference(ot))
		cw.append(".")
		cw.append(entry_name)
		cw.append(", ataxic:constant(V)),")
		cw.newline()
		cw.start_line("E")
		cw.append(NameConverter.type_to_record_reference(ot))
		cw.append("{ ")
		cw.append(entry_name)
		cw.append(" = V }")
		cw.newline()
		cw.decrease_indent()
		cw.line("}.")
		cw.decrease_indent()
		cw.newline()
		cw.newline()

	def add_ataxia_update_function (
		cw: dragoman.CodeWriter,
		ot: dragoman.ObjectType,
		ote: dragoman.ObjectTypeEntry
	):
		entry_name = NameConverter.object_entry_to_record_member(ote)

		cw.start_line("-spec ")
		cw.append("ataxia_update_")
		cw.append(entry_name)
		cw.append(" (ataxic:type(), ")
		cw.append(NameConverter.type_to_type_reference(ote.get_type()))
		cw.append(", type()) -> {ataxic:type(), type()}.")
		cw.newline()

		cw.start_line("ataxia_update_")
		cw.append(entry_name)
		cw.append(" (U, V, E) ->")
		cw.newline()
		cw.increase_indent()
		cw.line("{")
		cw.increase_indent()
		cw.start_line("ataxic:update_field(")
		cw.append(NameConverter.type_to_record_reference(ot))
		cw.append(".")
		cw.append(entry_name)
		cw.append(", ")
		cw.append("U),")
		cw.newline()
		cw.start_line("E")
		cw.append(NameConverter.type_to_record_reference(ot))
		cw.append("{ ")
		cw.append(entry_name)
		cw.append(" = V }")
		cw.newline()
		cw.decrease_indent()
		cw.line("}.")
		cw.decrease_indent()
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

	def add_get_field_function (
		cw: dragoman.CodeWriter,
		ot: dragoman.ObjectType,
		ote: dragoman.ObjectTypeEntry
	):
		entry_name = NameConverter.object_entry_to_record_member(ote)

		cw.start_line("-spec ")
		cw.append("get_")
		cw.append(entry_name)
		cw.append("_field () -> non_neg_integer().")
		cw.newline()

		cw.start_line("get_")
		cw.append(entry_name)
		cw.append("_field () -> ")
		cw.append(NameConverter.type_to_record_reference(ot))
		cw.append(".")
		cw.append(entry_name)
		cw.append(".")
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

			(depth, leaf_type) = dragoman.ArrayOfDefinedType.compute_depth(et)

			if (
				(not isinstance(leaf_type, dragoman.UserDefinedType))
				and (not isinstance(leaf_type, dragoman.DictOfDefinedType))
			):
				cw.append(value_access)
			elif (depth == 0):
				if (isinstance(leaf_type, dragoman.DictOfDefinedType)):
					cw.append("lists:map(fun ")
					cw.append(
						NameConverter.type_to_module_name(leaf_type.get_parent())
					)
					cw.append(":json_export/1, maps:values(")
					cw.append(value_access)
					cw.append("))")
				else:
					cw.append(NameConverter.type_to_module_name(et))
					cw.append(":json_export(")
					cw.append(value_access)
					cw.append(")")
			elif (depth == 1):
				if (isinstance(leaf_type, dragoman.DictOfDefinedType)):
					cw.append("lists:map(fun (Y) -> lists:map(fun ")
					cw.append(
						NameConverter.type_to_module_name(leaf_type.get_parent())
					)
					cw.append(":json_export/1, maps:values(Y)) end, ")
					cw.append(value_access)
					cw.append(")")
				else:
					cw.append("lists:map(fun ")
					cw.append(NameConverter.type_to_module_name(leaf_type))
					cw.append(":json_export/1, ")
					cw.append(value_access)
					cw.append(")")
			else:
				cw.append("lists_deep_map(")
				cw.append(str(depth - 1))
				cw.append(", ")
				cw.append(value_access)
				cw.append(", fun ")
				if (isinstance(leaf_type, dragoman.DictOfDefinedType)):
					cw.append("(Y) -> ")
					cw.append("lists:map(fun ")
					cw.append(
						NameConverter.type_to_module_name(leaf_type.get_parent())
					)
					cw.append(":json_export/1, Y) end)")
				else:
					cw.append(NameConverter.type_to_module_name(leaf_type))
					cw.append(":json_export/1)")

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

	def add_deep_map_function (
		cw: dragoman.CodeWriter,
		object_type: dragoman.ObjectType
	):
		cw.line("-spec lists_deep_map (non_neg_int(), list(any()), fun()) -> list().")
		cw.line("lists_deep_map (0, List, Fun) -> lists:map(Fun, List);")
		cw.line("lists_deep_map (RemainingDepth, List, Fun) ->")
		cw.increase_indent()
		cw.line("[ lists_deep_map(RemainingDepth - 1, E, Fun) || E <- List ].")
		cw.decrease_indent()

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

			(depth, leaf_type) = dragoman.ArrayOfDefinedType.compute_depth(et)

			if (depth == 0):
				if (isinstance(leaf_type, dragoman.DictOfDefinedType)):
					cw.append("lists:fold(fun (X, Map) -> E = ")
					cw.append(
						NameConverter.type_to_module_name(leaf_type.get_parent())
					)
					cw.append(":json_import(X), maps:put(")
					cw.append(
						NameConverter.type_to_module_name(leaf_type.get_parent())
					)
					cw.append(":get_")
					cw.append(leaf_type.get_field_name())
					cw.append("(E), E, Map) end, maps:new(), ")
					cw.append(value_access)
					cw.append(")")
				elif (isinstance(leaf_type, dragoman.UserDefinedType)):
					cw.append(NameConverter.type_to_module_name(et))
					cw.append(":json_import(")
					cw.append(value_access)
					cw.append(")")
				else:
					cw.append(value_access)
			elif (depth == 1):
				if (isinstance(leaf_type, dragoman.DictOfDefinedType)):
					cw.append("lists:map(fun (Y) -> ")
					cw.append("lists:fold(fun (X, Map) -> E = ")
					cw.append(
						NameConverter.type_to_module_name(leaf_type.get_parent())
					)
					cw.append(":json_import(X), maps:put(")
					cw.append(
						NameConverter.type_to_module_name(leaf_type.get_parent())
					)
					cw.append(":get_")
					cw.append(leaf_type.get_key_field_name())
					cw.append("(E), E, Map) end, maps:new(), Y) end, ")
					cw.append(value_access)
					cw.append(")")
				elif (isinstance(leaf_type, dragoman.UserDefinedType)):
					cw.append("lists:map(fun ")
					cw.append(NameConverter.type_to_module_name(leaf_type))
					cw.append(":json_import/1, ")
					cw.append(value_access)
					cw.append(")")
				else:
					cw.append(value_access)
			else:
				cw.append("lists_deep_map(")
				cw.append(str(depth - 1))
				cw.append(", ")
				cw.append(value_access)
				cw.append(", fun ")
				if (isinstance(leaf_type, dragoman.DictOfDefinedType)):
					cw.append("(Y) -> ")
					cw.append("lists:fold(fun (X, Map) -> E = ")
					cw.append(
						NameConverter.type_to_module_name(leaf_type.get_parent())
					)
					cw.append(":json_import(X), maps:put(")
					cw.append(
						NameConverter.type_to_module_name(leaf_type.get_parent())
					)
					cw.append(":get_")
					cw.append(leaf_type.get_field_name())
					cw.append("(E), E, Map) end, maps:new(), Y) end)")
				elif (isinstance(leaf_type, dragoman.UserDefinedType)):
					cw.append(NameConverter.type_to_module_name(leaf_type))
					cw.append(":json_import/1)")
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
			Path(dragoman.Dragoman.OUTPUT_FOLDER)
			/ (NameConverter.type_to_module_name(e) + ".erl")
		)

		code_writer.start_line("-module(")
		code_writer.append(NameConverter.type_to_module_name(e))
		code_writer.append(").")
		code_writer.newline()
		code_writer.newline()

		code_writer.title_line("%", "", 0, 80)
		code_writer.title_line("%", " TYPES ", 2, 80)
		code_writer.title_line("%", "", 0, 80)

		ObjectTypeConverter.add_record(code_writer, e)
		code_writer.newline()

		code_writer.title_line("%", "", 0, 80)
		code_writer.title_line("%", " EXPORTS ", 2, 80)
		code_writer.title_line("%", "", 0, 80)
		ObjectTypeConverter.add_exports(code_writer, e)
		code_writer.newline()

		code_writer.title_line("%", "", 0, 80)
		code_writer.title_line("%", " LOCAL FUNCTIONS ", 2, 80)
		code_writer.title_line("%", "", 0, 80)

		for i in e.get_entries():
			(depth, leaf_type) = dragoman.ArrayOfDefinedType.compute_depth(
				i.get_type()
			)

			if (depth > 1):
				ObjectTypeConverter.add_deep_map_function(code_writer, e)
				break

		code_writer.newline()

		code_writer.title_line("%", "", 0, 80)
		code_writer.title_line("%", " EXPORTED FUNCTIONS ", 2, 80)
		code_writer.title_line("%", "", 0, 80)

		ObjectTypeConverter.add_json_export_function(code_writer, e)
		ObjectTypeConverter.add_json_import_function(code_writer, e)

		ObjectTypeConverter.add_builder(code_writer, e)

		for i in e.get_entries():
			ObjectTypeConverter.add_get_function(code_writer, e, i)
			ObjectTypeConverter.add_set_function(code_writer, e, i)

			if (Dragoman2Erlang.ENABLE_ATAXIA):
				ObjectTypeConverter.add_ataxia_set_function(code_writer, e, i)

				if (
					isinstance(i.get_type(), dragoman.UserDefinedType)
					or isinstance(i.get_type(), dragoman.ArrayOfDefinedType)
					or isinstance(i.get_type(), dragoman.DictOfDefinedType)
				):
					ObjectTypeConverter.add_ataxia_update_function(code_writer, e, i)

				ObjectTypeConverter.add_get_field_function(code_writer, e, i)

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
			Path(dragoman.Dragoman.OUTPUT_FOLDER)
			/ (NameConverter.type_to_module_name(e) + ".erl")
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
				if (build_param.get_name() == polymorph_type.get_key_field_name()):
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
				if (build_param.get_name() == polymorph_type.get_key_field_name()):
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
				if (build_param.get_name() == polymorph_type.get_key_field_name()):
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
		cw.append(polymorph_type.get_key_field_tag())
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
			Path(dragoman.Dragoman.OUTPUT_FOLDER)
			/ (NameConverter.type_to_module_name(e) + ".erl")
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

class Dragoman2Erlang:
	ENABLE_ATAXIA = False

	def initialize ():
		argparser = dragoman.Dragoman.initialize()
		argparser.add_argument(
			"--ataxia",
			action="store_true",
			default=False,
			help="Enable Ataxia functions"
		)

		args = argparser.parse_args()

		if args.ataxia:
			Dragoman2Erlang.ENABLE_ATAXIA = True

		dragoman.Dragoman.handle_arguments(args)
		dragoman.DragomanParser.parse_file(str(args.dgl_file[0]))

	def export ():
		for e in dragoman.EnumType.get_all():
			EnumTypeConverter.convert(e)

		for e in dragoman.ObjectType.get_all():
			ObjectTypeConverter.convert(e)

		for e in dragoman.PolymorphType.get_all():
			PolymorphTypeConverter.convert(e)

if __name__ == '__main__':
	Dragoman2Erlang.initialize()
	Dragoman2Erlang.export()
