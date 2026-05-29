function varargout = builtin(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'builtin() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
