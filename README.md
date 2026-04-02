# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。本リポジトリはデータ収集（ETL）・データ品質チェック・ニュースNLP・市場レジーム判定・リサーチ用ファクター計算・監査ログ（トレーサビリティ）など、アルゴリズム取引システムに必要な基盤機能を提供します。

概要、機能、セットアップ、使い方、ディレクトリ構成を以下にまとめます。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの株価・財務・マーケットカレンダー等の差分 ETL（DuckDB を保存先）
- ETL 後のデータ品質チェック（欠損・スパイク・重複・日付不整合検出）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄ごとのスコア付与）
- マクロセンチメント × ETF MA200 乖離を用いた市場レジーム判定（bull/neutral/bear）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）および特徴量探索ユーティリティ
- 監査ログ（signal → order_request → executions）のためのテーブル定義・初期化
- 環境設定管理（.env 自動読み込み、必須設定のラッパー）

設計上、バックテストでのルックアヘッドバイアスを避けるために日付の扱いに注意が払われています（原則として date.today()/datetime.today() への直接依存を避ける）。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（fetch & save: daily quotes, financials, market calendar）
  - 差分 ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- データ品質管理
  - 欠損値検出、前日比スパイク検出、主キー重複チェック、日付整合性チェック
  - run_all_checks で一括実行し QualityIssue のリストを取得

- ニュース収集 / NLP
  - RSS フィード収集（SSRF 対応、トラッキング除去、最大サイズ制限）
  - ニュースの前処理（URL 除去、空白正規化）
  - OpenAI を使った銘柄ごとのニュースセンチメントスコア生成（score_news）

- 市場レジーム判定
  - ETF 1321 の MA200 乖離 × マクロニュースセンチメントの重み付け合成で日次レジームスコアを算出（score_regime）

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC 計算、統計サマリー、Z スコア正規化

- 監査ログ（Audit）
  - signal_events, order_requests, executions を含む監査スキーマ初期化（init_audit_schema / init_audit_db）
  - すべての監査タイムスタンプは UTC 保存

- 環境設定管理
  - settings オブジェクトから必須設定を取得（JQUANTS_REFRESH_TOKEN や SLACK_BOT_TOKEN 等）
  - .env / .env.local 自動読み込み（優先順位: OS 環境変数 > .env.local > .env）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 前提条件 / 推奨環境

- Python 3.10 以上（型注釈で | を使用しているため）
- DuckDB（duckdb パッケージ）
- OpenAI Python SDK（openai）
- defusedxml（RSS パースの安全化）
- その他標準ライブラリのみで多くを実装しています

最低限の Python パッケージ（例）:
- duckdb
- openai
- defusedxml

必要に応じて Slack 等のクライアントを導入してください（本コードベースでは Slack API は環境変数を参照する箇所のみ確認できます）。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト

   git clone <リポジトリURL>
   cd <repo>

2. 仮想環境作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール（例）

   pip install duckdb openai defusedxml

   （パッケージ化されている場合は pip install -e . や requirements.txt を利用してください）

4. 環境変数の設定

   本プロジェクトは複数の必須／任意環境変数を参照します。開発時はルートに .env を置くと自動読込されます（ただし OS 環境変数が優先）。

   重要な環境変数（例）

   - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

   自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を検出）を基準に行われます。自動読み込みを無効にする場合:

   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB スキーマ初期化（必要に応じて）

   監査ログスキーマを初期化する例:

   from kabusys.data.audit import init_audit_db
   from kabusys.config import settings

   conn = init_audit_db(settings.duckdb_path)  # または別 DB パス
   conn.close()

   注意: ETL 用の各種テーブルは別途スキーマ初期化関数（本リポジトリにある場合）で準備してください。監査スキーマは init_audit_schema / init_audit_db で作成できます。

---

## 使い方（簡単な例）

以下は最小限の利用例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY）を設定してください。

- DuckDB 接続を用意して日次 ETL を実行する

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()

- ニュースセンチメントを生成する（OpenAI キーが必要）

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  conn.close()

- 市場レジーム（マクロセンチメント + MA200）をスコアリングする

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  conn.close()

- 研究用ファクターを計算する

  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  results = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(results), results[:3])
  conn.close()

- 監査 DB を初期化する

  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  conn = init_audit_db(settings.duckdb_path)
  # 必要に応じて conn を利用
  conn.close()

ログレベルは環境変数 LOG_LEVEL で調整してください。

---

## 注意点 / トラブルシューティング

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。テスト等で自動読み込みを止めたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しはネットワークやレート制限に対してリトライ処理が実装されていますが、API キー未設定時は ValueError を投げます。
- DuckDB の executemany による空リストバインドに注意（モジュール側で保護済み）。ETL 等は部分失敗時に既存データを保護する実装方針です。
- ニュース収集は SSRF / 大容量レスポンス等への対策を実装していますが、RSS ソース追加時は信頼できるソースを指定してください。
- J-Quants API の呼び出しでは rate limiting（120 req/min）とトークン自動リフレッシュのロジックが組み込まれています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                -- 環境変数 / 設定管理（.env 自動読み込み・settings）
- ai/
  - __init__.py
  - news_nlp.py            -- ニュース NLP（score_news 等）
  - regime_detector.py     -- 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py      -- J-Quants API クライアント（fetch / save）
  - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
  - etl.py                 -- ETL 結果型のエクスポート（ETLResult）
  - stats.py               -- 汎用統計（zscore_normalize）
  - quality.py             -- データ品質チェック（check_missing_data 等）
  - news_collector.py      -- RSS 収集と前処理
  - calendar_management.py -- 市場カレンダー管理（is_trading_day 等）
  - audit.py               -- 監査ログスキーマ定義 / 初期化
- research/
  - __init__.py
  - factor_research.py     -- ファクター計算（momentum/volatility/value）
  - feature_exploration.py -- 将来リターン / IC / 統計サマリー
- research パッケージは data.stats を再利用

（その他、execution / monitoring / strategy 等のパッケージがプロジェクト全体として存在する設計になっていますが、本 README は現行の主要モジュールに焦点を当てています。）

---

## ライセンス / コントリビューション

本ドキュメントはコードベースの説明です。実際のライセンス情報、コントリビューションルールはリポジトリの LICENSE や CONTRIBUTING.md を参照してください。

---

ご不明点があれば、特定のユースケース（ETL の自動化、OpenAI 呼び出しのテスト、監査スキーマの拡張など）について詳細な使い方やサンプルコードを提供します。