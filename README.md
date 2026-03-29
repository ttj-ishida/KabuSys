# KabuSys

日本株向けの自動売買 / データプラットフォーム用 Python ライブラリ群です。  
ETL（J-Quants 経由）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ（約定トレーサビリティ）など、運用に必要な主要コンポーネントをモジュール化して提供します。

バージョン: 0.1.0

---

## 主な特徴 (概要)

- J-Quants API を使った差分 ETL（株価日足、財務、JPX カレンダー）
- DuckDB を使ったローカルデータベース保存（冪等保存：ON CONFLICT DO UPDATE）
- ニュース収集（RSS）と記事の前処理、安全対策（SSRF、サイズ制限、defusedxml）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価（銘柄別・マクロ）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメントの合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計サマリー）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ
- 環境変数 / .env の自動読み込み（プロジェクトルートを検出）

---

## 機能一覧（モジュール別）

- kabusys.config
  - 環境変数読み込み・検証、settings オブジェクト（J-Quants トークン、OpenAI など）
  - 自動 .env / .env.local 読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得／保存関数、認証・レート制御・リトライ）
  - pipeline / etl: 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 取得・前処理・raw_news への保存ロジック（SSRF 対策、gzip 対応）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats: 汎用統計（Zスコア正規化）
  - audit: 監査ログスキーマ定義・初期化ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュース記事をまとめて LLM へ送り、銘柄ごとの ai_score を生成して ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロ記事の LLM スコアを合成して market_regime を書き込み
- kabusys.research
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン、IC、統計サマリー、ランク関数など

設計上のポイント:
- ルックアヘッドバイアスを避けるため、ほとんどの関数は内部で datetime.today() を参照せず、呼び出し側が target_date を渡す方式を採用。
- API 呼び出しは堅牢性を重視（リトライ、バックオフ、フェイルセーフでの継続）。
- DuckDB を主なローカル永続層と想定（設定でパスを指定可）。

---

## 前提 / 必要条件

- Python 3.10 以上（型ヒントに X | Y 形式を使用）
- 必須ライブラリ（最低限）
  - duckdb
  - openai（v1 SDK など、OpenAI の Chat Completions を利用できるもの）
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）

パッケージ例:
pip install duckdb openai defusedxml

（本レポジトリに requirements.txt / packaging がある場合はそれに従ってください）

---

## 環境変数（主なもの）

以下は Settings クラスで参照される主要変数（.env に設定して利用します）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（発注系を使う場合）
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知に使うトークン（通知機能を使う場合）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL (任意) — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"
- OPENAI_API_KEY — OpenAI 呼び出しで個別に渡さない場合に参照される

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を探索）にある `.env` → `.env.local` の順に読み込みます。
- OS 環境変数が優先され、.env.local は既存値を上書きします。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば: pip install -r requirements.txt）

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成し、以下を記載（例）:

     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

   - 自動読み込みが有効なら起動時に読み込まれます。

5. データベースの初期化（監査用 DB を使う場合）
   - Python REPL やスクリプトで:

     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

   - または既存 DuckDB 接続へスキーマを追加:

     import duckdb
     from kabusys.data.audit import init_audit_schema
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)

---

## 使い方（代表的な例）

以下は一例です。各関数は DuckDB 接続を受け取るので、まず接続を作成します。

- 日次 ETL の実行（株価・財務・カレンダーの差分取得）
  - 例:

    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュース NLP スコア生成（指定日分）
  - 例:

    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"score_news wrote {n_written} scores")

  - 引数 `api_key` を渡すと環境変数に依存せずに実行できます。渡さない場合は `OPENAI_API_KEY` を参照します。

- 市場レジーム判定
  - 例:

    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数か引数で指定

- 監査スキーマ初期化（既存 DB へ追加）
  - 例:

    import duckdb
    from kabusys.data.audit import init_audit_schema

    conn = duckdb.connect("data/kabusys.duckdb")
    init_audit_schema(conn, transactional=True)

- 研究用ファクター計算（例：モメンタム）
  - 例:

    from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum

    conn = duckdb.connect("data/kabusys.duckdb")
    results = calc_momentum(conn, target_date=date(2026, 3, 20))
    # results は [{ "date": ..., "code": "...", "mom_1m": ..., ... }, ...]

---

## 実運用上の注意点 / 設計ノート

- Look-ahead bias（未来情報参照）を避ける設計：
  - 関数は基本的に target_date を引数で受け、内部で現在日時を直接参照しないようになっています。
- フェイルセーフ：
  - LLM / API が失敗してもシステム全体が停止しない（多くの箇所でフォールバック値やスキップを採用）。
- リトライとレート制御：
  - J-Quants は固定スロットリング（120 req/min）、OpenAI 呼び出しはリトライ / バックオフが組まれています。
- セキュリティ：
  - RSS 収集は SSRF 対策、受信サイズ制限、XML パースの安全化（defusedxml）を実装。

---

## ディレクトリ構成

リポジトリは `src/kabusys` 配下に実装をまとめています。主なファイル・モジュール構成は下記の通り（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
    - (その他データ関連ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring, execution, strategy 等（package public API として __all__ で公開予定）

（README 内のファイルは実装の抜粋に基づく。完全なツリーは git ls-tree 等で確認してください）

---

## 開発・テスト向けヒント

- 自動 .env 読み込みを無効化したいテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI / J-Quants 呼び出し部分は個別にモック可能なように実装されています（ユニットテストでは _call_openai_api 等を patch してください）。
- DuckDB の接続はメモリモード `":memory:"` もサポートされている関数があります（例: init_audit_db(":memory:")）。

---

## ライセンス / 貢献

本 README はコードベースに基づく概要・利用方法を示しています。実際の配布パッケージや組織内ポリシーに従ってライセンスや貢献ガイドラインを追加してください。

---

質問や README に加えてほしい具体的な例（例: CI 実行方法、docker-compose サンプル、requirements.txt の内容など）があれば教えてください。README をそれに合わせて追記します。