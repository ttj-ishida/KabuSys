KabuSys — 日本株データプラットフォーム & 自動売買基盤
=================================================

概要
----
KabuSys は日本株向けのデータプラットフォーム兼自動売買基盤のコアライブラリです。本リポジトリは ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を用いたニュースセンチメント）、市場レジーム判定、ファクター計算・リサーチ、監査ログ／発注トレーサビリティなど、トレードシステムのバックエンド機能群を提供します。

主な設計方針
- Look-ahead バイアス回避（内部で date.today() を直接参照しない API 設計）
- DuckDB を中心としたローカルデータストア（ETL／品質チェック／監査ログ）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント・レジーム判定（フォールバック付）
- 冪等設計（DB 書き込みは ON CONFLICT/DELETE→INSERT 等で安全化）
- ネットワーク操作に対する堅牢な対策（レートリミット、リトライ、SSRF 対策、レスポンスサイズ制限）

機能一覧
--------
- データ ETL（J-Quants API 経由）
  - 日次株価（raw_prices）、財務データ（raw_financials）、JPX カレンダー（market_calendar）
  - 差分取得 / バックフィル / 品質チェック（欠損・スパイク・重複・日付整合性）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
- ニュース収集・前処理（RSS）
  - RSS フィード取得、URL 正規化、トラッキングパラメータ除去、記事ID生成（SHA-256）
  - SSRF 対策、gzip サイズ制限（kabusys.data.news_collector）
- ニュース NLP（OpenAI）
  - 銘柄単位に記事を集約して gpt-4o-mini に JSON モードで投げ、スコアを ai_scores に保存（kabusys.ai.news_nlp.score_news）
- 市場レジーム判定（AI + テクニカル）
  - ETF(1321) の 200 日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成して 'bull'/'neutral'/'bear' を算出（kabusys.ai.regime_detector.score_regime）
- リサーチ / ファクター計算
  - モメンタム / ボラティリティ / バリュー 等のファクター計算、将来リターン、IC（kabusys.research）
- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions 等の監査テーブル初期化・管理（kabusys.data.audit）
- 設定管理
  - 環境変数・.env 自動読み込み、Settings クラス経由の型安全なアクセス（kabusys.config）

セットアップ手順
----------------

1. Python 環境（推奨: 3.10+）を用意する
   - 仮想環境の作成例:
     python -m venv .venv
     source .venv/bin/activate

2. 必要パッケージをインストールする（例）
   pip install duckdb openai defusedxml

   ※ 実環境では他の依存（logging 等標準ライブラリ以外）やバージョン固定を requirements.txt / pyproject.toml で管理してください。

3. パッケージをインストール（開発モード）
   pip install -e .

4. 環境変数設定
   - プロジェクトルートに .env（および必要なら .env.local）を置くと自動で読み込まれます（kabusys.config が .git または pyproject.toml を探索して自動ロード）。
   - 自動ロードを無効化したい場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   代表的な環境変数（README 用サンプル .env）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx

   # OpenAI（AI 機能を使う場合）
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx

   # kabuステーション API（注文送信をする場合）
   KABU_API_PASSWORD=your_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack（通知）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C1234567890

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development  # development|paper_trading|live
   LOG_LEVEL=INFO
   ```

使い方（代表的な API / ワークフロー）
-----------------------------------

- DuckDB 接続準備
  ```
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（株価・財務・カレンダーの差分取得 + 品質チェック）
  ```
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（AI）計算（score_news）
  ```
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定（score_regime）
  ```
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化（監査専用 DB を分ける場合）
  ```
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算 / リサーチ
  ```
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  vol = calc_volatility(conn, date0)
  val = calc_value(conn, date0)
  normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

主要モジュールと API（抜粋）
- kabusys.config
  - settings: Settings インスタンス（JQUANTS_REFRESH_TOKEN / OPENAI API KEY などを参照）
  - 自動 .env 読み込み: .env, .env.local（優先度: OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可。

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...): 日次 ETL（戻り値: ETLResult）
  - run_prices_etl / run_financials_etl / run_calendar_etl

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token(refresh_token=None)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30) 等（RSS 取得と前処理）

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)

- kabusys.research
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

ディレクトリ構成
----------------
（主要ファイルと概要）

- src/kabusys/
  - __init__.py                — パッケージ定義（__version__）
  - config.py                  — 環境変数 / .env 管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースセンチメント（score_news）
    - regime_detector.py       — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py        — J-Quants API クライアント（fetch/save）
    - news_collector.py        — RSS 収集（SSRF 対策・前処理）
    - calendar_management.py   — マーケットカレンダー管理（営業日判定）
    - stats.py                 — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py               — データ品質チェック
    - audit.py                 — 監査ログスキーマ初期化・監査 DB ヘルパ
    - etl.py                   — ETLResult の再公開
  - research/
    - __init__.py
    - factor_research.py       — Momentum/Value/Volatility 等の計算
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー 等
  - research/*、ai/*、data/* の各種ユーティリティや設計ノートが含まれます。

運用上の注意
------------
- OpenAI API 使用時はコストとレート制限に注意してください。AI 呼び出しに失敗した場合はフェイルセーフ（スコア=0 等）で継続する設計になっていますが、API キーの管理は慎重に行ってください。
- J-Quants API のレート制限（120 req/min）・認証フローを尊重してください（jquants_client は固定間隔レートリミッタと 401 自動リフレッシュを実装）。
- DuckDB のバージョン差異により executemany で空リストを渡せない制約があるため、呼び出し側コードは空チェックを行っています。ETL を拡張する場合も留意してください。
- 本ライブラリはバックテストの内部ループから直接外部 API を呼び出さない設計を推奨します（Look-ahead バイアス防止）。

ライセンス・寄稿
----------------
本 README ではライセンスファイルを含めていません。実際の配布リポジトリでは LICENSE を追加してください。貢献される場合は Issue / Pull Request を通じてご提案ください。

補足（質問・カスタマイズ）
------------------------
具体的な実行シナリオ（例: ETL のスケジューリング、kabu ステーション経由の発注実装、Slack 通知フローの追加等）や、実際に動かすための .env.example ファイルの自動生成など、必要であれば README を拡張して運用手順・デプロイ手順・監視設計を追記します。どの内容を優先して詳しくしたいか教えてください。