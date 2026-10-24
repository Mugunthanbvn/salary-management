from salary_api.core.schemas import FileFormat
from salary_api.modules.employees.schemas import EmployeeFilterQuery


class EmployeeExportQuery(EmployeeFilterQuery):
    """The query of GET /employees/export: every filter and the sort of GET /employees, and
    the file format. No paging: the whole filtered list is exported."""

    format: FileFormat = FileFormat.CSV
