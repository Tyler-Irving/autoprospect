"""Workspace API views."""
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import WorkspaceSerializer


@api_view(["GET", "PATCH"])
def workspace_detail(request):
    """Get or update the current user's active workspace.

    GET  — returns workspace info including member count and caller's role.
    PATCH — allows updating the workspace name.
    """
    workspace = request.workspace
    if workspace is None:
        return Response({"detail": "No workspace found for this user."}, status=404)

    if request.method == "PATCH":
        serializer = WorkspaceSerializer(
            workspace, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    serializer = WorkspaceSerializer(workspace, context={"request": request})
    return Response(serializer.data)
