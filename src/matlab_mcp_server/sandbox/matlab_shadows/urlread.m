function varargout = urlread(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'urlread() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
