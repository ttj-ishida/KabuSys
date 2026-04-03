# KabuSys — 日本株自動売買システム（README）

概要
---
KabuSys は日本株を対象としたデータ収集・品質管理・リサーチ・AIによるニュースセンチメント解析・市場レジーム判定・ETL を備えたライブラリ群です。DuckDB をデータストアに用い、J-Quants API から株価・財務・カレンダーを取得し、OpenAI（gpt-4o-mini 等）を用いたニュース分析で銘柄ごとの AI スコアを生成します。監査（オーダー／シグナル追跡）用のスキーマも提供します。

主な機能
---
- 環境変数/設定管理（.env/.env.local の自動読み込み、Settings API）
- J-Quants API クライアント（レート制御、認証リフレッシュ、リトライ、ページネーション）
- ETL パイプライン（株価/財務/カレンダーの差分取得・保存・品質チェック）
- ニュース収集（RSS → raw_news、SSRF 対策、前処理）
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコアリング、バッチ・リトライ対策）
- 市場レジーム判定（ETF 1321 の MA 乖離 + マクロニュースセンチメントの合成）
- データ品質チェック（欠損／重複／スパイク／日付不整合）
- 監査ログスキーマの初期化・管理（signal → order_request → executions のトレース設計）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z-score 正規化）
- 汎用統計ユーティリティ（z-score など）

セットアップ手順
---
1. Python と仮想環境
   - Python 3.9+ を推奨（プロジェクト要件に合わせて調整してください）。
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）
   - pip install duckdb openai defusedxml
   - 実運用・開発時は logger ライブラリ等を追加してください。
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

3. 環境変数 / .env
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（Settings.jquants_refresh_token）
     - KABU_API_PASSWORD — kabu ステーション API 用パスワード（Settings.kabu_api_password）
   - AI/API 関連（機能を使う場合は必須）:
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で利用）
   - その他の設定（省略時はデフォルトがあるものも含む）:
     - KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、デフォルト data/monitoring.db）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development | paper_trading | live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

   - サンプル（.env.example を参考に作成してください）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DB 初期化（監査スキーマなど）
   - 監査ログ用 DB を初期化する例:
     ```py
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - ETL / データ格納に用いる DuckDB ファイルパスは Settings.duckdb_path を参照するよう設計されています。

使い方（簡易例）
---
- DuckDB 接続と日次 ETL 実行
  ```py
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```
  - run_daily_etl はカレンダー → 株価 → 財務 → 品質チェックの順で差分 ETL を行い、ETLResult を返します。

- ニュースセンチメント（銘柄別 AI スコア）の計算
  ```py
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書込銘柄数:", n_written)
  ```
  - OPENAI_API_KEY が環境変数に設定されていることを想定。api_key 引数で明示的に渡すことも可能。

- 市場レジーム判定
  ```py
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime テーブルへ保存します。

- J-Quants クライアントを直接使う（データ取得）
  ```py
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  quotes = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
  ```

- 監査スキーマを作成する（既存接続へ）
  ```py
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

ディレクトリ構成（主要ファイル）
---
リポジトリの主要モジュールは src/kabusys 以下にあります（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込み含む）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの銘柄別センチメント（OpenAI 呼び出し、バッチ・検証）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存・認証・レート制御）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再エクスポート
    - news_collector.py      — RSS ニュース収集・前処理・SSRF 対策
    - calendar_management.py — 市場カレンダー管理（営業日判定／更新ジョブ）
    - quality.py             — データ品質チェック
    - stats.py               — Z-score などの統計ユーティリティ
    - audit.py               — 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py     — モメンタム・ボラティリティ・バリュー算出
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - （将来的に strategy/ execution/ monitoring 等のパッケージを想定）

開発上の注意・設計方針
---
- ルックアヘッドバイアス対策:
  - モジュールの多くは datetime.today() / date.today() を直接参照せず、外部から target_date を受け取る設計です。
  - DB クエリも target_date 未満のデータしか参照しない等の配慮があります。
- フェイルセーフ:
  - 外部 API（OpenAI/J-Quants）失敗時はゼロスコアで継続したり部分的に処理をスキップして全体停止を避ける実装が多くあります。
- 冪等性:
  - DuckDB への保存は可能な限り ON CONFLICT / DELETE→INSERT 等で冪等に行われます。
- セキュリティ:
  - news_collector は SSRF 対策・XML インジェクション対策（defusedxml）・レスポンスサイズ上限等の保護を実装しています。

よくある運用フロー（例）
---
1. 仮想環境を立てて依存をインストールする
2. .env を作成して J-Quants / OpenAI キー等を設定する
3. DuckDB を初期化し監査スキーマを作成する（init_audit_db）
4. cron / Airflow / systemd タイマーで日次 ETL（run_daily_etl）を実行
5. ETL 後に news_nlp → score_news、regime_detector → score_regime を実行して AI スコア・レジーム情報を更新
6. 研究やバックテストでは research/* の関数を利用

貢献・テスト
---
- ユニットテストやモックを用いた外部 API 呼び出しの差し替えを想定した設計（_call_openai_api などをモック可能）。
- lint/formatting、追加の CI 設定を導入して品質を担保してください。

問い合わせ
---
仕様や実装に関する質問、拡張提案があれば Issue を立ててください。

---

この README はコードベースの要点をまとめたものです。具体的な使い方・パラメータ・API 仕様は各モジュールの docstring を参照してください。必要ならサンプル .env.example やサンプルワークフロー（スクリプト）も追加で作成できます。