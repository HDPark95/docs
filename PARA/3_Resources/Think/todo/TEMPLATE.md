---
created: <% tp.date.now("YYYY-MM-DD HH:mm") %>
tags: #daily_note
---

# <% tp.date.now("YYYY-MM-DD") %>

## Todo

- [ ]
- [ ]
- [ ]


## Doing

- [ ]


## Done

- [x]


---

## 메모


## 회고


---

[[<% tp.date.now("YYYY-MM-DD", -1) %>|← 어제]] | [[<% tp.date.now("YYYY-MM-DD", 1) %>|내일 →]]

<%*
// 파일 생성 후 자동으로 CardBoard로 열기
await tp.app.commands.executeCommandById('cardboard:open-board-view')
%>