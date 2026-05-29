function delete(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'delete() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
