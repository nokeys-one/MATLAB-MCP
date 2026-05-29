function varargout = input(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'input() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
