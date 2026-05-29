function varargout = rmdir(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'rmdir() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
