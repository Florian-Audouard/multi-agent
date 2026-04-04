class AgentMiddleware(Generic[StateT, ContextT, ResponseT]):
    """Base middleware class for an agent.

    Subclass this and implement any of the defined methods to customize agent behavior
    between steps in the main agent loop.

    Type Parameters:
        StateT: The type of the agent state. Defaults to `AgentState[Any]`.
        ContextT: The type of the runtime context. Defaults to `None`.
        ResponseT: The type of the structured response. Defaults to `Any`.
    """

    state_schema: type[StateT] = cast("type[StateT]", _DefaultAgentState)
    """The schema for state passed to the middleware nodes."""

    tools: Sequence[BaseTool]
    """Additional tools registered by the middleware."""

    @property
    def name(self) -> str:
        """The name of the middleware instance.

        Defaults to the class name, but can be overridden for custom naming.
        """
        return self.__class__.__name__

    def before_agent(self, state: StateT, runtime: Runtime[ContextT]) -> dict[str, Any] | None:
        """Logic to run before the agent execution starts.

        Args:
            state: The current agent state.
            runtime: The runtime context.

        Returns:
            Agent state updates to apply before agent execution.
        """

    async def abefore_agent(
        self, state: StateT, runtime: Runtime[ContextT]
    ) -> dict[str, Any] | None:
        """Async logic to run before the agent execution starts.

        Args:
            state: The current agent state.
            runtime: The runtime context.

        Returns:
            Agent state updates to apply before agent execution.
        """

    def before_model(self, state: StateT, runtime: Runtime[ContextT]) -> dict[str, Any] | None:
        """Logic to run before the model is called.

        Args:
            state: The current agent state.
            runtime: The runtime context.

        Returns:
            Agent state updates to apply before model call.
        """

    async def abefore_model(
        self, state: StateT, runtime: Runtime[ContextT]
    ) -> dict[str, Any] | None:
        """Async logic to run before the model is called.

        Args:
            state: The agent state.
            runtime: The runtime context.

        Returns:
            Agent state updates to apply before model call.
        """

    def after_model(self, state: StateT, runtime: Runtime[ContextT]) -> dict[str, Any] | None:
        """Logic to run after the model is called.

        Args:
            state: The current agent state.
            runtime: The runtime context.

        Returns:
            Agent state updates to apply after model call.
        """

    async def aafter_model(
        self, state: StateT, runtime: Runtime[ContextT]
    ) -> dict[str, Any] | None:
        """Async logic to run after the model is called.

        Args:
            state: The current agent state.
            runtime: The runtime context.

        Returns:
            Agent state updates to apply after model call.
        """

    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
    ) -> ModelResponse[ResponseT] | AIMessage | ExtendedModelResponse[ResponseT]:
        """Intercept and control model execution via handler callback.

        Async version is `awrap_model_call`

        The handler callback executes the model request and returns a `ModelResponse`.
        Middleware can call the handler multiple times for retry logic, skip calling
        it to short-circuit, or modify the request/response. Multiple middleware
        compose with first in list as outermost layer.

        Args:
            request: Model request to execute (includes state and runtime).
            handler: Callback that executes the model request and returns
                `ModelResponse`.

                Call this to execute the model.

                Can be called multiple times for retry logic.

                Can skip calling it to short-circuit.

        Returns:
            The model call result.

        Examples:
            !!! example "Retry on error"

                ```python
                def wrap_model_call(self, request, handler):
                    for attempt in range(3):
                        try:
                            return handler(request)
                        except Exception:
                            if attempt == 2:
                                raise
                ```

            !!! example "Rewrite response"

                ```python
                def wrap_model_call(self, request, handler):
                    response = handler(request)
                    ai_msg = response.result[0]
                    return ModelResponse(
                        result=[AIMessage(content=f"[{ai_msg.content}]")],
                        structured_response=response.structured_response,
                    )
                ```

            !!! example "Error to fallback"

                ```python
                def wrap_model_call(self, request, handler):
                    try:
                        return handler(request)
                    except Exception:
                        return ModelResponse(result=[AIMessage(content="Service unavailable")])
                ```

            !!! example "Cache/short-circuit"

                ```python
                def wrap_model_call(self, request, handler):
                    if cached := get_cache(request):
                        return cached  # Short-circuit with cached result
                    response = handler(request)
                    save_cache(request, response)
                    return response
                ```

            !!! example "Simple `AIMessage` return (converted automatically)"

                ```python
                def wrap_model_call(self, request, handler):
                    response = handler(request)
                    # Can return AIMessage directly for simple cases
                    return AIMessage(content="Simplified response")
                ```
        """
        msg = (
            "Synchronous implementation of wrap_model_call is not available. "
            "You are likely encountering this error because you defined only the async version "
            "(awrap_model_call) and invoked your agent in a synchronous context "
            "(e.g., using `stream()` or `invoke()`). "
            "To resolve this, either: "
            "(1) subclass AgentMiddleware and implement the synchronous wrap_model_call method, "
            "(2) use the @wrap_model_call decorator on a standalone sync function, or "
            "(3) invoke your agent asynchronously using `astream()` or `ainvoke()`."
        )
        raise NotImplementedError(msg)

    async def awrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], Awaitable[ModelResponse[ResponseT]]],
    ) -> ModelResponse[ResponseT] | AIMessage | ExtendedModelResponse[ResponseT]:
        """Intercept and control async model execution via handler callback.

        The handler callback executes the model request and returns a `ModelResponse`.

        Middleware can call the handler multiple times for retry logic, skip calling
        it to short-circuit, or modify the request/response. Multiple middleware
        compose with first in list as outermost layer.

        Args:
            request: Model request to execute (includes state and runtime).
            handler: Async callback that executes the model request and returns
                `ModelResponse`.

                Call this to execute the model.

                Can be called multiple times for retry logic.

                Can skip calling it to short-circuit.

        Returns:
            The model call result.

        Examples:
            !!! example "Retry on error"

                ```python
                async def awrap_model_call(self, request, handler):
                    for attempt in range(3):
                        try:
                            return await handler(request)
                        except Exception:
                            if attempt == 2:
                                raise
                ```
        """
        msg = (
            "Asynchronous implementation of awrap_model_call is not available. "
            "You are likely encountering this error because you defined only the sync version "
            "(wrap_model_call) and invoked your agent in an asynchronous context "
            "(e.g., using `astream()` or `ainvoke()`). "
            "To resolve this, either: "
            "(1) subclass AgentMiddleware and implement the asynchronous awrap_model_call method, "
            "(2) use the @wrap_model_call decorator on a standalone async function, or "
            "(3) invoke your agent synchronously using `stream()` or `invoke()`."
        )
        raise NotImplementedError(msg)

    def after_agent(self, state: StateT, runtime: Runtime[ContextT]) -> dict[str, Any] | None:
        """Logic to run after the agent execution completes.

        Args:
            state: The current agent state.
            runtime: The runtime context.

        Returns:
            Agent state updates to apply after agent execution.
        """

    async def aafter_agent(
        self, state: StateT, runtime: Runtime[ContextT]
    ) -> dict[str, Any] | None:
        """Async logic to run after the agent execution completes.

        Args:
            state: The current agent state.
            runtime: The runtime context.

        Returns:
            Agent state updates to apply after agent execution.
        """

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        """Intercept tool execution for retries, monitoring, or modification.

        Async version is `awrap_tool_call`

        Multiple middleware compose automatically (first defined = outermost).

        Exceptions propagate unless `handle_tool_errors` is configured on `ToolNode`.

        Args:
            request: Tool call request with call `dict`, `BaseTool`, state, and runtime.

                Access state via `request.state` and runtime via `request.runtime`.
            handler: `Callable` to execute the tool (can be called multiple times).

        Returns:
            `ToolMessage` or `Command` (the final result).

        The handler `Callable` can be invoked multiple times for retry logic.

        Each call to handler is independent and stateless.

        Examples:
            !!! example "Modify request before execution"

                ```python
                def wrap_tool_call(self, request, handler):
                    modified_call = {
                        **request.tool_call,
                        "args": {
                            **request.tool_call["args"],
                            "value": request.tool_call["args"]["value"] * 2,
                        },
                    }
                    request = request.override(tool_call=modified_call)
                    return handler(request)
                ```

            !!! example "Retry on error (call handler multiple times)"

                ```python
                def wrap_tool_call(self, request, handler):
                    for attempt in range(3):
                        try:
                            result = handler(request)
                            if is_valid(result):
                                return result
                        except Exception:
                            if attempt == 2:
                                raise
                    return result
                ```

            !!! example "Conditional retry based on response"

                ```python
                def wrap_tool_call(self, request, handler):
                    for attempt in range(3):
                        result = handler(request)
                        if isinstance(result, ToolMessage) and result.status != "error":
                            return result
                        if attempt < 2:
                            continue
                        return result
                ```
        """
        msg = (
            "Synchronous implementation of wrap_tool_call is not available. "
            "You are likely encountering this error because you defined only the async version "
            "(awrap_tool_call) and invoked your agent in a synchronous context "
            "(e.g., using `stream()` or `invoke()`). "
            "To resolve this, either: "
            "(1) subclass AgentMiddleware and implement the synchronous wrap_tool_call method, "
            "(2) use the @wrap_tool_call decorator on a standalone sync function, or "
            "(3) invoke your agent asynchronously using `astream()` or `ainvoke()`."
        )
        raise NotImplementedError(msg)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        """Intercept and control async tool execution via handler callback.

        The handler callback executes the tool call and returns a `ToolMessage` or
        `Command`. Middleware can call the handler multiple times for retry logic, skip
        calling it to short-circuit, or modify the request/response. Multiple middleware
        compose with first in list as outermost layer.

        Args:
            request: Tool call request with call `dict`, `BaseTool`, state, and runtime.

                Access state via `request.state` and runtime via `request.runtime`.
            handler: Async callable to execute the tool and returns `ToolMessage` or
                `Command`.

                Call this to execute the tool.

                Can be called multiple times for retry logic.

                Can skip calling it to short-circuit.

        Returns:
            `ToolMessage` or `Command` (the final result).

        The handler `Callable` can be invoked multiple times for retry logic.

        Each call to handler is independent and stateless.

        Examples:
            !!! example "Async retry on error"

                ```python
                async def awrap_tool_call(self, request, handler):
                    for attempt in range(3):
                        try:
                            result = await handler(request)
                            if is_valid(result):
                                return result
                        except Exception:
                            if attempt == 2:
                                raise
                    return result
                ```

                ```python
                async def awrap_tool_call(self, request, handler):
                    if cached := await get_cache_async(request):
                        return ToolMessage(content=cached, tool_call_id=request.tool_call["id"])
                    result = await handler(request)
                    await save_cache_async(request, result)
                    return result
                ```
        """
        msg = (
            "Asynchronous implementation of awrap_tool_call is not available. "
            "You are likely encountering this error because you defined only the sync version "
            "(wrap_tool_call) and invoked your agent in an asynchronous context "
            "(e.g., using `astream()` or `ainvoke()`). "
            "To resolve this, either: "
            "(1) subclass AgentMiddleware and implement the asynchronous awrap_tool_call method, "
            "(2) use the @wrap_tool_call decorator on a standalone async function, or "
            "(3) invoke your agent synchronously using `stream()` or `invoke()`."
        )
        raise NotImplementedError(msg)

