#!/bin/env python3

from sly import Lexer, Parser

import sys
import argparse

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
	DEFAULT_INDENT = "\t"
	def __init__ (this, filepath: Path):
		filepath.parent.mkdir(parents=True, exist_ok=True)
		this.file = open(filepath, 'w')
		this.indent_style = CodeWriter.DEFAULT_INDENT
		this.indent_level = 0
		this.buffer = None
		this.buffer_ends_line = False

	def set_indent_style (this, indent: str):
		this.indent_style = indent

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

	def title_line (this, char: str, title: str, pre: int, total: int):
		this.start_line(char * pre)
		this.append(title)
		this.append(char * (total - pre - len(title)))
		this.newline()

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

	def compute_depth (this) -> (int, DefinedType):
		next = this
		depth = 0

		while (isinstance(next, ArrayOfDefinedType)):
			next = next.get_parent()
			depth += 1

		return (depth, next)

	def get_parent (this):
		return this.parent

class DictOfDefinedType (DefinedType):
	def __init__ (
			this,
			field_name: str,
			field_type: DefinedType,
			parent: DefinedType
	):
		DefinedType.__init__(
			this,
			(
				"(Dict "
				+ field_name
				+ ": "
				+ field_type.get_name()
				+ " -> "
				+ parent.get_name()
				+ ")"
			)
		)
		this.parent = parent
		this.field_name = field_name
		this.field_type = field_type

	def get_parent (this) -> DefinedType:
		return this.parent

	def get_field_name (this) -> str:
		return this.field_name

	def get_field_type (this) -> DefinedType:
		return this.field_type

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
		this.markers = set()

	def get_token (this) -> TokenLocation:
		return this.token

	def add_marker (this, marker: str):
		this.markers.add(marker.lower())

	def has_marker (this, marker: str) -> bool:
		return (marker.lower() in this.markers)

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

			while (
				isinstance(dependency, ArrayOfDefinedType)
				or isinstance(dependency, DictOfDefinedType)
			):
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

	def maybe_get_entry_from_name (this, name: str) -> ObjectTypeEntry | None:
		return this.entry_from_name.get(name)

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
		this.eentry = None

	def get_token (this) -> TokenLocation:
		return this.token

	def get_name (this) -> str:
		return this.name

	def get_type (this) -> DefinedType:
		return this.dtype

	def get_enum_entry (this) -> EnumTypeEntry:
		return this.eentry

	def set_enum_entry (this, eentry: EnumTypeEntry):
		this.eentry = eentry

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
		key_field_name: str,
		key_field_tag: str,
		enum_type: EnumType,
		cases: dict()
	):
		UserDefinedType.__init__(this, token, name)
		this.enum_type = enum_type
		this.cases = cases
		this.key_field_name = key_field_name
		this.key_field_tag = key_field_tag
		this.shared_fields = dict()
		this.shared_field_tags = dict()

		this.shared_fields[key_field_name] = enum_type
		this.shared_field_tags[key_field_name] = key_field_tag

		this.dependencies = set() # Types to include so members are defined.

		for entry in cases.values():
			dependency = entry.get_type()

			while (
				isinstance(dependency, ArrayOfDefinedType)
				or isinstance(dependency, DictOfDefinedType)
			):
				dependency = dependency.get_parent()

			if (isinstance(dependency, UserDefinedType)):
				this.dependencies.add(dependency)

	def get_key_field_name (this) -> str:
		return this.key_field_name

	def get_key_field_tag (this) -> str:
		return this.key_field_tag

	def get_enum_type (this) -> EnumType:
		return this.enum_type

	def get_dependencies (this) -> set[UserDefinedType]:
		return this.dependencies

	def get_cases_as_dict (this) -> dict[str, PolymorphTypeCase]:
		return this.cases

	def get_shared_fields (this) -> dict[str, DefinedType]:
		return this.shared_fields

	def get_shared_field (this, id: str) -> DefinedType:
		return this.shared_fields[id]

	def get_shared_field_tag (this, id: str) -> str:
		return this.shared_field_tags[id]

	def add_shared_field (this, id: str, target_type: DefinedType, tag: str):
		this.shared_fields[id] = target_type
		this.shared_field_tags[id] = tag

	def get_cases (this) -> list[PolymorphTypeCase]:
		return this.cases.values()

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

class NameSplitter:
	def split (s: str):
		result = []
		next_word = ""

		for c in s:
			if c.isalnum():
				if c.isupper():
					c = c.lower()

					if (len(next_word) > 0):
						result.append(next_word)
						next_word = ""
					next_word += str(c)
				else:
					next_word += c
					continue
			else:
				if (len(next_word) > 0):
					result.append(next_word)
					next_word = ""

		if (len(next_word) > 0):
			result.append(next_word)

		return result

class DragomanLexer (Lexer):
	tokens = {
		#NUMBER,
		ID,

		ARRAY_KW,
		CASE_KW,
		DICT_KW,
		ENTRY_KW,
		ENUM_KW,
		#MAX_KW,
		#MIN_KW,
		MARKERS_KW,
		OBJECT_KW,
		POLYMORPH_KW,
		REQUIRE_KW,
		SHARED_KW,

		EOP,
	}

	#@_(r'[\-]?\d+')
	#def NUMBER (this, t):
	#	t.value = int(t.value)
	#	return t

	ID = r'\+|\-|([\&a-zA-Z_,.%/#\':][\&a-zA-Z_0-9,.\-%#/\+\':]*)'

	ARRAY_KW = r'(?i:\(ARRAY)'
	CASE_KW = r'(?i:\(CASE)'
	DICT_KW = r'(?i:\(DICT)'
	ENTRY_KW = r'(?i:\(ENTRY)'
	ENUM_KW = r'(?i:\(ENUM)(?i:ERATE)?'
	MARKERS_KW = r'(?i:\(MARKERS)'
	#MAX_KW = r'(?i:\(MAX)(?i:IMUM)?'
	#MIN_KW = r'(?i:\(MIN)(?i:IMUM)?'
	OBJECT_KW = r'(?i:\(OBJECT)'
	POLYMORPH_KW = r'(?i:\(POLY)(?i:MORPH)?'
	REQUIRE_KW = r'(?i:\(REQUIRE)'
	SHARED_KW = r'(?i:\(SHARED)'

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
	INCLUDE_DIRECTORIES = set()

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

		filename = t.ID + ".dgl"
		found_file = False

		if (Path(filename).is_file()):
			found_file = True
			DragomanParser.parse_file(str(candidate))
		else:
			for dir in DragomanParser.INCLUDE_DIRECTORIES:
				candidate = dir / filename

				if (candidate.is_file()):
					found_file = True
					DragomanParser.parse_file(str(candidate))
					break

		if (not found_file):
			DragomanParser.print_error("Could not find required file.", t )
			raise Exception

		DragomanParser.COLUMN_STARTS_AT = COLUMN_STARTS_AT
		DragomanParser.CURRENT_FILE = CURRENT_FILE
		DragomanParser.LAST_TOKEN = LAST_TOKEN

		return t

	@_(r'ENUM_KW ID get_type enum_definition EOP')
	def file_entry (this, t):
		DragomanParser.LAST_TOKEN = t

		(tags, names, entries, markers) = t.enum_definition

		result = EnumType(TokenLocation(t), t.ID, t.get_type, entries)

		for m in markers:
			result.add_marker(m)

		result.register()

		return t

	@_(r'OBJECT_KW ID object_definition EOP')
	def file_entry (this, t):
		DragomanParser.LAST_TOKEN = t

		(tags, names, entries, markers) = t.object_definition

		result = ObjectType(TokenLocation(t), t.ID, entries)

		for m in markers:
			result.add_marker(m)

		result.register()

		return t

	@_(r'POLYMORPH_KW ID ID polymorph_definition EOP')
	def file_entry (this, t):
		DragomanParser.LAST_TOKEN = t

		enum_type = None
		key_field_tag = None

		(cases, shared, markers) = t.polymorph_definition

		shared_field_types = dict()
		for s in shared:
			shared_field_types[s] = None

		shared_field_tags = dict()
		for s in shared:
			shared_field_tags[s] = None

		for (k, pcase) in cases.items():
			pcase_type = pcase.get_type()

			if (isinstance(pcase_type, ObjectType)):
				# TODO: TypoFixer use for these...
				try:
					entry = pcase_type.get_entry_from_name(t.ID1)
					entry_type = entry.get_type()
				except Exception:
					DragomanParser.print_error(
						(
							"Type '"
							+ pcase_type.get_name()
							+ "' does not have entry '"
							+ t.ID1
							+ "'."
						),
						pcase.get_token()
					)
					raise Exception

				if (key_field_tag == None):
					key_field_tag = entry.get_tag()
				elif (key_field_tag != entry.get_tag()):
					DragomanParser.print_error(
						(
							"Type "
							+ entry_type.get_name()
							+ " does not use the same tag for "
							+ t.ID1
							+ " as previous entries."
						),
						pcase.get_token()
					)
					raise Exception
			elif (isinstance(entry, PolymorphType)):
				# TODO: TypoFixer use for these...
				try:
					entry_type = entry.get_shared_field(t.ID1)
				except Exception:
					DragomanParser.print_error(
						(
							"Type '"
							+ entry.get_name()
							+ "' does not have entry '"
							+ t.ID1
							+ "' as shared."
						),
						pcase.get_token()
					)
					raise Exception

				candidate_field_tag = entry.get_shared_field_tag(t.ID1)

				if (key_field_tag == None):
					key_field_tag = candidate_field_tag
				elif (key_field_tag != candidate_field_tag):
					DragomanParser.print_error(
						(
							"Entry '"
							+ t.ID1
							+ "' of target type does not use the same tag for "
							+ entry.get_name()
							+ " as previous entries."
						),
						pcase.get_token()
					)
					raise Exception
			else:
				# TODO: support for PolymorphType here.
				DragomanParser.print_error(
					"Invalid type used for polymorph case.",
					pcase.get_token()
				)
				raise Exception

			if (enum_type == None):
				enum_type = entry_type
			elif (enum_type != entry_type):
				DragomanParser.print_error(
					(
						"Type "
						+ entry_type.get_name()
						+ " does not use the same tag for "
						+ t.ID1
						+ " as previous entries."
					),
					pcase.get_token()
				)
				raise Exception

			try:
				entry = enum_type.get_entry_from_name(pcase.get_name())
			except Exception:
				DragomanParser.print_error(
					(
						"The Enum type '"
						+ enum_type.get_name()
						+ "' does not have any entry named '"
						+ pcase.get_name()
						+ "'."
					),
					pcase.get_token()
				)
				raise Exception

			pcase.set_enum_entry(entry)

			for s in shared:
				if (isinstance(entry, ObjectType)):
					try:
						shared_field = entry_type.get_entry_from_name(s)
						shared_field_type = shared_field.get_type()
						shared_field_tag = shared_field_type.get_tag()
					except Exception:
						DragomanParser.print_error(
							(
								"Type '"
								+ entry.get_name()
								+ "' does not have entry '"
								+ s
								+ "'."
							),
							pcase.get_token()
						)
						raise Exception
				elif (isinstance(entry, PolymorphType)):
					try:
						shared_field_type = entry_type.get_shared_field(t.ID1)
						shared_field_tag = entry_type.get_shared_field_tag(t.ID1)
					except Exception:
						DragomanParser.print_error(
							(
								"Type '"
								+ entry_type.get_name()
								+ "' does not have entry '"
								+ s
								+ "' as shared."
							),
							pcase.get_token()
						)
						raise Exception
				else:
					DragomanParser.print_error(
						(
							"Unsupported shared type of field for '"
							+ entry_type.get_name()
							+ "' ('"
							+ s
							+ "')."
						),
						pcase.get_token()
					)
					raise Exception

				if (shared_field_types[s] == None):
					shared_field_types[s] = shared_field_type
				elif (shared_field_type[s] != shared_field_type):
					DragomanParser.print_error(
						(
							"Entry '"
							+ t.ID1
							+ "' of target type does not use the same type for shared"
							+ " field '"
							+ s
							+ "' as previous entries."
						),
						pcase.get_token()
					)
					raise Exception

				if (shared_field_tags[s] == None):
					shared_field_tags[s] = shared_field_tag
				elif (shared_field_tag[s] != shared_field_tag):
					DragomanParser.print_error(
						(
							"Entry '"
							+ t.ID1
							+ "' of target tag does not use the same tag for shared"
							+ " field '"
							+ s
							+ "' as previous entries."
						),
						pcase.get_token()
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
			t.ID1,
			key_field_tag,
			enum_type,
			cases,
		)

		for s in shared:
			result.add_shared_field(s, shared_field_types[s], shared_field_tags[s])

		for m in markers:
			result.add_marker(m)

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

	@_(r'DICT_KW ID get_type EOP')
	def get_type (this, t):
		DragomanParser.LAST_TOKEN = t

		value_type = t.get_type

		if (isinstance(value_type, ObjectType)):
			try:
				field = value_type.get_entry_from_name(t.ID)
				field_type = field.get_type()
			except Exception as e:
				# TODO: TypoFixer
				DragomanParser.print_error(
					(
						"There is no '"
						+ t.ID
						+ "' entry in type '"
						+ value_type.get_name()
						+ "'"
					),
					t.DICT_KW
				)
				raise Exception
		elif (isinstance(value_type, PolymorphType)):
				try:
					field_type = value_type.get_shared_field(t.ID)
				except Exception as e:
					# TODO: TypoFixer
					DragomanParser.print_error(
						(
							"There is no '"
							+ t.ID
							+ "' shared field in type '"
							+ value_type.get_name()
							+ "'"
						),
						t.DICT_KW
					)
					raise Exception
		if (
			isinstance(field_type, UserDefinedType)
			and not isinstance(field_type, EnumType)
		):
			DragomanParser.print_error(
				(
					"Dictionaries cannot use type '"
					+ field_type.get_name()
					+ "' for keys."
				),
				t.DICT_KW
			)
			raise Exception

		return DictOfDefinedType(t.ID, field_type, t.get_type)

	#### OBJECT #################################################################
	@_(r'')
	def object_definition (this, t):
		DragomanParser.LAST_TOKEN = t

		return (set(), set(), list(), set())

	@_(r'ENTRY_KW ID ID get_type EOP object_definition')
	def object_definition (this, t):
		DragomanParser.LAST_TOKEN = t

		(names, tags, entries, markers) = t.object_definition

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

		return (names, tags, entries, markers)

	@_(r'ENTRY_KW ID get_type EOP object_definition')
	def object_definition (this, t):
		DragomanParser.LAST_TOKEN = t

		(names, tags, entries, markers) = t.object_definition

		result = ObjectTypeEntry(
			TokenLocation(t),
			t.ID,
			"f" + str(len(tags)),
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
				(
					"Automatic tag '"
					+ result.get_tag()
					+ "' conflicts with manual one."
				),
				t.ENTRY_KW
			)
			raise Exception

		names.add(result.get_name())
		tags.add(result.get_tag())
		entries.append(result)

		return (names, tags, entries, markers)

	@_(r'MARKERS_KW id_set EOP object_definition')
	def object_definition (this, t):
		DragomanParser.LAST_TOKEN = t

		(names, tags, entries, markers) = t.object_definition

		for m in t.id_set:
			markers.add(m)

		return (names, tags, entries, markers)

	#### ENUM ###################################################################
	@_(r'')
	def enum_definition (this, t):
		DragomanParser.LAST_TOKEN = t

		return (set(), set(), list(), set())

	@_(r'ENTRY_KW ID ID EOP enum_definition')
	def enum_definition (this, t):
		DragomanParser.LAST_TOKEN = t

		(names, tags, entries, markers) = t.enum_definition

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

		return (names, tags, entries, markers)

	@_(r'MARKERS_KW id_set EOP enum_definition')
	def enum_definition (this, t):
		DragomanParser.LAST_TOKEN = t

		(names, tags, entries, markers) = t.enum_definition

		for m in t.id_set:
			markers.add(m)

		return (names, tags, entries, markers)

	#### POLYMORPH ##############################################################
	@_(r'')
	def polymorph_definition (this, t):
		DragomanParser.LAST_TOKEN = t

		return (dict(), set(), set())

	@_(r'CASE_KW ID get_type EOP polymorph_definition')
	def polymorph_definition (this, t):
		DragomanParser.LAST_TOKEN = t

		(cases, shared, markers) = t.polymorph_definition

		result = PolymorphTypeCase(TokenLocation(t), t.ID, t.get_type)

		if (result.get_name() in cases):
			DragomanParser.print_error(
				"Duplicate case '" + result.get_name() + "'",
				t.CASE_KW
			)
			raise Exception

		cases[result.get_name()] = result

		return (cases, shared, markers)

	@_(r'MARKERS_KW id_set EOP polymorph_definition')
	def polymorph_definition (this, t):
		DragomanParser.LAST_TOKEN = t

		(cases, shared, markers) = t.polymorph_definition

		for m in t.id_set:
			markers.add(m.lower())

		return (cases, shared, markers)

	@_(r'SHARED_KW id_set EOP polymorph_definition')
	def polymorph_definition (this, t):
		DragomanParser.LAST_TOKEN = t

		(cases, shared, markers) = t.polymorph_definition

		for s in t.id_set:
			shared.add(s)

		return (cases, shared, markers)

	#### ID SET #################################################################
	@_(r'')
	def id_set (this, t):
		return set()

	@_(r'ID id_set')
	def id_set (this, t):
		prev = t.id_set

		prev.add(ID)

		return prev

	#############################################################################
	def error (this, t):
		Log.print_error(
			"Syntax error. Unexpected \"" + str(t.value) + "\".",
			DragomanParser.get_cursor(t)
		)
		raise Exception

	def parse_file (filename):
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

class Dragoman:
	OUTPUT_FOLDER = "."

	def initialize ():
		t0 = DefinedType("string")
		t0.register()

		t0 = DefinedType("integer")
		t0.register()

		t0 = DefinedType("boolean")
		t0.register()

		t0 = DefinedType("float")
		t0.register()

		argparser = argparse.ArgumentParser()
		argparser.add_argument(
			"dgl_file",
			type=Path,
			nargs=1,
			help="DGL description entry point."
		)
		argparser.add_argument(
			"--roles",
			type=str,
			nargs='*',
			help="Roles for this target."
		)
		argparser.add_argument(
			"--output-folder",
			type=Path,
			nargs=1,
			help="Where to output files"
		)
		argparser.add_argument(
			"--include",
			type=Path,
			nargs='*',
			help="Where to look for files"
		)
		argparser.add_argument(
			"--indentation",
			type=str,
			nargs=1,
			help="What to use as indentation"
		)

		return argparser

	def handle_arguments (args):
		if (args.include is not None):
			for dir in args.include:
				DragomanParser.INCLUDE_DIRECTORIES.add(dir)

		if (args.output_folder is not None):
			Dragoman.OUTPUT_FOLDER = args.output_folder[0]

		if (args.indentation is not None):
			CodeWriter.DEFAULT_INDENT = args.indentation[0]

	def print ():
		print("---- Enum Types:")
		for e in EnumType.get_all():
			print(e.to_string())

		print("\n---- Object Types:")
		for e in ObjectType.get_all():
			print(e.to_string())

		print("\n---- Polymorph Types:")
		for e in PolymorphType.get_all():
			print(e.to_string())

if __name__ == '__main__':
	Dragoman.initialize()

	DragomanParser.parse_file('test')

	Dragoman.print()
