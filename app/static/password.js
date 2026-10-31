document.addEventListener("DOMContentLoaded", () => {
    const password = document.getElementById("password");
    const confirm = document.getElementById(
        "confirm_password"
    );
    const match = document.getElementById("password-match");

    if (!password || !confirm || !match) return;

    function validate() {
        const value = password.value;

        const rules = {
            length: Array.from(value).length >= 12 &&
                    Array.from(value).length <= 128,
            lower: /\p{Ll}/u.test(value),
            upper: /\p{Lu}/u.test(value),
            digit: /\p{Nd}/u.test(value),
            special: /[\p{P}\p{S}]/u.test(value),
        };

        for (const [rule, valid] of Object.entries(rules)) {
            const item = document.querySelector(
                `[data-rule="${rule}"]`
            );

            if (!item) continue;

            item.classList.toggle("valid", valid);
            item.classList.toggle("invalid", !valid);
        }

        if (!confirm.value) {
            match.textContent = "";
        } else if (value === confirm.value) {
            match.textContent = "✓ Hasla sa identyczne";
            match.className = "match-success";
        } else {
            match.textContent = "✕ Hasla nie sa identyczne";
            match.className = "match-error";
        }
    }

    password.addEventListener("input", validate);
    confirm.addEventListener("input", validate);

    validate();
});
