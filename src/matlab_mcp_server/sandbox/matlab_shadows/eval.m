function varargout = eval(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'eval() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
