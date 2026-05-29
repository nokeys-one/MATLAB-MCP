function varargout = evalin(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'evalin() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
