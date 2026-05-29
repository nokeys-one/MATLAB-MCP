function varargout = rmpath(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'rmpath() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
