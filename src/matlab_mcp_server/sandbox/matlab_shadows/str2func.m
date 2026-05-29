function varargout = str2func(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'str2func() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
