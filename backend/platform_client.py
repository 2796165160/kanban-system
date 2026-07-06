import httpx

BASE_TIMEOUT = 60


class PlatformClient:
    def __init__(self, base_url: str, access_key: str):
        self.base_url = base_url.rstrip("/")
        self.access_key = access_key
        self._client = httpx.Client(timeout=BASE_TIMEOUT)

    def _headers(self):
        return {
            "access-key": self.access_key,
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, */*",
        }

    def _request(self, method: str, path: str, **kwargs):
        url = f"{self.base_url}{path}"
        resp = self._client.request(method, url, headers=self._headers(), **kwargs)
        text = resp.text
        if text.startswith("<"):
            raise Exception("服务器返回了 HTML 页面（access-key 错误或未登录）")
        data = resp.json()
        if data.get("code"):
            raise Exception(data.get("msg", data["code"]))
        return data

    def test_connection(self) -> dict:
        """POST /v2/users/info"""
        return self._request("POST", "/v2/users/info", content="{}")

    def get_projects(self) -> list:
        """GET /v2/projects - list all projects with their keys, auto-paginate"""
        all_projects = []
        page = 1
        while True:
            data = self._request("GET", f"/v2/projects?page={page}&page_num=20")
            items = data.get("data", {}).get("items", [])
            all_projects.extend(items)
            total = data.get("data", {}).get("meta", {}).get("total_num", 0)
            if len(items) < 20 or len(all_projects) >= total:
                break
            page += 1
        return all_projects
        # each item: { project_id, project_name, project_key: "pr_xxx", ... }

    def get_task_batches(self, project_key: str) -> list:
        """GET /v2/projects/{project_key}/task-batches - list task batches"""
        all_batches = []
        page = 1
        while True:
            data = self._request(
                "GET",
                f"/v2/projects/{project_key}/task-batches"
                f"?task_name=&task_key=&line_status=&page_num=20&page={page}"
                f"&creator_ids=&file_name=&seg_dir_name=",
            )
            items = data.get("data", {}).get("items", [])
            all_batches.extend(items)
            total = data.get("data", {}).get("meta", {}).get("total_num", 0)
            if len(items) < 20 or len(all_batches) >= total:
                break
            page += 1
        return all_batches
        # each item: { task_batch_id, task_batch_name, task_batch_key: "xxx", ... }

    def get_packages(self, task_key: str) -> list:
        """GET /v2/task-batches/{task_key}/packages - get all packages with status"""
        all_packages = []
        page = 1
        while True:
            data = self._request(
                "GET",
                f"/v2/task-batches/{task_key}/packages"
                f"?status=99&work_type=1&task_id=&package_id=&file_name="
                f"&seg_dir_name=&operate_work_type=&seg_dir_name_like="
                f"&operate_users=&issue_status=&is_issues="
                f"&page_num=20&mark_status=&page={page}&get_result_package=1",
            )
            items = data.get("data", {}).get("items", [])
            all_packages.extend(items)
            total = data.get("data", {}).get("meta", {}).get("total_num", 0)
            if len(items) < 20 or len(all_packages) >= total:
                break
            page += 1
        return all_packages
        # each item likely has label_info, check_info, quality_info, acceptance_info
        # with user_id and status info

    def get_check_info(self, task_key: str) -> dict:
        """GET /v2/reports/{task_key}/check-info"""
        return self._request("GET", f"/v2/reports/{task_key}/check-info")

    def get_performance(self, project_key: str, work_type: int, day_param: int) -> list:
        """GET /v2/performance/user/labels - user performance for a project + work_type"""
        data = self._request(
            "GET",
            f"/v2/performance/user/labels"
            f"?project_key={project_key}&work_type={work_type}&day={day_param}&gid=0",
        )
        return data.get("data", {}).get("items", [])

    def close(self):
        self._client.close()
