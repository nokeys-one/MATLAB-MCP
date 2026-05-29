function varargout = feval(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'feval() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
