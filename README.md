# KabuSys

日本株向けの自動売買・データパイプライン基盤ライブラリです。  
ETL（J-Quants）、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログ（DuckDB）などを統合して、バックテスト／リサーチ／実行フローの基盤を提供します。

バージョン: 0.1.0

---

## 特徴（概要）

- J-Quants API を用いた差分 ETL（株価・財務・カレンダー）と品質チェック
- RSS ベースのニュース収集（SSRF 対策・トラッキング除去・前処理）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント解析と市場レジーム判定
- ファクター計算（モメンタム / ボラティリティ / バリュー）および特徴量解析ユーティリティ
- 監査ログ（signal → order_request → executions）のための冪等な DuckDB スキーマ
- 環境変数による設定読み込み（.env / .env.local 自動読み込み / 無効化オプションあり）
- Look-ahead バイアス防止を意識した設計（日時参照や DB クエリの排他条件）

---

## 主な機能一覧

- ETL
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl（kabusys.data.pipeline）
- データ品質チェック
  - run_all_checks（欠損・重複・スパイク・日付不整合）
- ニュース収集
  - fetch_rss / preprocess_text / news 保存ロジック（kabusys.data.news_collector）
- ニュース NLP（OpenAI）
  - score_news（銘柄別センチメントを ai_scores に保存）
- 市場レジーム判定（MA + マクロニュース）
  - score_regime（kabusys.ai.regime_detector）
- リサーチ
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- 監査ログ初期化
  - init_audit_db / init_audit_schema（kabusys.data.audit）
- J-Quants クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / save_*（kabusys.data.jquants_client）

---

## セットアップ手順

前提: Python 3.10+（typing 機能を使用）。プロジェクトは src パッケージ形式です。

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール  
   （本コードベースで使用される主要依存の例）
   ```bash
   pip install duckdb openai defusedxml
   ```
   実際のプロジェクトでは requirements.txt / pyproject.toml に依存を定義してください。

4. 環境変数設定
   - 推奨: プロジェクトルートに `.env` / `.env.local` を作成。
   - 自動読み込みはデフォルトで ON。テスト等で無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   必須（本システムで直接参照される環境変数）:
   - JQUANTS_REFRESH_TOKEN   — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD       — kabuステーション API パスワード
   - SLACK_BOT_TOKEN         — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID        — Slack チャンネル ID
   - OPENAI_API_KEY          — （score_news / score_regime 実行時に必要。引数で注入も可）

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   KABU_API_PASSWORD=...
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

5. データベースの配置（デフォルト）
   - DuckDB path: data/kabusys.duckdb（設定は環境変数 DUCKDB_PATH）
   - 監視用 SQLite path: data/monitoring.db（環境変数 SQLITE_PATH）

---

## 使い方（サンプル）

以下は Python REPL や実行スクリプトでの利用例です。

- DuckDB 接続を作り ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを計算して ai_scores に保存
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("scores written:", n_written)
  ```

- 市場レジームスコアを算出（1321 の MA200 乖離 + マクロニュース）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ用の DuckDB を初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- RSS を取得（news_collector）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["title"], a["datetime"])
  ```

注意:
- score_news / score_regime は OpenAI API を呼び出します。api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- DuckDB のテーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime, market_calendar 等）は ETL / schema 初期化処理で作成される前提です。実運用前に適切なスキーマ初期化手順を行ってください（プロジェクト内スキーマ初期化ユーティリティがある場合はそれを使用）。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (推奨) — OpenAI 呼び出し用キー（score_news/score_regime）
- KABU_API_PASSWORD (必須) — kabu API
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動ロードを無効化

設定は .env / .env.local をプロジェクトルートに置くことで自動的に読み込まれます（プロジェクトルートは .git または pyproject.toml を基準に探索）。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI）と score_news
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー（営業日判定 / next/prev / update job）
    - etl.py                  — ETL 公開インターフェース
    - pipeline.py             — ETL パイプライン主処理（run_daily_etl 等）
    - stats.py                — zscore_normalize 等汎用統計
    - quality.py              — データ品質チェック
    - audit.py                — 監査ログスキーマ初期化 / init_audit_db
    - jquants_client.py       — J-Quants API クライアント + 保存関数
    - news_collector.py       — RSS 取得・前処理・保存ユーティリティ
    - etl.py                  — ETL 型の再エクスポート（ETLResult）
  - research/
    - __init__.py
    - factor_research.py      — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py  — calc_forward_returns / calc_ic / factor_summary / rank

---

## 運用上の注意 / 設計ポリシー（要点）

- Look-ahead バイアス回避: 内部実装は date を引数で受け取り、datetime.today() を直接参照しない設計が多く採用されています。バックテスト環境で過去時点のデータだけを与えて再現性を確保してください。
- OpenAI 呼び出し: レートや障害に備えたリトライ・フェイルセーフ（失敗時は 0.0 を返す等）が実装されていますが、API キーの管理とコスト抑制には注意してください。
- ETL は差分取得（最終取得日ベース）とバックフィルを組み合わせ、後出し修正を吸収する仕様です。
- RSS 収集は SSRF 防止・受信サイズ制限・トラッキング除去などを実施しています。外部 URL の扱いに注意。

---

## よくある質問

Q: テーブルスキーマや初期化はどうする？  
A: audit 用スキーマは kabusys.data.audit.init_audit_db / init_audit_schema で作成できます。その他 ETL が想定する raw_* テーブルはプロジェクトの schema 初期化ユーティリティ（もし存在する場合）で作成してください。無ければ DuckDB に適切な CREATE TABLE 文を用意する必要があります。

Q: テストで .env の自動読み込みを無効にしたい  
A: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

README に記載のない細かい挙動や追加のユーティリティはソースコード内の docstring とコメントに詳細が書かれています。運用や実装変更時は該当モジュールの docstring を参照してください。必要であれば README を拡張して、スキーマ定義例や運用手順（cron / airflow / GitHub Actions）を追加できます。