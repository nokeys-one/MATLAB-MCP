function varargout = evalc(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'evalc() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
