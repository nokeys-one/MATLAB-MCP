function varargout = keyboard(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'keyboard() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
