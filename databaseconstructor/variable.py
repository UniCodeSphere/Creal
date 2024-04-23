from enum import Enum, auto
import random
import ctypes


class VarType(Enum):
    INT8    =   auto()
    UINT8   =   auto()
    INT16   =   auto()
    UINT16  =   auto()
    INT32   =   auto()
    UINT32  =   auto()
    INT64   =   auto()
    UINT64  =   auto()
    CHAR    =   auto()
    UCHAR   =   auto()
    VOID    =   auto()
    STRUCT  =   auto()
    '''pointers'''
    PTR_INT8    =   auto()
    PTR_UINT8   =   auto()
    PTR_INT16   =   auto()
    PTR_UINT16  =   auto()
    PTR_INT32   =   auto()
    PTR_UINT32  =   auto()
    PTR_INT64   =   auto()
    PTR_UINT64  =   auto()
    PTR_CHAR    =   auto()
    PTR_UCHAR   =   auto()
    PTR_VOID    =   auto()

    def __eq__(self, other_type):
        return self.value == other_type.value
    
    @staticmethod
    def from_str(type_str:str):
        type_str = type_str.strip()
        if "const" in type_str:
            Warning(f"{type_str} found. We now only ignore the \"const\".")
            type_str = type_str.replace("const", "").strip()
        for map_type in VAR_MAP:
            for map_type_str in map_type.type_str_list:
                if map_type_str == type_str:
                    return VarType(map_type.vartype.value)
        if type_str.count("*") == 1:
            base_type = VarType.from_str(type_str.replace("*", "").strip())
            for map_type in VAR_MAP:
                if map_type.vartype == base_type:
                    return VarType(map_type.pointertype.value)
        # we now treat all other types as int
        return VarType.INT32
        # raise ValueError(f"{type_str} is not a valid variable type")
    
    @staticmethod
    def from_list(type_list):
        return [VarType.from_str(x) if not isinstance(x, VarType) else x for x in type_list]
        
    @staticmethod
    def get_base_type(var_type):
        for map_type in VAR_MAP:
            if map_type.pointertype == var_type:
                return VarType(map_type.vartype.value)
            if map_type.vartype == var_type:
                return VarType(map_type.vartype.value)
        raise ValueError("Unknown pointer type from VarType.get_pointer_base_type")
    
    @staticmethod
    def to_str(vartype):
        for map_type in VAR_MAP:
            if vartype == map_type.vartype:
                return map_type.type_str_list[0]
            if vartype == map_type.pointertype:
                return f"{map_type.type_str_list[0]} *"
        raise ValueError
    
    @staticmethod
    def get_range(var_type):
        for type_info in VAR_MAP:
            if type_info.vartype == var_type:
                return type_info.range_list[0], type_info.range_list[1]
        return -1, -1
    
    @staticmethod
    def get_random_value(var_type, given_min=None, given_max=None):
        """
        In theory, we could generate any value sampled from VarType.get_range(var_type)
        But this would generate large values that can not be used by other smaller types.
        So we limit the range to [-100, 100]
        """
        range_min, range_min = VarType.get_range(var_type)
        _min = -100 if not given_min else given_min
        _max = 100 if not given_min else given_max
        if range_min >= 0:
            _min = 0
        return random.randint(_min, _max)
    
    @staticmethod
    def is_unsupport_type(var_type) -> bool:
        """Now only struct is unsupported"""
        return var_type == VarType.STRUCT# or var_type == VarType.VOID
    
    @staticmethod
    def get_random_type():
        """get a random VarType that is not VOID or STRUCT"""
        while True:
            rand_type = random.choice(list(VarType))
            if rand_type != VarType.VOID and rand_type != VarType.STRUCT:
                return rand_type
    
    @staticmethod
    def get_ctypes(var_type, var_value=None):
        """Get a ctype object"""
        for map_type in VAR_MAP:
            if var_type == map_type.vartype:
                if var_value == None:
                    return map_type.ctypes_conver_func
                else:
                    return map_type.ctypes_conver_func(var_value)
        raise(f"Cannot get ctypes of {VarType.to_str(var_type)}.")
    
    @staticmethod
    def get_format(var_type):
        """Get the printf format for the type"""
        for map_type in VAR_MAP:
            if var_type == map_type.vartype:
                return map_type.fmt
        raise(f"Cannot get format of {VarType.to_str(var_type)}.")

class TypeInfo:
    """
    [base type, pointer type, list[type str], range, ctype convert function, printf format]
    """
    def __init__(self, vartype:VarType, pointertype:VarType, type_str_list:list[str], range_list:list[int], ctypes_conver_func, fmt):
        self.vartype = vartype
        self.pointertype = pointertype
        self.type_str_list = type_str_list
        self.range_list = range_list
        self.ctypes_conver_func = ctypes_conver_func
        self.fmt = fmt

VAR_MAP = []
VAR_MAP.append(TypeInfo(VarType.INT8, VarType.PTR_INT8, ["int8_t"], [-128, 127], ctypes.c_int8, "PRId8"))
VAR_MAP.append(TypeInfo(VarType.UINT8, VarType.PTR_UINT8, ["uint8_t"], [0, 255], ctypes.c_uint8, "PRIu8"))
VAR_MAP.append(TypeInfo(VarType.INT16, VarType.PTR_INT16, ["int16_t"], [-32768, 32767], ctypes.c_int16, "PRId16"))
VAR_MAP.append(TypeInfo(VarType.UINT16, VarType.PTR_UINT16, ["uint16_t"], [0, 65535], ctypes.c_uint16, "PRIu16"))
VAR_MAP.append(TypeInfo(VarType.INT32, VarType.PTR_INT32, ["int", "int32_t"], [-2147483648, 2147483647], ctypes.c_int32, "PRId32"))
VAR_MAP.append(TypeInfo(VarType.UINT32, VarType.PTR_UINT32, ["unsigned int", "uint32_t"], [0, 4294967295], ctypes.c_uint32, "PRIu32"))
VAR_MAP.append(TypeInfo(VarType.INT64, VarType.PTR_INT64, ["long", "int64_t"], [-9223372036854775808, 9223372036854775807], ctypes.c_int64, "PRId64"))
VAR_MAP.append(TypeInfo(VarType.UINT64, VarType.PTR_UINT64, ["unsigned long", "uint64_t"], [0, 18446744073709551615], ctypes.c_uint64, "PRIu64"))
VAR_MAP.append(TypeInfo(VarType.CHAR, VarType.PTR_CHAR, ["char"], [-128, 127], ctypes.c_int8, "PRId8"))
VAR_MAP.append(TypeInfo(VarType.UCHAR, VarType.PTR_UCHAR, ["unsigned char"], [0, 255], ctypes.c_uint8, "PRIu8"))
VAR_MAP.append(TypeInfo(VarType.VOID, VarType.PTR_VOID, ["void"], [0, 0], None, None))


def CAST_VAR(value:int, from_type:VarType, to_type:VarType) -> int:
    """
    Casting the value from type 'from_type' to type 'to_type'
    """
    for var_map in VAR_MAP:
        if var_map.vartype == to_type:
            return var_map.ctypes_conver_func(value)
