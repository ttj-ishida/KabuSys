KabuSys — 日本株自動売買 / データ基盤ライブラリ
================================

概要
----
KabuSys は日本株のデータ収集（ETL）・品質チェック・研究（ファクター/特徴量探索）・ニュース/NLP によるセンチメント評価・市場レジーム判定・監査ログ初期化等を提供する内部ライブラリ群です。主に DuckDB をデータバックエンドに、J-Quants API からのデータ取得、OpenAI（gpt-4o-mini）を利用したニュース解析を行います。

設計上のポイント
- Look-ahead bias（先見バイアス）に配慮した設計：内部で datetime.today()/date.today() を使わない、ETL/解析は明示的な target_date を使用する。
- 冪等性：ETL の保存処理は ON CONFLICT / DO UPDATE を用いて何度実行しても正しく上書きされる。
- フェイルセーフ：外部 API エラー時はゼロやスキップして処理を継続するような設計箇所がある。
- テスト容易性：API 呼び出しや自動 .env ロードを差し替え可能（モック・環境変数で制御）。

主な機能一覧
--------------
- data (kabusys.data)
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch/save daily_quotes / financials / market_calendar / listed info）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS → raw_news 保存、SSRF/サイズ対策、URL 正規化）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- research (kabusys.research)
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン算出（calc_forward_returns）
  - IC 計算・ランク・統計サマリー（calc_ic / rank / factor_summary）
- ai (kabusys.ai)
  - ニュース NLP スコアリング（score_news）
  - 市場レジーム判定（score_regime）
  - OpenAI 呼び出しは retry / JSON mode に対応
- config (kabusys.config)
  - .env 自動ロード（プロジェクトルート基準）
  - settings オブジェクト経由で各種環境変数にアクセス
- audit (監査ログ) 初期化（data.audit モジュール）

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の | を使用）
- OS による差異はあるが Unix 系を想定した手順例

1) 仮想環境作成（推奨）
- python -m venv .venv
- source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2) 依存パッケージ（例）
必須（本リポジトリ内で利用されている主要パッケージ）:
- duckdb
- openai
- defusedxml

例: pip でインストール
- pip install duckdb openai defusedxml

（プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）
開発インストール（パッケージとして利用する場合）:
- pip install -e .

3) 環境変数 / .env
ルートに .env または .env.local を置けば自動読み込みされます（kabusys.config によりプロジェクトルート判定）。
必須の環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
- OPENAI_API_KEY=<your_openai_api_key>  # score_news / regime で使用
- KABU_API_PASSWORD=<kabu_station_api_password>  # 発注系で使用（本コードベースには発注実装の断片も想定）
- SLACK_BOT_TOKEN=<slack_bot_token>
- SLACK_CHANNEL_ID=<slack_channel_id>

オプション:
- DUCKDB_PATH=data/kabusys.duckdb  (デフォルト)
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
- LOG_LEVEL=INFO|DEBUG|...
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1  (自動 .env 読み込みを無効化)

.env の例（.env.example を作る場合のテンプレート）
- JQUANTS_REFRESH_TOKEN=your_refresh_token_here
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

使い方（コード例）
------------------

共通: settings の利用
- from kabusys.config import settings
- settings.duckdb_path / settings.jquants_refresh_token などでアクセス可能

1) DuckDB に接続して日次 ETL を実行する
- from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

2) ニュースの NLP スコアリング（score_news）
- from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → env の OPENAI_API_KEY を使う

戻り値は書き込んだ銘柄数（int）。失敗や記事なしの場合は 0 を返す。

3) 市場レジーム判定（score_regime）
- from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  res = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

4) 監査ログ DB 初期化
- from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリがなければ自動作成

5) J-Quants API を直接叩く（例: ID トークン取得）
- from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用

注意点 / 挙動
----------------
- API 呼び出しはリトライ・バックオフ・レートリミット制御が組み込まれているが、APIキー・トークンの管理は充分に注意してください。
- ETL は差分処理を行い、既存データは上書き（冪等）されます。バックテスト等での look-ahead を避けるため、target_date を明示してください。
- OpenAI との通信でのエラーやレスポンスパースエラーはフェイルセーフとして 0 や中立値にフォールバックする実装箇所があります（ログ出力はされます）。
- news_collector は RSS の URL 正規化・SSRF 検査・サイズ制限等の安全対策を実装しています。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                         -- 環境変数 / settings
- ai/
  - __init__.py
  - news_nlp.py                     -- ニュース NLP スコアリング
  - regime_detector.py              -- 市場レジーム判定
- data/
  - __init__.py
  - pipeline.py                      -- ETL パイプラインのエントリ
  - etl.py (re-export)               -- ETLResult の公開など
  - jquants_client.py               -- J-Quants API クライアント & 保存処理
  - news_collector.py               -- RSS 収集 + 前処理 + DB 保存
  - calendar_management.py          -- 市場カレンダー管理
  - quality.py                      -- データ品質チェック
  - stats.py                        -- zscore_normalize 等
  - audit.py                        -- 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py              -- モメンタム / バリュー / ボラティリティ
  - feature_exploration.py          -- 将来リターン / IC / summary / rank
- research/（その他ファイル）
- ai/（上記）
- その他: strategy/ execution/ monitoring/ などはパッケージ API に列挙されていますが、今回の抜粋コードには一部実装のみ含まれます。

ロギング / デバッグ
-------------------
- settings.log_level を使ってログレベルを制御できます（環境変数 LOG_LEVEL）。
- DuckDB の接続ログや OpenAI / J-Quants 呼び出しのログを有効にすると詳細な動作確認ができます。

テスト / 開発
-------------
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト実行時に便利です）。
- OpenAI / J-Quants 呼び出しはユニットテストでモックしやすいように内部関数が分割されています（例えば _call_openai_api を patch）。

ライセンス / 貢献
-----------------
- 本 README 内ではライセンス情報は含めていません。実運用・公開時は適切な LICENSE ファイルをリポジトリルートに追加してください。
- バグ修正・機能追加は PR を歓迎します。API 互換性に注意して設計してください。

補足（よくある利用例）
---------------------
- 日次バッチ（cron）: 毎朝 ETL 実行 → news スコアリング → reserch / factor 計算 → シグナル生成 → 発注（発注モジュールと連携）
- 監査: init_audit_db で専用 DB を作成し、発注/約定のトレーサビリティを確保
- 研究用途: research モジュールでファクター生成 → zscore 正規化 → IC 計測

必要に応じて README に含める具体的なコマンド例や .env.example を追加できます。必要があればテンプレートを作成しますので教えてください。