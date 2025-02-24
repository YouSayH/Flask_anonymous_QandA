-- student_number を主キー(PRIMARY KEY)にしてもいいと思う
CREATE TABLE users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    st_num TEXT NOT NULL UNIQUE,
    pass_w TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE questions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATETIME NOT NULL,
    question_content TEXT NOT NULL,
    category TEXT CHECK (category IN ('カテゴリー1','カテゴリー2','カテゴリー3','カテゴリー4','カテゴリー5','カテゴリー6','カテゴリー7')),
    user_id INTEGER,
    best_answer_id INTEGER,
    best_st_num TEXT,
    best_answer_user_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (best_answer_id) REFERENCES answers(id),
    FOREIGN KEY (best_st_num) REFERENCES users(st_num),
    FOREIGN KEY (best_answer_user_id) REFERENCES users(id)
);

CREATE TABLE answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    answer_content TEXT NOT NULL,
    user_id INTEGER,
    st_num TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (st_num) REFERENCES users(st_num)
);
