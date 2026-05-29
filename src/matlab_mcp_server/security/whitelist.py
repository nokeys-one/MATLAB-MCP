from enum import Enum


class SecurityLevel(Enum):
    L0_AUTO = "auto"
    L1_LOGGED = "logged"
    L2_APPROVAL = "approval"
    L3_BLOCKED = "blocked"


L0_SAFE_FUNCTIONS = {
    "abs", "acos", "angle", "atan", "atan2",
    "bar", "bode", "ceil", "char", "circshift", "class", "clc",
    "clear", "close", "cond", "conj", "contour", "conv", "cos",
    "csvread", "csvwrite", "cumsum", "datestr", "det", "diag",
    "diff", "disp", "double", "eig", "errorbar", "exist", "exp",
    "eye", "fft", "fft2", "figure", "fill", "filter", "find",
    "fix", "flip", "floor", "fopen", "format", "freqz", "full",
    "fzero", "get_param", "gradient", "grid", "gtext",
    "hist", "histogram", "hold", "hypot", "ifft", "ifft2",
    "imag", "imagesc", "imfinfo", "imread", "imshow", "interp1",
    "isa", "iscell", "isempty", "isfield", "isfinite", "isnan",
    "isnumeric", "linspace", "load", "log", "log10", "log2",
    "loglog", "lsim", "max", "mean", "mesh", "meshgrid", "min",
    "mod", "ndims", "norm", "normcdf", "norminv", "normpdf",
    "num2str", "numel", "ode45", "ones", "pade", "peaks",
    "perms", "pi", "plot", "plot3", "plotyy", "polar", "poly",
    "polyfit", "polyval", "pow2", "printf", "prod",
    "quiver", "rand", "randi", "randn", "rcond", "readtable",
    "real", "rem", "repmat", "reshape", "roots", "rosser",
    "save", "scatter", "scatter3", "semilogx", "semilogy",
    "set_param", "sign", "sim", "sin", "size", "sort",
    "sortrows", "sos2tf", "sphere", "sprintf", "sqrt", "ss",
    "stairs", "std", "stem", "str2double", "str2num", "strcmp",
    "strcmpi", "strfind", "strings", "strlength", "subplot",
    "subplot", "sum", "surf", "surface", "svd", "table",
    "tan", "text", "tf", "tiledlayout", "title", "trapz",
    "tril", "triu", "union", "unique", "var", "vertcat",
    "xlabel", "xlim", "ylabel", "ylim", "zeros", "zlabel",
    "add_block", "add_line", "delete_block", "delete_line",
    "find_system", "get_param", "load_system", "new_system",
    "save_system", "set_param", "sim", "open_system",
    "close_system", "bdclose", "gcbh", "gcb", "gcs",
}

L3_BLOCKED_FUNCTIONS = {
    "eval", "evalc", "evalin", "feval", "builtin", "str2func",
    "unix", "perl", "python",
    "addpath", "rmpath", "javaaddpath",
    "keyboard", "input",
    "java", "javaObject", "javaMethod", "javaArray",
}

L2_APPROVAL_FUNCTIONS = {
    "system", "dos",
    "delete", "rmdir", "movefile", "copyfile",
    "urlread", "urlwrite", "webread", "webwrite",
    "fopen", "fwrite", "fclose",
    "cd",
    "trainNetwork", "train", "fitnet",
}


def check_security_level(function_name: str) -> SecurityLevel:
    name_lower = function_name.strip().lower()
    for f in L0_SAFE_FUNCTIONS:
        if f.lower() == name_lower:
            return SecurityLevel.L0_AUTO
    for f in L3_BLOCKED_FUNCTIONS:
        if f.lower() == name_lower:
            return SecurityLevel.L3_BLOCKED
    for f in L2_APPROVAL_FUNCTIONS:
        if f.lower() == name_lower:
            return SecurityLevel.L2_APPROVAL
    return SecurityLevel.L2_APPROVAL
