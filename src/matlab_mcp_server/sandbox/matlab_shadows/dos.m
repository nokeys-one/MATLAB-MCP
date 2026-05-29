function varargout = dos(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'dos() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
