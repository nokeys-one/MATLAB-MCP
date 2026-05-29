function varargout = javaaddpath(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'javaaddpath() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
