# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants / RSS / OpenAI 等の外部データを取り込み、ETL、品質チェック、ニュース NLP、マーケットレジーム判定、ファクター計算、監査ログなどを提供します。

主な用途
- 日次 ETL による株価・財務・市場カレンダーの取得・保存
- RSS ベースのニュース収集と LLM による銘柄センチメント算出
- ETF とマクロニュースを組み合わせた市場レジーム判定
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ）
- データ品質チェック、監査ログ用スキーマ管理
- J-Quants API クライアント（ページネーション／リトライ／レート制御付き）

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save：prices, financials, calendar, listed info）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS -> raw_news、URL 正規化、SSRF 防御、トラッキング除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ（signal_events, order_requests, executions）および初期化ユーティリティ
  - 統計ユーティリティ（z-score 正規化 等）
- ai
  - news_nlp.score_news: ニュースをまとめて OpenAI に送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む
  - regime_detector.score_regime: ETF(1321)のMA乖離とマクロニュース（LLM）を合成して market_regime に書き込む
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- 設定管理（kabusys.config.Settings）
  - .env / .env.local 自動ロード（プロジェクトルート検出）、環境変数による設定管理

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   - 例: git clone ...

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（プロジェクトに requirements.txt / pyproject.toml がある想定）
   - 例（最低限）:
     pip install duckdb openai defusedxml

   - 実際のプロジェクトでは pyproject.toml / requirements.txt に記載された依存をインストールしてください。

4. 環境変数を準備
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` を作成すると自動で読み込まれます（プロセス開始時）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   推奨する主要な環境変数（README 用サンプル）:
   - JQUANTS_REFRESH_TOKEN=あなたの_jquants_リフレッシュトークン  ← 必須（ETL 用）
   - OPENAI_API_KEY=あなたの_OpenAI_キー  ← ai.news_nlp / regime_detector を使う場合に必須
   - KABU_API_PASSWORD=kabuステーション接続パスワード（発注関連）
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  ← デフォルト
   - DUCKDB_PATH=data/kabusys.duckdb  ← デフォルトの DuckDB ファイルパス
   - SQLITE_PATH=data/monitoring.db    ← 監視用 sqlite（デフォルト）
   - KABUSYS_ENV=development|paper_trading|live  ← 環境
   - LOG_LEVEL=INFO|DEBUG|...  ← ログレベル
   - PID_FILE_PATH / KILL_FLAG_PATH / thresholds（監視設定）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用、任意）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データディレクトリを作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要な API / 実行例）

ここでは Python から直接呼び出す例を示します。DuckDB 接続は `duckdb.connect(path)` を利用します。

- 日次 ETL を実行（run_daily_etl）
  ```
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコア（指定日）
  - OpenAI API キーが環境変数 OPENAI_API_KEY に設定されていること
  ```
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026,3,20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（regime scoring）
  ```
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ用 DB 初期化
  ```
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/monitoring_audit.duckdb")
  # conn は初期化済み DuckDB 接続
  ```

- 市場カレンダーの判定ユーティリティ
  ```
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026,3,20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- 研究モジュール（例：モメンタム算出）
  ```
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026,3,20))
  ```

注意点
- AI 系（score_news/score_regime）は OpenAI API を呼び出します。API キーと使用料に注意してください。
- DB 書き込みは冪等性（DELETE→INSERT など）やトランザクションを多用していますが、DuckDB のバージョン差分に注意してください。
- ニュース収集モジュールは SSRF 対策や XML パースの安全化（defusedxml）を行っています。

---

## 環境変数（主要一覧）

- JQUANTS_REFRESH_TOKEN (必須 for J-Quants)
- OPENAI_API_KEY (score_news / regime_detector を使う場合必須)
- KABU_API_PASSWORD (kabu API を使う場合必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知用)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live) — 不正値は例外
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

設定は package 内の `kabusys.config.settings` から参照できます。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP スコア計算（ai_scores へ保存）
    - regime_detector.py         — 市場レジーム判定（market_regime へ保存）
  - data/
    - __init__.py
    - pipeline.py                — ETL パイプライン & run_daily_etl 等
    - jquants_client.py          — J-Quants API クライアント（取得・保存）
    - news_collector.py          — RSS 収集（raw_news 保存）
    - calendar_management.py     — 市場カレンダー、営業日ロジック
    - quality.py                 — データ品質チェック
    - stats.py                   — 統計ユーティリティ（zscore）
    - etl.py                     — ETLResult 再エクスポート
    - audit.py                   — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算（momentum/value/volatility）
    - feature_exploration.py     — 将来リターン、IC、rank、summary
  - monitoring/ (not shown in code listing) — 監視・実行制御関連（PID / kill flag 等）
  - execution/, strategy/, monitoring/ (パッケージエクスポート対象として __all__ に含むが詳細はコードベース参照)

---

## 開発・運用上の注意

- 自動環境変数ロードはプロジェクトルート（.git / pyproject.toml）から行われます。CI などで制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し部分はリトライ・フォールバック実装があり、失敗時は安全側（macro_sentiment=0.0 等）で継続する仕組みになっていますが、運用での API コストとレイテンシを考慮してください。
- J-Quants API のレート制御（120 req/min）に対応するため専用の RateLimiter を使っています。大量データ取得時は API の制限に合わせた設計をしてください。
- DuckDB のバージョン差異により executemany の振る舞い等に差が出る場合があります（コード中に互換性考慮のコメントあり）。

---

もし README に特定の実行例（スケジュールジョブ設定、docker-compose、systemd サービス定義 など）や、pyproject/requirements の内容を追加したい場合は、その情報を教えてください。README を運用ドキュメント向けに拡張して作成します。