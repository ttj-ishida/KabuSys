# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログ（オーダー／約定トレース）、カレンダー管理などを提供します。

この README はコードベース（src/kabusys 以下）に基づく簡潔な使い方・セットアップを日本語でまとめたものです。

---

## 概要

KabuSys は以下を主眼に設計されたモジュール群を含みます。

- データパイプライン（J-Quants API 経由で株価・財務・カレンダーを差分取得 → DuckDB に保存）
- ニュース収集（RSS）と NLP スコアリング（OpenAI を利用）
- 市場レジーム判定（ETF の MA200 とマクロニュースの LLM センチメントを合成）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損・重複・スパイク・日付不整合の検出）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- 環境設定の読み込みユーティリティ（.env 自動読み込み等）

設計上のポイント：
- ルックアヘッドバイアスを避けるため、内部処理は datetime.today() を直接参照しない実装方針。
- DuckDB を中心に SQL と最小限の標準ライブラリで実装。
- OpenAI / J-Quants / RSS に対して堅牢なリトライやエラーハンドリングを備える。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch/save 系）
  - マーケットカレンダー管理（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（RSS -> raw_news 保存、SSRF対策・トラッキングパラメータ除去）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査ログスキーマの初期化（init_audit_schema, init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュースのセンチメントスコアリング（score_news）
  - 市場レジーム判定（score_regime）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索・IC計算（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数／.env 自動読み込み、Settings オブジェクト（settings）による集中参照

---

## 必要要件（推奨）

少なくとも以下の Python パッケージが必要です（プロジェクトの requirements.txt が無い場合の最小セット）：

- Python 3.9+
- duckdb
- openai (OpenAI の v1 SDK を想定)
- defusedxml

その他、ネットワーク・外部API（J-Quants、OpenAI）へのアクセスが必要です。

---

## 環境変数

主に以下の環境変数を使用します（必須・任意の区別は Settings を参照）。

必須（実行する機能に応じて必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（データ ETL 用）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先
- KABU_API_PASSWORD — kabuステーション API を使う場合

OpenAI:
- OPENAI_API_KEY — news_nlp / regime_detector を使う際に参照（score_news/score_regime は引数での注入も可）

任意／デフォルトあり:
- KABUSYS_ENV — 環境（development / paper_trading / live）、デフォルト `development`
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）、デフォルト `INFO`
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト "http://localhost:18080/kabusapi"）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite path（デフォルト `data/monitoring.db`）

.env 自動読み込み:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動読み込みします。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

---

## セットアップ手順（ローカルでの開発・実行例）

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※プロジェクトに requirements.txt がある場合はそれを使用してください。

3. .env を作成
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を作成し、必要な環境変数を設定します。

4. DuckDB データベース準備
   - デフォルトは `data/kabusys.duckdb`。settings.duckdb_path で変更可能。
   - 必要に応じて監査ログ DB を初期化:
     - Python 例:
       from kabusys.data.audit import init_audit_db
       conn = init_audit_db("data/audit.duckdb")

5. OpenAI API キー
   - score_news / score_regime を使うなら `OPENAI_API_KEY` を設定（または関数呼び出し時に api_key を渡す）

---

## 使い方（簡単なコード例）

以下は最低限の使用例です。実行は Python スクリプト内で行います。

- ETL（日次パイプライン）を実行する例:
  - Python:
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str)  # 例: duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

  - run_daily_etl は市場カレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック を順に実行し、ETLResult を返します。

- ニュースのスコアリング（score_news）
  - Python:
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
    print(f"書込件数: {written}")

  - score_news は raw_news と news_symbols を読み、ai_scores テーブルへ結果を書き込みます。
  - api_key が None の場合は環境変数 OPENAI_API_KEY を参照します。

- 市場レジーム判定（score_regime）
  - Python:
    from kabusys.ai.regime_detector import score_regime
    # conn は DuckDB 接続（prices_daily, raw_news, market_regime を参照）
    score_regime(conn, target_date=date(2026,3,20), api_key=None)

  - 判定ロジックは ETF 1321 の MA200 乖離（重み 70%）とマクロニュースセンチメント（重み 30%）を合成します。

- 監査ログスキーマ初期化
  - init_audit_schema(conn) または init_audit_db(db_path) を使用して監査用テーブルを作成します。

---

## 注意点 / 実装上の補足

- OpenAI 呼び出し
  - news_nlp / regime_detector は OpenAI の JSON-mode（model gpt-4o-mini を想定）を利用します。
  - API エラーや JSON パース失敗時にはフェイルセーフ（0.0 を返す、もしくはスキップ）する設計です。
  - テスト時には内部の _call_openai_api をモックすることが推奨されています。

- J-Quants クライアント
  - リクエストは固定間隔のレートリミット（120 req/min）に従い、401 の場合はトークンを自動リフレッシュします。
  - get_id_token() は JQUANTS_REFRESH_TOKEN を利用して id token を取得します。

- ニュース収集（RSS）
  - SSRF 対策、応答サイズ上限、トラッキングパラメータ削除、gzip 解凍上限などセキュリティに配慮した実装です。

- 日付取り扱い
  - 多くのモジュールで「ルックアヘッドバイアス回避」のため、target_date を明示的に渡すことを前提としています。内部で date.today() を参照しないか限定して使用しています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数/Settings（.env 自動読み込みロジック含む）
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）および ETLResult
  - quality.py — データ品質チェック
  - news_collector.py — RSS ニュース収集
  - calendar_management.py — 市場カレンダー管理
  - stats.py — zscore_normalize 等
  - audit.py — 監査ログスキーマ初期化（init_audit_schema, init_audit_db）
  - etl.py — ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py — calc_momentum, calc_value, calc_volatility
  - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank
- research/*（その他リサーチユーティリティ）

その他：
- data/ 以下に DuckDB・SQLite ファイルを置くことを想定（DUCKDB_PATH / SQLITE_PATH）。

---

## 開発・貢献

- テスト: 各モジュールは外部 API 呼び出し箇所に差し替え（mock）を容易にする設計です。例えば OpenAI 呼び出しは内部関数をモックして単体テストできます。
- Issue / PR: 実運用でのログ出力や例外ハンドリングの改善、ETL のパフォーマンス最適化等を歓迎します。

---

以上がこのコードベースの概要・セットアップ・利用方法のまとめです。  
追加で README に入れたいサンプルスクリプト、requirements.txt の生成、CI 実行方法などあれば教えてください。