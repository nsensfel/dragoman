#!/bin/env python3

import dragoman

def generate_record (object_type):
	result = "-record\n(\n\t"
	result += object_type.get_name().lower()
	result += ",\n\t{\n"
	for e in object_type.get_entries():
		result += "\t\t"
		result += e.get_name().lower()
		result += " :: "
		result += e.get_type().get_name().lower()
		result += "(),\n"
	result += "\t}\n)."

	return result

def generate_enum_type (enum_type):
	result = "-type "
	result += enum_type.get_name().lower()
	result += "() :: "

	for e in enum_type.get_entries():
		result += "'"
		result += e.get_name().lower()
		result += "' | "

	result += "."

	return result

def generate_polymorph_type (enum_type):
	result = "-type "
	result += enum_type.get_name().lower()
	result += "() :: "

	for e in enum_type.get_cases().values():
		result += e.get_type().get_name().lower()
		result += "() | "

	result += "."

	return result

if __name__ == '__main__':
	t0 = dragoman.DefinedType("string")
	t0.register()

	t0 = dragoman.DefinedType("integer")
	t0.register()

	dragoman.DragomanParser.parse_file('test')

	for e in dragoman.EnumType.get_all():
		print(generate_enum_type(e))

	print("\n---- Object Types:")
	for e in dragoman.ObjectType.get_all():
		print(generate_record(e))

	print("\n---- Polymorph Types:")
	for e in dragoman.PolymorphType.get_all():
		print(generate_polymorph_type(e))
