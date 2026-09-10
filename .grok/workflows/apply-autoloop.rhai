let meta = #{
    name: "apply-autoloop",
    description: "无人值守把中小厂待投岗跑到人工审简历门禁，不自动提交",
    phases: [
        #{ title: "Queue", detail: "选出岗位并海投预填" },
        #{ title: "Inbox", detail: "列出待审简历" },
    ],
    when_to_use: "自动准备投递、只在审简历时打断",
};

let limit = 3;
if (args != () && args.limit != ()) {
    limit = args.limit;
}

phase("Queue");
let prompt = "You are in the Career OS repo root. Run this exact command with the shell tool and return the JSON it prints: python bin/career_apply_run.py autoloop --mode volume --limit ";
prompt += limit.to_string();
prompt += " Do not click any website submit button. Do not git push. Do not edit config/profile.yml. Summarize started job_id, run_id, resume_path.";
let queued = agent(prompt, #{ label: "volume-autoloop", capability_mode: "execute" });
if (queued == () || !queued.success) {
    pause("infra", "volume autoloop agent failed; inspect the run and retry.");
}

phase("Inbox");
let inbox_prompt = "In the Career OS repo root, run: python bin/career_apply_run.py inbox . Return company, title, resume_path, url for each item. Tell the user to review those resumes in person, then open the apply URL and submit themselves. Never click submit.";
let inbox = agent(inbox_prompt, #{ label: "inbox", capability_mode: "execute" });
if (inbox == () || !inbox.success) {
    pause("infra", "inbox agent failed; run python bin/career_apply_run.py inbox locally.");
}

log("Stopped at human resume review. No auto-submit.");
complete(#{
    ok: true,
    note: "stopped at human resume review; user evaluates then applies",
    queue_ok: queued.success,
    inbox_ok: inbox.success,
});
