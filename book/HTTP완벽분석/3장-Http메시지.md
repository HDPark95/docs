3장 HTTP 메시지

메시지의 흐름
•	인바운드 : 클라이언트로부터 서버로의 흐름을 의미한다. 예를 들어 브라우저가 서버에 페이지를 요청하는 것.
•	아웃바운드 : 서버로부터 클라이언트로의 흐름을 의미한다. 예를 들어 서버가 HTML 페이지를 브라우저로 보내는 것.
•	메시지의 발송자는 업스트림이고 수신자는 다운스트림이다. 항상 업스트림에서 다운스트림 방향으로만 흐른다.

⸻

메시지의 구성
•	메시지는 시작줄, 헤더, 본문 세 부분으로 구성된다.
•	시작줄: 이 메시지가 어떤 종류인지 설명. (요청이면 요청라인, 응답이면 상태라인)
•	헤더: 메시지와 본문에 대한 속성, 메타데이터를 담는다.
•	본문: 실제 데이터(payload). 없을 수도 있다.
•	시작줄과 헤더는 CRLF(\r\n)으로 구분하고, 헤더와 본문 사이는 CRLF 2번으로 구분한다.

⸻

메시지 문법
•	요청

<메서드> <요청 URL> <버전>
<헤더>

<엔티티 본문>

예:

GET /index.html HTTP/1.1
Host: www.example.com
User-Agent: Mozilla/5.0

•	응답

<버전> <상태 코드> <사유 구절>
<헤더>

<엔티티 본문>

예:

HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 100

<html>...</html>


⸻

메서드
•	GET: 리소스 조회
•	HEAD: GET과 같지만 본문 없이 헤더만 반환
•	PUT: 지정한 URL에 데이터 업로드/대체
•	POST: 서버에 데이터 전송 (주로 폼 제출, API 요청)
•	TRACE: 요청이 서버에 도달하기까지의 경로를 그대로 반환
•	OPTIONS: 서버가 지원하는 메서드와 옵션 확인
•	DELETE: 지정한 리소스 삭제 요청
•	확장 메서드: 표준은 아니지만 확장해서 쓰는 메서드들 (예: LOCK, MKCOL, COPY)

⸻

상태 코드
•	100-199 : 정보성 상태 코드 (예: 100 Continue)
•	200-299 : 성공 상태 코드 (예: 200 OK, 201 Created)
•	300-399 : 리다이렉션 상태 코드 (예: 301 Moved Permanently, 302 Found)
•	400-499 : 클라이언트 에러 상태 코드 (예: 400 Bad Request, 404 Not Found)
•	500-599 : 서버 에러 상태 코드 (예: 500 Internal Server Error, 503 Service Unavailable)

⸻

헤더
•	일반 헤더: 요청과 응답 모두에서 사용되는 공통 정보 (예: Date, Connection, Cache-Control)
•	요청 헤더: 클라이언트가 서버로 보내는 추가 정보 (예: Host, User-Agent, Accept)
•	보안 관련 요청 헤더 (예: Authorization, Cookie)
•	응답 헤더: 서버가 클라이언트로 보내는 추가 정보 (예: Server, Set-Cookie)
•	보안 관련 응답 헤더 (예: WWW-Authenticate, Strict-Transport-Security)
•	엔티티 헤더: 본문 데이터에 대한 메타데이터 (예: Content-Type, Content-Length, Allow, Content-Encoding)

⸻
