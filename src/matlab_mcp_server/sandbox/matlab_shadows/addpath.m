function varargout = addpath(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'addpath() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
