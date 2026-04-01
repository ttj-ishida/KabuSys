# KabuSys

日本株向け自動売買・データ基盤ライブラリ（プロトタイプ）

概要：
KabuSys は日本株のデータ収集（J-Quants）、品質チェック、特徴量生成、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログなど自動売買システムに必要なプラットフォーム機能を提供する Python パッケージです。DuckDB をデータ格納に利用し、OpenAI（gpt-4o-mini）でニュースセンチメントを評価する機能を含みます。

主な用途：
- 日次 ETL（株価・財務・カレンダー）と品質チェック
- ニュース収集と銘柄別センチメント算出（AI）
- 市場レジーム判定（MA200 勾配 + マクロニュース）
- 研究用のファクター計算・特徴量解析
- 発注フローの監査ログスキーマ初期化

------------------------------------------------------------
目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（例）
- 環境変数 / 設定
- ディレクトリ構成（主要ファイル一覧）
- 補足・トラブルシュート
------------------------------------------------------------

プロジェクト概要
- パッケージ名: kabusys
- 目的: 日本市場に特化したデータプラットフォーム / 研究ツール群とニュース NLP に基づく補助機能を提供し、自動売買システムの上位レイヤで利用できる基礎を実装。
- データ保存: DuckDB（ローカルファイルまたは :memory:）
- 外部依存: J-Quants API（株価・財務・カレンダー）、OpenAI（ニュースセンチメント）、kabuステーション API（注文実行に利用想定）

主な機能一覧
- 環境設定管理
  - .env ファイルの自動読み込み（プロジェクトルート検出）
  - settings オブジェクト経由で必須設定にアクセス
- Data ETL / 品質管理
  - 差分 ETL（prices / financials / calendar）
  - 品質チェック（欠損、スパイク、重複、日付整合性）
  - J-Quants クライアント（ページネーション・リトライ・レート制御・トークン自動更新）
- カレンダー管理
  - 営業日判定、次/前営業日取得、カレンダー更新バッチ
- ニュース収集
  - RSS 取得（SSRF ガード、トラッキングパラメータ除去、前処理）
- AI（ニュース NLP / レジーム検出）
  - 銘柄ごとのニュースセンチメントを ai_scores に書き込む score_news
  - ETF 1321 の MA200 乖離とマクロニュースを合成して市場レジームを判定する score_regime
  - OpenAI API 呼び出しはリトライ・フォールバック実装（失敗時は安全側の値にフォールバック）
- 研究用ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - クロスセクション Z-score 正規化ユーティリティ
- 監査ログ（オーダー/シグナル追跡）
  - 監査スキーマの初期化（監査テーブル・インデックス、init_audit_db）

セットアップ手順（ローカル開発用）
1. Python 仮想環境の作成（例）
   - python 3.10+ を推奨
   - 仮想環境作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージ（代表）
   - requirements.txt は本コードベースに含まれていませんが、主要依存は次の通りです：
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

3. リポジトリルートに .env を作成
   - 設定の自動読み込み: パッケージはプロジェクトルート（.git または pyproject.toml を基準）を探して .env / .env.local を読み込みます。
   - サンプル（必要な環境変数は後述）:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb

4. DuckDB 初期化（監査 DB 例）
   - Python REPL かスクリプトから:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
   - これにより監査用のテーブル群とインデックスが作成されます。

5. 自動ロードが不要なテスト等では環境変数で無効化可能:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

簡単な使い方（サンプル）
- 日次 ETL 実行（DuckDB 接続を渡す）
  - 例:
    - import duckdb
    - from datetime import date
    - from kabusys.data.pipeline import run_daily_etl
    - conn = duckdb.connect("data/kabusys.duckdb")
    - result = run_daily_etl(conn, target_date=date(2026,3,20))
    - print(result.to_dict())

- ニューススコアリング（AI）
  - score_news は raw_news / news_symbols / ai_scores を使用
  - 例:
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - from datetime import date
    - n = score_news(conn, date(2026,3,20))  # OPENAI_API_KEY は環境変数か api_key 引数で指定

- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_regime(conn, date(2026,3,20))  # OpenAI API key 必要

- 監査 DB 初期化
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/monitoring_audit.duckdb")

主要な環境変数（必須／推奨）
- OPENAI_API_KEY: OpenAI API キー（AI 評価に必須）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL に必須）
- KABU_API_PASSWORD: kabu API パスワード（発注用）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知に使用
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視設定
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

注意: settings.jquants_refresh_token 等は必須です。設定されていない場合 Settings プロパティが ValueError を投げます。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py         -- ニュースセンチメント算出（score_news）
    - regime_detector.py  -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   -- J-Quants API クライアント（fetch/save 関連）
    - pipeline.py         -- ETL 実装（run_daily_etl 等）
    - etl.py              -- ETLResult 再エクスポート
    - calendar_management.py -- 市場カレンダー管理
    - news_collector.py   -- RSS 収集ユーティリティ
    - quality.py          -- データ品質チェック
    - stats.py            -- zscore_normalize 等統計ユーティリティ
    - audit.py            -- 監査ログスキーマ初期化（init_audit_schema/init_audit_db）
    - ...（他ユーティリティ）
  - research/
    - __init__.py
    - factor_research.py  -- calc_momentum / calc_volatility / calc_value
    - feature_exploration.py -- calc_forward_returns / calc_ic / factor_summary / rank
  - monitoring/, strategy/, execution/ ...（パッケージ初期化に参照される想定）

補足・設計上のポイント
- Look-ahead bias 回避:
  - AI スコアリング・レジーム判定等は target_date を引数で受け取り、内部で datetime.today() を参照しない設計です。バックテストに安全です。
- フェイルセーフ:
  - OpenAI 呼び出しはリトライ・フォールバック（失敗時は macro_sentiment=0.0 等）で、処理継続を優先します。
- J-Quants クライアント:
  - 固定間隔レート制御（120 req/min）、リトライ、401 時のトークン自動更新などを実装しています。
- DB 操作は可能な限り冪等に設計（ON CONFLICT DO UPDATE / INSERT … DO NOTHING / トランザクション＋DELETE→INSERT のパターン）。

トラブルシュート（よくある問題）
- OpenAI API エラー:
  - レート制限やネットワークエラーが起きた場合はログに WARNING が出力され、スコアは 0.0 にフォールバックすることがあります。
- .env が読み込まれない:
  - パッケージはプロジェクトルートを .git または pyproject.toml で検出して自動的に .env を読み込みます。テスト時など自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany 空リスト制約:
  - 一部関数は DuckDB の制約に合わせて executemany に空リストを渡さないよう保護しています（内部でのチェック）。
- RSS 収集の SSRF/大容量対策:
  - news_collector はリダイレクト先検査、ホストがプライベートかのチェック、Content-Length と受信サイズの上限を持ちます。

貢献 / 拡張
- モジュールは比較的疎結合に設計されているため、以下のような拡張が行いやすいです:
  - 発注実行やブローカー連携の追加（execution 層）
  - strategy 層で signal_events を用いた戦略実装
  - Slack / モニタリング統合の強化

ライセンス / 注意
- 本 README はコードベースからの情報を元にした概要です。実運用前に必ずコードの安全性・規約遵守・取引リスク等を確認してください。

以上。必要であればサンプルスクリプトや .env.example のテンプレート、より詳細な API リファレンス（関数引数・戻り値）を追加で生成します。どの情報を優先的に README に追加しますか？