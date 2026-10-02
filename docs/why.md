# Why this approach

There are two common ways to build a screen.

In a single-page app, the browser holds a program. The server sends data, and that program draws the next screen. React is the usual example.

In this approach, the server sends the screen. The response is HTML, and the browser shows it. A click asks for the next piece of HTML. HTMX belongs to this side. People call it server-side rendering: every answer is HTML, including the piece that follows a click. The browser does not take over and keep its own copy of the screen.

This note is for anyone choosing between those two. Someone who already builds with React will recognize the first one.

## The pages did not need their own scripts

Search, forms, paging, confirm-and-delete, and a progress bar were wired in the template and answered by a backend endpoint. No page grew a click handler. One small shared script covers what the browser itself has to do: open a confirm dialog, show a toast, and attach the CSRF token. That script is the exception. It is not a new component for each screen.

## There is nothing to rebuild

HTMX and Bootstrap are vendored. There is no frontend build, and neither project ships a new stack every week. A page you finished still works, because nothing has to compile it again. Moving this project from HTMX 2 to HTMX 4 renamed a few events in that one shared script. A React app more often needs someone to keep the install and the build alive. The library is stable. The toolchain around it is not. A dependency bump, a newer Node, or a forced security upgrade can stop a project that used to build.

## The HTML that comes back is the screen

In React, a wrong page means hunting state, props, and a render that did not run. Here the response is the page. If the table is wrong, the HTML from the endpoint is wrong. That is why a week of screens could stay in templates and endpoints: there is no second model of the screen sitting in the browser.

## The address is enough to draw the page again

Reload, Back, and a link you send someone all ask the server for that URL. The server answers with the whole page. You do not rebuild navigation in the browser, and you do not rehydrate a bundle so the screen can exist. List filters live in the query string for this reason. A refresh is the same kind of request as the first visit.

A screen that must change before the server answers, or that must work offline, wants a program in the browser. This stack is for screens the server can render.
