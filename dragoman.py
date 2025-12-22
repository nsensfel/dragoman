#!/bin/env python3

from sly import Lexer, Parser

import sys

from pathlib import Path

################################################################################
#### LOG / TERMINAL OUTPUT #####################################################
################################################################################
class Log:
	ERRORS = 0
	WARNINGS = 0

	def print_error (*args, **kwargs):
		print(*args, file=sys.stderr, **kwargs)
		Log.ERRORS += 1

	def print_warning (*args, **kwargs):
		print(*args, file=sys.stderr, **kwargs)
		Log.WARNINGS += 1

	def print(*args, **kwargs):
		print(*args, **kwargs)

	def print_debug (*args, **kwargs):
		print(*args, **kwargs)

	def print_summary ():
		Log.print(
			"Completed with "
			+ str(Log.ERRORS)
			+ " error(s) and "
			+ str(Log.WARNINGS)
			+ " warning(s)."
		)

################################################################################
#### IN-PLACE TYPO FIXING ######################################################
################################################################################
class TypoFixer:
	ACCEPTED_FIXES = dict()

	def deconstruct (string: str) -> dict[str, int]:
		result = dict()
		chars = [char for char in string.lower()]

		for char in chars:
			if (char in result):
				result[char] += 1
			else:
				result[char] = 1

		return result

	def compare_deconstructed (a: dict[str, int], b: dict[str, int]) -> int:
		result = 0
		keys = set()
		keys.update(a.keys())
		keys.update(b.keys())

		for k in keys:
			in_a = 0
			in_b = 0

			if k in a:
				in_a = a[k]

			if k in b:
				in_b = b[k]

			result += abs(in_a - in_b)

		return result

	def find_closest_to (target: str, candidates: list[str], percent) -> list[(str, int)]:
		target_len = len(target)
		max_distance = max(target_len * percent, 3)
		max_candidate_len = target_len + max_distance
		min_candidate_len = target_len - max_distance
		result = list()

		deconstructed_target = TypoFixer.deconstruct(target)

		for c in candidates:
			c_len = len(c)

			if (
				(c_len >= min_candidate_len)
				and (c_len <= max_candidate_len)
			):
				c_score = TypoFixer.compare_deconstructed(
					deconstructed_target,
					TypoFixer.deconstruct(c)
				)

				if (c_score <= max_distance):
					result.append((c, c_score))

		def get_score (a: (str, int)) -> int:
			(v, result) = a

			return result

		result.sort(key = get_score)

		return [a for (a, b) in result]

	def propose_fix (
		token,
		group_name: str,
		target: str,
		candidates: list[str]
	) -> str | None:
		current_fix = TypoFixer.ACCEPTED_FIXES.get(target)

		if (current_fix is not None):
			return current_fix

		candidates = TypoFixer.find_closest_to(target, candidates, 0.25)
		if (len(candidates) == 0):
			return None

		prompt = DragomanParser.get_cursor(token)
		prompt += "\n[?] Unknown "
		prompt += group_name
		prompt += " \""
		prompt += target
		prompt += "\".\nClosest candidates are:\n"

		for i in range(0, len(candidates)):
			prompt += str(i)
			prompt += ". "
			prompt += candidates[i]
			prompt += "\n"

		prompt += "\nEnter number of the candidate to replace \""
		prompt += target
		prompt += "\" with, or -1 to cancel: "

		prompt_prefix = ""

		while True:
			choice = int(input(prompt_prefix + prompt))
			prompt_prefix = ""

			if (choice == -1):
				return None

			if ((choice >= 0) and (choice < len(candidates))):
				choice = candidates[choice]
				TypoFixer.ACCEPTED_FIXES[target] = choice

				return choice
			else:
				prompt_prefix = "\"" + str(choice) + "\" is out of range.\n"
				choice = None

	def apply_fix (
		filename,
		t,
		target: str,
		replacement: str
	):
		data = []

		DragomanParser.print_warning(
			(
				"Replacing \""
				+ target
				+ "\" with \""
				+ replacement
				+ "\"."
			),
			t
		)

		with open(filename, 'r') as file:
			data = file.readlines()

		data[t.lineno - 1] = data[t.lineno - 1].replace(target, replacement, 1)

		with open(filename, 'w') as file:
			file.writelines(data)

################################################################################
#### CODE GENERATION UTILITY ###################################################
################################################################################
class CodeWriter:

	def __init__ (this, filename: str):
		this.file = open(filename, 'w')
		this.indent_style = "\t"
		this.indent_level = 0
		this.buffer = None
		this.buffer_ends_line = False

	def decrease_indent (this):
		if (this.indent_level == 0):
			Log.print_warning("Unable to lower indent level further.")
		else:
			this.indent_level -= 1

	def increase_indent (this):
		this.indent_level += 1

	def indent (this):
		this.file.write(this.indent_style * this.indent_level)

	def discard_buffer (this):
		this.buffer = None
		this.buffer_ends_line = False

	def write_buffer (this):
		this.file.write(this.buffer)

		if (this.buffer_ends_line):
			this.file.write("\n")

		this.discard_buffer()

	def mark_buffer_as_ending_line (this):
		this.buffer_ends_line = True

	def set_buffer (this, s: str):
		this.buffer = s

	def append (this, s: str):
		if (this.buffer is not None):
			this.write_buffer()

		this.file.write(s)

	def newline (this):
		if (this.buffer is not None):
			this.write_buffer()

		this.file.write("\n")

	def start_line (this, s: str):
		if (this.buffer is not None):
			this.write_buffer()

		this.indent()
		this.file.write(s)

	def line (this, s: str):
		if (this.buffer is not None):
			this.write_buffer()

		this.indent()
		this.file.write(s)
		this.newline()

	def finalize (this):
		if (this.buffer is not None):
			this.write_buffer()

		this.file.close()

class TokenLocation:
	def __init__ (this, token):
		this.filename = DragomanParser.CURRENT_FILE
		this.line = token.lineno
		this.column = token.index - DragomanParser.COLUMN_STARTS_AT

		if (this.column < 0):
			this.column = 0

	def get_filename (this) -> str:
		return this.filename

	def get_line (this) -> int:
		return this.line

	def get_column (this) -> int:
		return this.column

	def to_string (this) -> str:
		return (
			this.get_filename()
			+ ":"
			+ str(this.get_line())
			+ ","
			+ str(this.get_column())
		)

class DefinedType:
	COLLECTION = dict()

	def get (name: str):
		return DefinedType.COLLECTION[name]

	def get_all ():
		return DefinedType.COLLECTION.values()

	def maybe_get (name: str):
		return DefinedType.COLLECTION.get(name)

	def __init__ (this, name: str):
		this.name = name

	def get_name (this) -> str:
		return this.name

	def register (this):
		if (this.name in DefinedType.COLLECTION):
			return False
		else:
			DefinedType.COLLECTION[this.name] = this

			return True

	def to_string (this):
		return this.name

class ArrayOfDefinedType (DefinedType):
	def __init__ (this, parent):
		DefinedType.__init__(this, "(Array of " + parent.get_name() + ")")
		this.parent = parent

	def get_parent (this):
		return parent

class UserDefinedType (DefinedType):
	COLLECTION = dict()

	def get (name: str):
		return UserDefinedType.COLLECTION[name]

	def get_all ():
		return UserDefinedType.COLLECTION.values()

	def maybe_get (name: str):
		return UserDefinedType.COLLECTION.get(name)

	def __init__ (this, token: TokenLocation, name: str):
		DefinedType.__init__(this, name)
		this.token = token

	def get_token (this) -> TokenLocation:
		return this.token

	def register (this):
		candidate = DefinedType.maybe_get(this.name)

		if (candidate is not None):
			if (isinstance(candidate, UserDefinedType)):
				Log.print_error(
					"Name collision for types '"
					+ this.name
					+ "', defined at:\n- "
					+ candidate.token.to_string()
					+ "\n-"
					+ this.token.to_string()
				)
			else:
				Log.print_error(
					"Type definition at "
					+ this.token.to_string()
					+ " collides with base type name."
				)

			return False

		DefinedType.register(this)
		UserDefinedType.COLLECTION[this.name] = this
		return True

class ObjectTypeEntry:
	def __init__ (
		this,
		token: TokenLocation,
		name: str,
		tag: str,
		dtype: DefinedType
	):
		this.token = token
		this.name = name
		this.tag = tag
		this.dtype = dtype

	def get_token (this) -> TokenLocation:
		return this.token

	def get_name (this) -> str:
		return this.name

	def get_tag (this) -> str:
		return this.tag

	def get_type (this) -> DefinedType:
		return this.dtype

	def to_string (this):
		return (
			"(entry "
			+ this.get_name()
			+ " "
			+ this.get_tag()
			+ " "
			+ this.get_type().get_name()
			+ ")"
		)

class ObjectType (UserDefinedType):
	COLLECTION = dict()

	def get (name: str):
		return ObjectType.COLLECTION[name]

	def get_all ():
		return ObjectType.COLLECTION.values()

	def maybe_get (name: str):
		return ObjectType.COLLECTION.get(name)

	def __init__ (this, token: TokenLocation, name: str, entries: list()):
		UserDefinedType.__init__(this, token, name)
		this.entry_from_tag = dict()
		this.entry_from_name = dict()
		this.dependencies = set() # Types to include so members are defined.

		for entry in entries:
			this.entry_from_name[entry.get_name()] = entry
			this.entry_from_tag[entry.get_tag()] = entry

			dependency = entry.get_type()

			while (isinstance(dependency, ArrayOfDefinedType)):
				dependency = dependency.get_parent()

			if (isinstance(dependency, UserDefinedType)):
				this.dependencies.add(dependency)

	def register (this):
		if (UserDefinedType.register(this)):
			ObjectType.COLLECTION[this.name] = this
			return True
		else:
			return False

	def get_entry_from_name (this, name: str) -> ObjectTypeEntry:
		return this.entry_from_name[name]

	def get_entry_from_tag (this, tag: str) -> ObjectTypeEntry:
		return this.entry_from_tag[tag]

	def get_entries (this) -> list[ObjectTypeEntry]:
		return this.entry_from_tag.values()

	def get_dependencies (this) -> set[UserDefinedType]:
		return this.dependencies

	def to_string (this):
		result = "(object " + this.get_name()

		for e in this.get_entries():
			result += "\n\t" + e.to_string()

		result += "\n)"

		return result

class EnumTypeEntry:
	def __init__ (
		this,
		token: TokenLocation,
		name: str,
		tag: str,
	):
		this.token = token
		this.name = name
		this.tag = tag

	def get_token (this) -> TokenLocation:
		return this.token

	def get_name (this) -> str:
		return this.name

	def get_tag (this) -> str:
		return this.tag

	def to_string (this):
		return (
			"(entry "
			+ this.get_name()
			+ " "
			+ this.get_tag()
			+ ")"
		)

class EnumType (UserDefinedType):
	COLLECTION = dict()

	def get (name: str):
		return EnumType.COLLECTION[name]

	def get_all ():
		return EnumType.COLLECTION.values()

	def maybe_get (name: str):
		return EnumType.COLLECTION.get(name)

	def __init__ (
		this,
		token: TokenLocation,
		name: str,
		parent_type: DefinedType,
		entries: list[EnumTypeEntry]
	):
		UserDefinedType.__init__(this, token, name)
		this.parent_type = parent_type
		this.entry_from_tag = dict()
		this.entry_from_name = dict()

		for entry in entries:
			this.entry_from_name[entry.get_name()] = entry
			this.entry_from_tag[entry.get_tag()] = entry

	def get_parent_type (this) -> DefinedType:
		return this.parent_type

	def get_entries (this) -> list[EnumTypeEntry]:
		return this.entry_from_tag.values()

	def get_entry_from_name (this, name: str) -> EnumTypeEntry:
		return this.entry_from_name[name]

	def get_entry_from_tag (this, tag: str) -> EnumTypeEntry:
		return this.entry_from_tag[tag]

	def register (this):
		if (UserDefinedType.register(this)):
			EnumType.COLLECTION[this.name] = this
			return True
		else:
			return False

	def to_string (this):
		result = "(enum " + this.get_name()

		for e in this.get_entries():
			result += "\n\t" + e.to_string()

		result += "\n)"

		return result

class PolymorphTypeCase:
	def __init__ (
		this,
		token: TokenLocation,
		name: str,
		dtype: DefinedType
	):
		this.token = token
		this.name = name
		this.dtype = dtype

	def get_token (this) -> TokenLocation:
		return this.token

	def get_name (this) -> str:
		return this.name

	def get_type (this) -> DefinedType:
		return this.dtype

	def to_string (this):
		return (
			"(case "
			+ this.get_name()
			+ " "
			+ this.get_type().get_name()
			+ ")"
		)

class PolymorphType (UserDefinedType):
	COLLECTION = dict()

	def get (name: str):
		return PolymorphType.COLLECTION[name]

	def get_all ():
		return PolymorphType.COLLECTION.values()

	def maybe_get (name: str):
		return PolymorphType.COLLECTION.get(name)

	def __init__ (
		this,
		token: TokenLocation,
		name: str,
		tag: str,
		cases: dict()
	):
		UserDefinedType.__init__(this, token, name)
		this.tag = tag
		this.cases = cases

	def get_tag (this) -> str:
		return this.tag

	def get_cases (this) -> dict():
		return this.cases

	def register (this):
		if (UserDefinedType.register(this)):
			PolymorphType.COLLECTION[this.name] = this
			return True
		else:
			return False

	def to_string (this):
		result = "(polymorph " + this.get_name()

		for e in this.get_cases().values():
			result += "\n\t" + e.to_string()

		result += "\n)"

		return result

class DragomanLexer (Lexer):
	tokens = {
		#NUMBER,
		ID,

		ARRAY_KW,
		CASE_KW,
		ENTRY_KW,
		ENUM_KW,
		#MAX_KW,
		#MIN_KW,
		OBJECT_KW,
		POLYMORPH_KW,
		REQUIRE_KW,

		EOP,
	}

	#@_(r'[\-]?\d+')
	#def NUMBER (this, t):
	#	t.value = int(t.value)
	#	return t

	ID = r'\+|\-|([\&a-zA-Z_,.%/#\':][\&a-zA-Z_0-9,.\-%#/\+\':]*)'

	ARRAY_KW = r'(?i:\(ARRAY)'
	CASE_KW = r'(?i:\(CASE)'
	ENTRY_KW = r'(?i:\(ENTRY)'
	ENUM_KW = r'(?i:\(ENUM)(?i:ERATE)?'
	#MAX_KW = r'(?i:\(MAX)(?i:IMUM)?'
	#MIN_KW = r'(?i:\(MIN)(?i:IMUM)?'
	OBJECT_KW = r'(?i:\(OBJECT)'
	POLYMORPH_KW = r'(?i:\(POLY)(?i:MORPH)?'
	REQUIRE_KW = r'(?i:\(REQUIRE)'

	EOP = r'\)'


	ignore_comments = r';;.*'

	@_('\r?\n')
	def ignore_newline (this, t):
		this.lineno += 1
		DragomanParser.COLUMN_STARTS_AT = this.index

	ignore = ' \t'

	def error (this, t):
		Log.print_error(
			"Syntax error. Unexpected \"" + str(t.value) + "\".",
			DragomanParser.get_cursor(t)
		)
		raise Exception

class DragomanParser (Parser):
	COLUMN_STARTS_AT = 0
	CURRENT_FILE = None
	LAST_TOKEN = None
	PARSED_FILES = set()

	tokens = DragomanLexer.tokens

	def get_cursor (t, use_column = True) -> str:
		column = t.index - DragomanParser.COLUMN_STARTS_AT
		result = DragomanParser.CURRENT_FILE
		result += ":" + str(t.lineno)

		if (use_column):
			result += "," + str(column)

		result += "\n"

		with open(DragomanParser.CURRENT_FILE, 'r') as file:
			line_content = file.readlines()[t.lineno - 1][:-1]

		result += line_content.replace("\t", " ")
		result += "\n"

		if (use_column):
			result += ' ' * column + "^"
		else:
			result += len(line_content) * "^"

		result += "\n"

		return result

	def print_warning (msg, t):
		if (isinstance(t, TokenLocation)):
			Log.print_error(
				"[W] "
				+ msg
				+ "\n"
				+ t.to_string()
			)
		else:
			Log.print_error(
				"[W] "
				+ msg
				+ "\n"
				+ DragomanParser.get_cursor(t, False)
			)

	def print_error (msg, t):
		if (isinstance(t, TokenLocation)):
			Log.print_error(
				"[E] "
				+ msg
				+ "\n"
				+ t.to_string()
			)
		else:
			Log.print_error(
				"[E] "
				+ msg
				+ "\n"
				+ DragomanParser.get_cursor(t, False)
			)

	#### FILE ###################################################################
	@_(r'file_entry file')
	def file (this, t):
		DragomanParser.LAST_TOKEN = t

		return t

	@_(r'')
	def file (this, t):
		DragomanParser.LAST_TOKEN = t

		return t

	@_(r'REQUIRE_KW ID EOP')
	def file_entry (this, t):
		DragomanParser.LAST_TOKEN = t

		# It would be cleaner not to go for a static solution, but oh well...
		COLUMN_STARTS_AT = DragomanParser.COLUMN_STARTS_AT
		CURRENT_FILE = DragomanParser.CURRENT_FILE
		LAST_TOKEN = DragomanParser.LAST_TOKEN

		DragomanParser.parse_file(t.ID)

		DragomanParser.COLUMN_STARTS_AT = COLUMN_STARTS_AT
		DragomanParser.CURRENT_FILE = CURRENT_FILE
		DragomanParser.LAST_TOKEN = LAST_TOKEN

		return t

	@_(r'ENUM_KW ID get_type enum_definition EOP')
	def file_entry (this, t):
		DragomanParser.LAST_TOKEN = t

		(tags, names, entries) = t.enum_definition

		result = EnumType(TokenLocation(t), t.ID, t.get_type, entries)

		result.register()

		return t

	@_(r'OBJECT_KW ID object_definition EOP')
	def file_entry (this, t):
		DragomanParser.LAST_TOKEN = t

		(tags, names, entries) = t.object_definition

		result = ObjectType(TokenLocation(t), t.ID, entries)

		result.register()

		return t

	@_(r'POLYMORPH_KW ID ID polymorph_definition EOP')
	def file_entry (this, t):
		DragomanParser.LAST_TOKEN = t

		enum_type = None

		a = dict()

		for (k, v) in t.polymorph_definition.items():
			entry = v.get_type()

			if (not isinstance(entry, ObjectType)):
				DragomanParser.print_error(
					"Invalid type used for polymorph case.",
					v.get_token()
				)
				raise Exception

			try:
				entry = entry.get_entry_from_tag(t.ID1)
			except Exception:
				DragomanParser.print_error(
					(
						"Type '"
						+ entry.get_name()
						+ "' does not have entry '"
						+ t.ID1
						+ "'."
					),
					v.get_token()
				)
				raise Exception

			if (enum_type == None):
				enum_type = entry.get_type()
			elif (enum_type != entry.get_type()):
				DragomanParser.print_error(
					(
						"Entry '"
						+ t.ID1
						+ "' of target type does not use the same Enum type as "
						+ " previous entries."
					),
					v.get_token()
				)
				raise Exception

			try:
				entry = enum_type.get_entry_from_name(v.get_name())
			except Exception:
				DragomanParser.print_error(
					(
						"The Enum type '"
						+ enum_type.get_name()
						+ "' does not have any entry named '"
						+ v.get_name()
						+ "'."
					),
					v.get_token()
				)
				raise Exception

		if (enum_type is None):
			DragomanParser.print_error(
				"No cases defined in Polymorph type.",
				t.POLYMORPH_KW
			)
			raise Exception

		result = PolymorphType(
			TokenLocation(t),
			t.ID0,
			enum_type,
			t.polymorph_definition
		)

		result.register()

		return t

	#### GET DEFINED OBJECT #####################################################
	@_(r'ID')
	def get_type (this, t):
		DragomanParser.LAST_TOKEN = t

		try:
			return DefinedType.get(t.ID)
		except Exception as e:
			fixed_id = TypoFixer.propose_fix(
				t,
				"Type",
				t.ID,
				[i.get_name() for i in DefinedType.get_all()]
			)

			if (fixed_id is None):
				raise e
			else:
				TypoFixer.apply_fix(DragomanParser.CURRENT_FILE, t, t.ID, fixed_id)

				return DefinedType.get(fixed_id)
		except Exception as e:
			raise e

	@_(r'ARRAY_KW get_type EOP')
	def get_type (this, t):
		DragomanParser.LAST_TOKEN = t

		return ArrayOfDefinedType(t.get_type)

	#### OBJECT #################################################################
	@_(r'')
	def object_definition (this, t):
		DragomanParser.LAST_TOKEN = t

		return (set(), set(), list())

	@_(r'ENTRY_KW ID ID get_type EOP object_definition')
	def object_definition (this, t):
		DragomanParser.LAST_TOKEN = t

		(names, tags, entries) = t.object_definition

		result = ObjectTypeEntry(
			TokenLocation(t),
			t.ID0,
			t.ID1,
			t.get_type,
		)

		if (result.get_name() in names):
			DragomanParser.print_error(
				"Duplicate name '" + result.get_name() + "'",
				t.ENTRY_KW
			)
			raise Exception

		if (result.get_tag() in tags):
			DragomanParser.print_error(
				"Duplicate tag '" + result.get_tag() + "'",
				t.ENTRY_KW
			)
			raise Exception

		names.add(result.get_name())
		tags.add(result.get_tag())
		entries.append(result)

		return (names, tags, entries)

	#### ENUM ###################################################################
	@_(r'')
	def enum_definition (this, t):
		DragomanParser.LAST_TOKEN = t

		return (set(), set(), list())

	@_(r'ENTRY_KW ID ID EOP enum_definition')
	def enum_definition (this, t):
		DragomanParser.LAST_TOKEN = t

		(names, tags, entries) = t.enum_definition

		result = EnumTypeEntry(TokenLocation(t), t.ID0, t.ID1)

		if (result.get_name() in names):
			DragomanParser.print_error(
				"Duplicate name '" + result.get_name() + "'",
				t.ENTRY_KW
			)
			raise Exception

		if (result.get_tag() in tags):
			DragomanParser.print_error(
				"Duplicate tag '" + result.get_tag() + "'",
				t.ENTRY_KW
			)
			raise Exception

		names.add(result.get_name())
		tags.add(result.get_tag())
		entries.append(result)

		return (names, tags, entries)

	#### POLYMORPH ##############################################################
	@_(r'')
	def polymorph_definition (this, t):
		DragomanParser.LAST_TOKEN = t

		return dict()

	@_(r'CASE_KW ID get_type EOP polymorph_definition')
	def polymorph_definition (this, t):
		DragomanParser.LAST_TOKEN = t

		result = PolymorphTypeCase(TokenLocation(t), t.ID, t.get_type)

		if (result.get_name() in t.polymorph_definition):
			DragomanParser.print_error(
				"Duplicate case '" + result.get_name() + "'",
				t.CASE_KW
			)
			raise Exception

		t.polymorph_definition[result.get_name()] = result

		return t.polymorph_definition

	#############################################################################
	def error (this, t):
		Log.print_error(
			"Syntax error. Unexpected \"" + str(t.value) + "\".",
			DragomanParser.get_cursor(t)
		)
		raise Exception

	def parse_file (filename):
		filename = './example/' + filename + ".dgl"
		module_name = Path(filename).stem
		if (module_name in DragomanParser.PARSED_FILES):
			Log.print_debug(
				"Module "
				+ module_name
				+ " already parsed, skipping file "
				+ filename
				+ "."
			)
		else:
			# Needs to search all include directories/subdirectories
			with open(filename, 'r') as file:
				Log.print_debug("Parsing " + filename + "...")

				lexer = DragomanLexer()
				parser = DragomanParser()
				DragomanParser.CURRENT_FILE = filename

				try:
					parser.parse(lexer.tokenize(file.read()))
				except Exception as e:
					DragomanParser.print_error(str(e), DragomanParser.LAST_TOKEN)
					file.close()
					raise e

				file.close()

			DragomanParser.PARSED_FILES.add(module_name)
			Log.print_debug("Loaded module " + module_name + ".")

if __name__ == '__main__':
	t0 = DefinedType("string")
	t0.register()

	t0 = DefinedType("integer")
	t0.register()

	DragomanParser.parse_file('test')

	print("---- Enum Types:")
	for e in EnumType.get_all():
		print(e.to_string())

	print("\n---- Object Types:")
	for e in ObjectType.get_all():
		print(e.to_string())

	print("\n---- Polymorph Types:")
	for e in PolymorphType.get_all():
		print(e.to_string())
