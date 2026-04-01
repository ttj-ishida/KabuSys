KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けのデータプラットフォーム／リサーチ／自動売買の基盤ライブラリです。  
主に以下の責務を持ちます。

- J-Quants API を用いた株価・財務・市場カレンダーの ETL と品質チェック
- RSS ニュース収集と銘柄別 NLP（OpenAI）によるセンチメントスコアリング
- 市場レジーム判定（ETF MA とマクロニュースの組み合わせ）
- 研究用ファクター生成・特徴量解析ユーティリティ
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ初期化ユーティリティ

主な機能
--------
- data/
  - jquants_client: J-Quants API とのやりとり（取得・保存・認証・レート制御・リトライ）
  - pipeline / etl: 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
  - news_collector: RSS 取得・前処理・raw_news 保存（SSRF・大容量保護）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management: 市場カレンダー管理・営業日判定
  - audit: 監査ログ（signal/order/execution）スキーマ初期化ユーティリティ
  - stats: 汎用統計ユーティリティ（Zスコア正規化等）
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとにまとめて OpenAI に投げ、ai_scores を作成
  - regime_detector.score_regime: ETF（1321）200日MA乖離とマクロニュース（LLM）を合成して市場レジームを判定
- research/
  - factor_research: Momentum / Volatility / Value などのファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）や統計サマリ

セットアップ手順
----------------

1. Python 環境を用意する（推奨: 3.10+）
   - 仮想環境を作成・有効化して下さい。
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要な外部ライブラリ（最低限）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （実際のプロジェクトでは requirements.txt や poetry / pyproject.toml を使用してください）

3. リポジトリからパッケージをインストール（開発モード）
   - pip install -e .

4. 環境変数を準備する
   - プロジェクトルートに .env / .env.local を置くことで自動読み込みされます（kabusys.config が自動ロード）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必要な主要環境変数（例）
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 用）
     - KABU_API_PASSWORD — kabuステーション API パスワード（使用する場合）
     - SLACK_BOT_TOKEN — Slack 通知用（任意だが設定されている箇所あり）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - DUCKDB_PATH — DuckDB DB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — SQLite（監視用 DB）パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV — development|paper_trading|live（デフォルト development）
     - LOG_LEVEL — DEBUG|INFO|...（デフォルト INFO）

   - 注意: .env のパースはシェル形式（export KEY=val, quoted string, コメント）に対応しています。未設定の必須変数は Settings プロパティで ValueError を投げます。

使い方（簡易例）
----------------

以下は代表的な利用例です。import する際は仮想環境や PYTHONPATH に注意してください。

1) DuckDB 接続を作って日次 ETL を実行する
- Python スクリプト例:
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

  - run_daily_etl は市場カレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック を順に実行し、ETLResult を返します。

2) ニュースセンチメントをスコアリングして ai_scores を書き込む
- Python スクリプト例:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数で読む
  print("書き込み銘柄数:", n_written)

  - score_news は raw_news / news_symbols / ai_scores を使用します。API 呼び出しは gpt-4o-mini（JSON mode）を期待します。

3) 市場レジームを判定して market_regime テーブルに書き込む
- Python スクリプト例:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

  - 内部で ETF 1321 の 200 日 MA 乖離とマクロニュースの LLM スコアを合成します。OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を参照します。

4) 監査ログ（audit）スキーマを初期化する
- Python スクリプト例:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

  - init_audit_db は parent ディレクトリを自動作成し、監査テーブル群とインデックスを transactional に作成します（UTC タイムゾーン固定）。

運用上の注意
------------
- Look-ahead bias を避ける設計:
  - 多くの関数（score_news, score_regime, run_daily_etl 等）は内部で datetime.today() に依存せず、target_date を明示的に受け取ります。バックテスト等では明示日付の注入を行ってください。
- OpenAI / J-Quants の API キーとレート制限に注意:
  - jquants_client には固定間隔スロットリングとリトライが実装されています（120 req/min）。
  - OpenAI 呼び出しはリトライやサーバーエラーハンドリングを行いますが、API キー・料金管理は運用側で注意してください。
- .env の自動読み込み:
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し .env/.env.local を読み込みます。CI やテストで自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（抜粋）
-----------------------
以下は本コードベースで重要なファイルと配置（src/kabusys 配下の代表例）です。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - quality.py
    - calendar_management.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/（その他ユーティリティ）
  - (strategy, execution, monitoring 等の上位パッケージは __all__ に含まれていますが、ここに含まれるモジュールを拡張して運用します)

主要なクラス / 関数一覧（抜粋）
----------------------------
- Settings (kabusys.config.settings) — 環境変数経由で設定値を取得
- jquants_client.get_id_token / fetch_daily_quotes / save_daily_quotes 等 — J-Quants 連携
- pipeline.run_daily_etl — 日次 ETL のメインエントリポイント
- news_nlp.score_news — ニュースセンチメントの一括スコア化（ai_scores へ保存）
- regime_detector.score_regime — 市場レジーム判定・market_regime への書込
- research.factor_research.calc_momentum / calc_volatility / calc_value — ファクター計算
- research.feature_exploration.calc_forward_returns / calc_ic / factor_summary — 研究用解析
- data.audit.init_audit_db / init_audit_schema — 監査ログ DB 初期化

補足 / トラブルシュート
-----------------------
- DuckDB のテーブルスキーマは本 README に含めていません。ETL を実行するには事前に必要なテーブル（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime, ...）を用意する必要があります。audit 用テーブルは data.audit.init_audit_db で初期化できます。
- OpenAI 呼び出しや外部 API 呼び出しはネットワーク環境に依存します。テスト時は各モジュールの _call_openai_api / _urlopen などをモックして下さい（コード中にテスト差し替えを想定したコメントがあります）。
- .env のパースは shell ライクですが完全なシェル互換ではありません。特殊なフォーマットの値はクォートとエスケープに注意してください。

最後に
------
この README はコードベースの主要部分を要約したものです。各モジュールの docstring に詳しい設計方針・挙動・例外処理方針が記載されていますので、実装や拡張を行う際は該当ファイルのコメントを参照してください。必要ならば README に運用例（systemd / cron / Docker コンテナ化・監視）や DB スキーマ定義を追加します。