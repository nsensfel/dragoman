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

			result = "Dragoman." + ("".join([n[0].upper() + n[1:] for n in split_name]))
			NameConverter.MODULE_NAMES[t] = result

		return result

	def type_to_filename (t: dragoman.DefinedType) -> str:
		split_name = dragoman.NameSplitter.split(t.get_name())

		result = "".join([n[0].upper() + n[1:] for n in split_name])

		return result + ".gren"

	def object_entry_to_variable (o: dragoman.ObjectTypeEntry) -> str:
		result = NameConverter.VARIABLE_NAMES.get(o)

		if result is None:
			split_name = dragoman.NameSplitter.split(o.get_name())

			result = "_".join(split_name)
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
		return "\"" + o.get_tag() + "\""

	def enum_entry_to_atom (o: dragoman.EnumTypeEntry) -> str:
		return o.get_name()

	def enum_entry_to_value (o: dragoman.EnumTypeEntry) -> str:
		# TODO: support for integer values
		return "\"" + o.get_tag() + "\""

	def polymorph_case_to_atom (o: dragoman.PolymorphTypeCase) -> str:
		return o.get_name()

	def type_to_type_reference (t: dragoman.DefinedType) -> str:
		if isinstance(t, dragoman.ArrayOfDefinedType):
			return (
				"(Array "
				+ NameConverter.type_to_type_reference(t.get_parent())
				+ ")"
			)
		elif isinstance(t, dragoman.DictOfDefinedType):
			return (
				"(Dict.Dict "
				+ NameConverter.type_to_type_reference(t.get_field_type())
				+ " "
				+ NameConverter.type_to_type_reference(t.get_parent())
				+ ")"
			)
		elif isinstance(t, dragoman.UserDefinedType):
			return NameConverter.type_to_module_name(t) + ".Type"
		else:
			name = t.get_name().lower()

			if (name == "string"):
				return "String"
			elif (name == "integer"):
				return "Int"
			elif (name == "boolean"):
				return "Bool"
			elif (name == "float"):
				return "Float"
			else:
				return name[0].upper() + name[1:]

class ObjectTypeConverter:
	def add_type (
		cw: dragoman.CodeWriter,
		object_type: dragoman.ObjectType
	):
		cw.line("type alias Type =")
		cw.increase_indent()
		cw.line("{")
		cw.increase_indent()
		for e in object_type.get_entries():
			cw.start_line(NameConverter.object_entry_to_record_member(e))
			cw.append(" : ")
			cw.append(NameConverter.type_to_type_reference(e.get_type()))
			cw.set_buffer(",")
			cw.mark_buffer_as_ending_line()

		cw.discard_buffer()
		cw.newline()
		cw.decrease_indent()
		cw.line("}")
		cw.decrease_indent()
		cw.newline()

	def add_exports (
		cw: dragoman.CodeWriter,
		object_type: dragoman.ObjectType
	):
		cw.line("Type,")
		cw.line("decoder,")
		cw.line("encode,")
		cw.line("new,")

		for e in object_type.get_entries():
			entry_name = NameConverter.object_entry_to_record_member(e)

			cw.newline()
			cw.start_line("get_")
			cw.append(entry_name)
			cw.append(",")
			cw.newline()

			cw.start_line("set_")
			cw.append(entry_name)
			cw.set_buffer(",")
			cw.mark_buffer_as_ending_line()
		cw.discard_buffer()
		cw.newline()

	def add_builder_function (
		cw: dragoman.CodeWriter,
		object_type: dragoman.ObjectType
	):
		cw.line("new: (")
		cw.increase_indent()
		cw.increase_indent()

		for e in object_type.get_entries():
			cw.start_line(NameConverter.type_to_type_reference(e.get_type()))
			cw.append(" ->")
			cw.newline()

		cw.line("Type")
		cw.decrease_indent()
		cw.line(")")
		cw.decrease_indent()

		cw.start_line("new ")

		for e in object_type.get_entries():
			cw.append(NameConverter.object_entry_to_variable(e))
			cw.append(" ")

		cw.append("=")
		cw.newline()
		cw.increase_indent()
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
		cw.line("}")
		cw.decrease_indent()

		cw.newline()

	def add_set_function (
		cw: dragoman.CodeWriter,
		ot: dragoman.ObjectType,
		ote: dragoman.ObjectTypeEntry
	):
		entry_name = NameConverter.object_entry_to_record_member(ote)

		cw.start_line("set_")
		cw.append(entry_name)
		cw.append(": ")
		cw.append(NameConverter.type_to_type_reference(ote.get_type()))
		cw.append(" -> Type -> Type")
		cw.newline()

		cw.start_line("set_")
		cw.append(entry_name)
		cw.append(" v e = {e | ")
		cw.append(entry_name)
		cw.append(" = v }")
		cw.newline()
		cw.newline()

	def add_get_function (
		cw: dragoman.CodeWriter,
		ot: dragoman.ObjectType,
		ote: dragoman.ObjectTypeEntry
	):
		entry_name = NameConverter.object_entry_to_record_member(ote)

		cw.start_line("get_")
		cw.append(entry_name)
		cw.append(": Type -> ")
		cw.append(NameConverter.type_to_type_reference(ote.get_type()))
		cw.newline()

		cw.start_line("get_")
		cw.append(entry_name)
		cw.append(" e = e.")
		cw.append(entry_name)
		cw.newline()
		cw.newline()

	def add_json_export_function (
		cw: dragoman.CodeWriter,
		object_type: dragoman.ObjectType
	):
		cw.line("encode: Type -> Json.Encode.Value")
		cw.line("encode e =")
		cw.increase_indent()
		cw.line("(Json.Encode.object")
		cw.increase_indent()
		cw.line("[")
		cw.increase_indent()

		for e in object_type.get_entries():
			et = e.get_type()

			cw.line("{")
			cw.increase_indent()
			cw.start_line("key = ")
			cw.append(NameConverter.object_entry_to_tag(e))
			cw.append(", ")
			cw.newline()

			value_access = "e." + NameConverter.object_entry_to_record_member(e)

			cw.start_line("value = ")
			if (isinstance(et, dragoman.ArrayOfDefinedType)):
				cw.append("(")
				cw.increase_indent()
				cw.newline()
				cw.line("(")
				cw.increase_indent()

				(depth, leaf_type) = et.compute_depth()

				if (isinstance(leaf_type, dragoman.UserDefinedType)):
					cw.start_line("(")
					cw.append(NameConverter.type_to_module_name(leaf_type))
					cw.append(".encode)")
					cw.newline()
				elif (isinstance(leaf_type, dragoman.DictOfDefinedType)):
					cw.start_line("(\ d -> (Json.Encode.array ")
					cw.append(
						NameConverter.type_to_module_name(leaf_type.get_parent())
					)
					cw.append(".encode (Dict.values d)))")
					cw.newline()
				else:
					type_name = leaf_type.get_name()

					if (type_name == "integer"):
						cw.line("(Json.Encode.int)")
					elif (type_name == "string"):
						cw.line("(Json.Encode.string)")
					elif (type_name == "float"):
						cw.line("(Json.Encode.float)")
					else:
						cw.line("(ENCODE_BASIC " + type_name + ")")

				for i in range(0, depth):
					cw.line("|> Json.Encode.array ")
				cw.decrease_indent()
				cw.line(")")
				cw.line(value_access)
				cw.decrease_indent()
				cw.line(")")
			elif (isinstance(et, dragoman.UserDefinedType)):
				cw.append("(")
				cw.append(NameConverter.type_to_module_name(et))
				cw.append(".encode ")
				cw.append(value_access)
				cw.append(")")
			else:
				type_name = et.get_name()

				if (type_name == "integer"):
					cw.append("(Json.Encode.int ")
				elif (type_name == "string"):
					cw.append("(Json.Encode.string ")
				elif (type_name == "float"):
					cw.append("(Json.Encode.float ")
				else:
					cw.append("(ENCODE_BASIC ")

				cw.append(value_access)
				cw.append(")")
			cw.newline()

			cw.decrease_indent()
			cw.start_line("}")
			cw.set_buffer(",")
			cw.mark_buffer_as_ending_line()

		cw.discard_buffer()
		cw.newline()
		cw.decrease_indent()
		cw.line("]")
		cw.decrease_indent()
		cw.line(")")
		cw.decrease_indent()
		cw.newline()

	def get_decoder_for (
		defined_type: dragoman.DefinedType
	):
		if (isinstance(defined_type, dragoman.ArrayOfDefinedType)):
			return (
				"(Json.Decode.array "
				+ ObjectTypeConverter.get_decoder_for(defined_type.get_parent())
				+ ")"
			)
		elif (isinstance(defined_type, dragoman.DictOfDefinedType)):
			parent_type = defined_type.get_parent()
			return (
				"(Json.Decode.map "
				+ "(Array.foldl (\ el acc -> (Dict.set ("
				+ NameConverter.type_to_module_name(parent_type)
				+ ".get_"
				+ defined_type.get_field_name()
				+ " el) el acc)) (Dict.empty)) (Json.Decode.array "
				+ ObjectTypeConverter.get_decoder_for(defined_type.get_parent())
				+ "))"
			)
		elif (isinstance(defined_type, dragoman.UserDefinedType)):
			return (
				NameConverter.type_to_module_name(defined_type)
				+ ".decoder"
			)
		else:
			name = defined_type.get_name().lower()

			if (name == "string"):
				return "Json.Decode.string"
			elif (name == "integer"):
				return "Json.Decode.int"
			elif (name == "float"):
				return "Json.Decode.float"
			elif (name == "boolean"):
				return "Json.Decode.bool"
			else:
				return "(NO DECODER FOR " + name + ")"

	def add_json_import_function (
		cw: dragoman.CodeWriter,
		object_type: dragoman.ObjectType
	):
		cw.line("decoder: (Json.Decode.Decoder Type)")
		cw.line("decoder =")
		cw.increase_indent()
		cw.line("(Json.Decode.succeed (new)")
		cw.increase_indent()

		for e in object_type.get_entries():
			cw.start_line("|> (Json.Decode.andMap (Json.Decode.field ")
			cw.append(NameConverter.object_entry_to_tag(e))
			cw.append(" ")
			cw.append(ObjectTypeConverter.get_decoder_for(e.get_type()))
			cw.append("))")
			cw.newline()
		cw.decrease_indent()
		cw.line(")")
		cw.decrease_indent()
		cw.newline()

	def convert (e: dragoman.ObjectType):
		code_writer = dragoman.CodeWriter(
			Path(dragoman.Dragoman.OUTPUT_FOLDER)
			/ NameConverter.type_to_filename(e)
		)

		code_writer.start_line("module ")
		code_writer.append(NameConverter.type_to_module_name(e))
		code_writer.append(" exposing")
		code_writer.newline()

		code_writer.increase_indent()
		code_writer.line("(")

		code_writer.increase_indent()
		ObjectTypeConverter.add_exports(code_writer, e)
		code_writer.decrease_indent()

		code_writer.line(")")
		code_writer.decrease_indent()
		code_writer.newline()

		code_writer.title_line("-", "", 0, 80)
		code_writer.title_line("-", " IMPORTS ", 2, 80)
		code_writer.title_line("-", "", 0, 80)
		code_writer.title_line("-", " Standard Library ", 2, 80)

		for a in e.get_entries():
			(depth, leaf_type) = dragoman.ArrayOfDefinedType.compute_depth(
				a.get_type()
			)

			if (isinstance(leaf_type, dragoman.DictOfDefinedType)):
				code_writer.line("import Dict")
				code_writer.newline()
				break

		code_writer.line("import Json.Decode")
		code_writer.line("import Json.Encode")
		code_writer.newline()

		code_writer.title_line("-", " Third Party ", 2, 80)
		code_writer.newline()

		code_writer.title_line("-", " Project ", 2, 80)

		for d in e.get_dependencies():
			code_writer.start_line("import ")
			code_writer.append(NameConverter.type_to_module_name(d))
			code_writer.newline()

		code_writer.newline()

		code_writer.title_line("-", "", 0, 80)
		code_writer.title_line("-", " TYPES ", 2, 80)
		code_writer.title_line("-", "", 0, 80)
		ObjectTypeConverter.add_type(code_writer, e)

		code_writer.title_line("-", "", 0, 80)
		code_writer.title_line("-", " LOCAL FUNCTIONS ", 2, 80)
		code_writer.title_line("-", "", 0, 80)
		code_writer.newline()

		code_writer.title_line("-", "", 0, 80)
		code_writer.title_line("-", " EXPORTED FUNCTIONS ", 2, 80)
		code_writer.title_line("-", "", 0, 80)

		ObjectTypeConverter.add_builder_function(code_writer, e)
		ObjectTypeConverter.add_json_export_function(code_writer, e)
		ObjectTypeConverter.add_json_import_function(code_writer, e)

		for i in e.get_entries():
			ObjectTypeConverter.add_get_function(code_writer, e, i)
			ObjectTypeConverter.add_set_function(code_writer, e, i)

		code_writer.finalize()

class EnumTypeConverter:
	def add_type (
		cw: dragoman.CodeWriter,
		enum_type: dragoman.EnumType
	):
		cw.line("type Type =")
		cw.increase_indent()
		first = True

		for e in enum_type.get_entries():
			cw.start_line("")

			if first:
				first = False
			else:
				cw.append("| ")

			cw.append(NameConverter.enum_entry_to_atom(e))
			cw.newline()
		cw.decrease_indent()
		cw.newline()

	def add_exports (
		cw: dragoman.CodeWriter,
		enum_type: dragoman.EnumType
	):
		cw.line("Type,")
		cw.line("decoder,")
		cw.line("encode,")
		cw.line("new,")
		cw.line("get_value,")
		cw.line("maybe_from_value")

	def add_json_export_function (
		cw: dragoman.CodeWriter,
		enum_type: dragoman.EnumType
	):
		parent_type_name = enum_type.get_parent_type().get_name().lower()

		cw.line("encode: Type -> Json.Encode.Value")
		cw.start_line("encode e = (Json.Encode.")

		if (parent_type_name == "integer"):
			cw.append("int ")
		elif (parent_type_name == "string"):
			cw.append("string ")
		else:
			cw.append("(NO ENCODE FOR " + parent_type_name + ")")

		cw.append("(get_value e))")
		cw.newline()
		cw.newline()

	def add_get_value_function (
		cw: dragoman.CodeWriter,
		enum_type: dragoman.EnumType
	):
		parent_type_name = enum_type.get_parent_type().get_name().lower()

		cw.start_line("get_value: Type -> ")

		if (parent_type_name == "integer"):
			cw.append("Int")
		elif (parent_type_name == "string"):
			cw.append("String ")
		else:
			cw.append("(NO ENCODE FOR " + parent_type_name + ")")

		cw.newline()

		cw.line("get_value e =")
		cw.increase_indent()
		cw.line("when e is")
		cw.increase_indent()

		for e in enum_type.get_entries():
			name = NameConverter.enum_entry_to_atom(e)

			cw.start_line(name)
			cw.append(" -> ")
			cw.append(NameConverter.enum_entry_to_value(e))
			cw.newline()

		cw.newline()
		cw.decrease_indent()
		cw.decrease_indent()

	def add_from_value_function (
		cw: dragoman.CodeWriter,
		enum_type: dragoman.EnumType
	):
		parent_type_name = enum_type.get_parent_type().get_name().lower()

		cw.start_line("maybe_from_value: ")

		if (parent_type_name == "integer"):
			cw.append("Int")
		elif (parent_type_name == "string"):
			cw.append("String ")
		else:
			cw.append("(NO ENCODE FOR " + parent_type_name + ")")
		cw.append(" -> (Maybe Type)")
		cw.newline()

		cw.line("maybe_from_value v =")
		cw.increase_indent()
		cw.line("when v is")
		cw.increase_indent()

		for e in enum_type.get_entries():
			name = NameConverter.enum_entry_to_atom(e)

			cw.start_line(NameConverter.enum_entry_to_value(e))
			cw.append(" -> (Just ")
			cw.append(name)
			cw.append(")")

			cw.newline()

		cw.line("_ -> Nothing")
		cw.newline()
		cw.newline()
		cw.decrease_indent()
		cw.decrease_indent()

	def add_json_import_function (
		cw: dragoman.CodeWriter,
		enum_type: dragoman.EnumType
	):
		parent_type_name = enum_type.get_parent_type().get_name().lower()

		cw.line("decoder: (Json.Decode.decoder Type)")
		cw.line("decoder =")
		cw.increase_indent()
		cw.line("(Json.Decode.andThen")
		cw.increase_indent()
		cw.line("(\\maybe_value ->")
		cw.increase_indent()
		cw.line("when maybe_value is")
		cw.increase_indent()
		cw.line("(Just value) -> (Json.Decode.succeed value)")
		cw.line("_ -> (Json.Decode.fail \"Invalid value\")")
		cw.decrease_indent()
		cw.decrease_indent()
		cw.line(")")
		cw.start_line("(Json.Decode.map (maybe_from_value) Json.Decode.")

		if (parent_type_name == "integer"):
			cw.append("int)")
		elif (parent_type_name == "string"):
			cw.append("string)")
		else:
			cw.append("(NO ENCODE FOR " + parent_type_name + "))")
		cw.newline()
		cw.decrease_indent()
		cw.line(")")
		cw.decrease_indent()
		cw.newline()

	def convert (e: dragoman.EnumType):
		code_writer = dragoman.CodeWriter(
			Path(dragoman.Dragoman.OUTPUT_FOLDER)
			/ NameConverter.type_to_filename(e)
		)

		code_writer.start_line("module ")
		code_writer.append(NameConverter.type_to_module_name(e))
		code_writer.append(" exposing")
		code_writer.newline()

		code_writer.increase_indent()
		code_writer.line("(")

		code_writer.increase_indent()
		EnumTypeConverter.add_exports(code_writer, e)
		code_writer.decrease_indent()

		code_writer.line(")")
		code_writer.decrease_indent()
		code_writer.newline()

		code_writer.title_line("-", "", 0, 80)
		code_writer.title_line("-", " IMPORTS ", 2, 80)
		code_writer.title_line("-", "", 0, 80)
		code_writer.title_line("-", " Standard Library ", 2, 80)
		code_writer.line("import Json.Decode")
		code_writer.line("import Json.Encode")
		code_writer.newline()

		code_writer.title_line("-", " Third Party ", 2, 80)
		code_writer.newline()

		code_writer.title_line("-", " Project ", 2, 80)
		code_writer.newline()

		code_writer.title_line("-", "", 0, 80)
		code_writer.title_line("-", " TYPES ", 2, 80)
		code_writer.title_line("-", "", 0, 80)
		EnumTypeConverter.add_type(code_writer, e)

		code_writer.title_line("-", "", 0, 80)
		code_writer.title_line("-", " LOCAL FUNCTIONS ", 2, 80)
		code_writer.title_line("-", "", 0, 80)
		code_writer.newline()

		code_writer.title_line("-", "", 0, 80)
		code_writer.title_line("-", " EXPORTED FUNCTIONS ", 2, 80)
		code_writer.title_line("-", "", 0, 80)

		EnumTypeConverter.add_json_export_function(code_writer, e)
		EnumTypeConverter.add_json_import_function(code_writer, e)
		EnumTypeConverter.add_get_value_function(code_writer, e)
		EnumTypeConverter.add_from_value_function(code_writer, e)

		code_writer.finalize()

class PolymorphTypeConverter:
	def add_type (
		cw: dragoman.CodeWriter,
		polymorph_type: dragoman.PolymorphType
	):
		cw.line("type Type =")
		cw.increase_indent()
		first = True

		for e in polymorph_type.get_cases():
			cw.start_line("")

			if first:
				first = False
			else:
				cw.append("| ")

			cw.append(NameConverter.polymorph_case_to_atom(e))
			cw.append(" ")
			cw.append(NameConverter.type_to_type_reference(e.get_type()))
			cw.newline()
		cw.decrease_indent()
		cw.newline()

	def add_exports (
		cw: dragoman.CodeWriter,
		polymorph_type: dragoman.PolymorphType
	):
		cw.line("Type,")
		cw.line("decoder,")
		cw.line("encode")

	def add_json_export_function (
		cw: dragoman.CodeWriter,
		polymorph_type: dragoman.PolymorphType
	):
		cw.line("encode: Type -> Json.Encode.Value")
		cw.line("encode e =")
		cw.increase_indent()
		cw.line("when e is")
		cw.increase_indent()

		for pcase in polymorph_type.get_cases():
			name = NameConverter.polymorph_case_to_atom(pcase)

			cw.start_line("(")
			cw.append(name)
			cw.append(" v) -> (")
			cw.append(NameConverter.type_to_module_name(pcase.get_type()))
			cw.append(".encode v)")
			cw.newline()
		cw.newline()
		cw.decrease_indent()
		cw.decrease_indent()

	def add_json_import_function (
		cw: dragoman.CodeWriter,
		polymorph_type: dragoman.PolymorphType
	):
		etype = polymorph_type.get_enum_type()

		cw.line("decoder -> (Json.Decode.decoder Type)")
		cw.line("decoder =")
		cw.increase_indent()
		cw.line("(Json.Decode.andThen")
		cw.increase_indent()
		cw.line("(\\value ->")
		cw.increase_indent()
		cw.line("when value is")
		cw.increase_indent()
		for pcase in polymorph_type.get_cases():
			eentry = pcase.get_enum_entry()
			cw.start_line(NameConverter.enum_entry_to_value(eentry))
			cw.append(" -> (Json.Decode.map (\\a -> (")
			cw.append(NameConverter.polymorph_case_to_atom(pcase))
			cw.append(" a)) (")
			cw.append(NameConverter.type_to_module_name(pcase.get_type()))
			cw.append(".decoder))")
			cw.newline()

		cw.line("_ -> (Json.Decode.fail \"Invalid Value.\")")
		cw.decrease_indent()
		cw.decrease_indent()
		cw.line(")")

		cw.start_line("(Json.Decode.field \"")
		cw.append(polymorph_type.get_key_field_tag())
		cw.append("\" (")
		cw.append(NameConverter.type_to_module_name(etype))
		cw.append(".decoder))")
		cw.newline()
		cw.decrease_indent()
		cw.line(")")
		cw.decrease_indent()
		cw.newline()

	def convert (e: dragoman.PolymorphType):
		code_writer = dragoman.CodeWriter(
			Path(dragoman.Dragoman.OUTPUT_FOLDER)
			/ NameConverter.type_to_filename(e)
		)

		code_writer.start_line("module ")
		code_writer.append(NameConverter.type_to_module_name(e))
		code_writer.append(" exposing")
		code_writer.newline()

		code_writer.increase_indent()
		code_writer.line("(")

		code_writer.increase_indent()
		PolymorphTypeConverter.add_exports(code_writer, e)
		code_writer.decrease_indent()

		code_writer.line(")")
		code_writer.decrease_indent()
		code_writer.newline()

		code_writer.title_line("-", "", 0, 80)
		code_writer.title_line("-", " IMPORTS ", 2, 80)
		code_writer.title_line("-", "", 0, 80)
		code_writer.title_line("-", " Standard Library ", 2, 80)
		code_writer.line("import Json.Decode")
		code_writer.line("import Json.Encode")
		code_writer.newline()

		code_writer.title_line("-", " Third Party ", 2, 80)
		code_writer.newline()

		code_writer.title_line("-", " Project ", 2, 80)

		for d in e.get_dependencies():
			code_writer.start_line("import ")
			code_writer.append(NameConverter.type_to_module_name(d))
			code_writer.newline()

		code_writer.newline()

		code_writer.title_line("-", "", 0, 80)
		code_writer.title_line("-", " TYPES ", 2, 80)
		code_writer.title_line("-", "", 0, 80)
		PolymorphTypeConverter.add_type(code_writer, e)

		code_writer.title_line("-", "", 0, 80)
		code_writer.title_line("-", " LOCAL FUNCTIONS ", 2, 80)
		code_writer.title_line("-", "", 0, 80)
		code_writer.newline()

		code_writer.title_line("-", "", 0, 80)
		code_writer.title_line("-", " EXPORTED FUNCTIONS ", 2, 80)
		code_writer.title_line("-", "", 0, 80)

		PolymorphTypeConverter.add_json_export_function(code_writer, e)
		PolymorphTypeConverter.add_json_import_function(code_writer, e)

		code_writer.finalize()

class Dragoman2Gren:
	def initialize ():
		dragoman.CodeWriter.DEFAULT_INDENT = "   "

		argparser = dragoman.Dragoman.initialize()
		args = argparser.parse_args()

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
	Dragoman2Gren.initialize()
	Dragoman2Gren.export()
