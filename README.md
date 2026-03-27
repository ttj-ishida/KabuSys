# KabuSys

日本株向け自動売買・データプラットフォームライブラリ KabuSys の README（日本語）。

概要、主要機能、セットアップ手順、簡単な使い方、ディレクトリ構成を記載しています。

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、ニュース収集・NLP（OpenAI）、ファクター計算、ETL パイプライン、監査ログを含む自動売買プラットフォームの基盤ライブラリです。  
主に以下を提供します：

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への冪等保存
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI を使ったニュースセンチメント（銘柄別）およびマクロセンチメントによる市場レジーム判定
- ファクター計算（モメンタム、バリュー、ボラティリティなど）と研究用ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution の追跡）を作るためのスキーマと初期化機能
- 設定管理（.env 自動読み込み、環境変数経由の設定）

設計方針として、ルックアヘッドバイアスの排除（datetime.today() を直接参照しない等）、外部 API の堅牢なリトライ/バックオフ処理、DuckDB を中心としたローカルデータベース管理、冪等性の確保を重視しています。

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（rate-limit、トークン自動更新、ページネーション、DuckDB への保存）
  - news_collector: RSS 取得、前処理、raw_news への保存（SSRF 対策、トラッキング除去）
  - pipeline / etl: 日次 ETL（カレンダー, 株価, 財務の差分取得・保存）と ETL 結果表現 (ETLResult)
  - quality: 品質チェック（欠損、スパイク、重複、日付不整合）
  - audit: 監査ログスキーマ初期化（signal / order_request / executions）
  - calendar_management: 営業日判定、カレンダー更新ジョブ
  - stats: z-score 正規化など汎用統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI に投げて ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA とマクロセンチメントを合成して market_regime を算出
- research/
  - factor_research: モメンタム / バリュー / ボラティリティファクターの計算
  - feature_exploration: 将来リターン計算、IC（情報係数）、統計サマリー等
- config: .env 自動読み込み・環境変数アクセスラッパー（settings）

## 必要条件 / 依存

- Python 3.10+
- 必要ライブラリ（主なもの）
  - duckdb
  - openai (OpenAI の Python SDK v1 系を想定)
  - defusedxml
- 標準ライブラリのみで完結する部分も多くありますが、OpenAI / DuckDB / defusedxml は機能利用時に必須です。

例：
pip install duckdb openai defusedxml

（プロジェクト配布がある場合は、requirements.txt / pyproject.toml を利用してください）

## 環境変数 / 設定

KabuSys は環境変数およびプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主な必須環境変数：

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client が ID トークンを取得するために使用）
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注関連、将来モジュールで使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（監視・通知用）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp, regime_detector 等）で必要

データベース関連（デフォルト値あり）：

- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: monitoring 用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" / "paper_trading" / "live"、デフォルト "development")
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)

.env を作る際の例（.env.example を参考にしてください）：
JQUANTS_REFRESH_TOKEN=...
OPENAI_API_KEY=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=./data/kabusys.duckdb

## セットアップ手順（ローカル開発 / 実行）

1. リポジトリをクローン / ソースを用意

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存をインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください）

4. 環境変数の設定
   - プロジェクトルートに `.env` を作成するか、環境変数をエクスポートしてください。
   - 自動読み込みは .env → .env.local の順で行われ、OS 環境変数が最優先です。

5. DuckDB データベースの準備
   - デフォルトパスは settings.duckdb_path（例: data/kabusys.duckdb）。
   - ETL 実行前に DuckDB に必要なテーブルを作成する初期化スクリプトがある場合は実行してください（本コードベースでは ETL がテーブルの存在をチェックして処理します）。監査ログ専用 DB は以下の helper を使えます（例を参照）。

## 使い方（簡単なコード例）

※ 以下は Python REPL / スクリプトでの呼び出し例です。各操作は DuckDB の接続オブジェクト（duckdb.connect）を受け取ります。

- ETL（日次 ETL の実行）
  - 目的: 市場カレンダー、株価日足、財務データの差分取得と保存、品質チェック
  - 例：
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(Path("data/kabusys.duckdb")))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュース（銘柄別）スコアリング
  - news_nlp.score_news は raw_news / news_symbols テーブルを参照し、ai_scores に書き込みます（OpenAI API キーが必要）。
  - 例：
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026,3,20))
    print("書き込んだ銘柄数:", n_written)

- 市場レジーム判定
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime に保存します（OpenAI API キーが必要）。
  - 例：
    import duckdb
    from datetime import date
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20))

- 監査ログ DB 初期化（監査専用 DB を作る）
  - 例：
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # これで signal_events / order_requests / executions テーブルが作成されます

- 設定参照
  - 環境変数は kabusys.config.settings 経由で参照できます：
    from kabusys.config import settings
    print(settings.duckdb_path, settings.env)

## 注意事項 / ベストプラクティス

- OpenAI を使う機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）を必要とします。API 呼び出しはリトライ、クリップ、フェイルセーフ（失敗時はゼロスコアへフォールバック）を備えていますが、API 使用量やレスポンス形状に注意してください。
- J-Quants API の利用にはリフレッシュトークンが必要です（JQUANTS_REFRESH_TOKEN）。トークンは settings.jquants_refresh_token から取得します。
- データ品質チェック（quality）を ETL 後に必ず実行し、重要な問題が検出された場合は手動で確認してください。
- DuckDB を用いたローカル DB は ETL の核ですが、バックテスト等でルックアヘッドバイアスを避けるために「いつそのデータが取得されたか（fetched_at）」を考慮してください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を検出して行います。CI/テスト環境などで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## 主要なディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                  — ニュースセンチメント（銘柄別）
  - regime_detector.py           — マクロ＋MA による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント（取得 + DuckDB 保存）
  - news_collector.py            — RSS 取得・前処理
  - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
  - etl.py                       — ETL 便利エクスポート（ETLResult）
  - calendar_management.py       — 市場カレンダー管理 / 営業日判定
  - quality.py                   — データ品質チェック
  - audit.py                     — 監査ログスキーマ初期化
  - stats.py                     — z-score 等汎用統計
- research/
  - __init__.py
  - factor_research.py           — ファクター計算（momentum/value/volatility）
  - feature_exploration.py       — 将来リターン/IC/統計サマリー

（上記は主要モジュールの抜粋です。実プロジェクトでは追加のモジュールやスクリプトが存在する可能性があります）

## 最後に

この README はコードベースに含まれるドキュメント文字列と設計コメントを基に作成しています。実運用を行う前に、環境変数や API キーの管理、DB バックアップ、ログ・監視、テスト（モックを用いた OpenAI/J-Quants 呼び出しの検証）を十分に行ってください。

必要であれば、README に具体的な .env.example、スキーマ初期化スクリプト、CI 設定、実行スクリプト例（cron / Airflow / prefect など）を追加できます。どのような追加情報が欲しいか教えてください。