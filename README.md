KabuSys — 日本株自動売買プラットフォーム
======================================

概要
----
KabuSys は日本株のデータプラットフォーム、研究（ファクター計算）、AI によるニュースセンチメント評価、監査ログ、ETL パイプラインを備えた自動売買システムのライブラリ群です。本リポジトリはデータ取得（J-Quants）、ニュース収集、品質チェック、ファクター/リサーチユーティリティ、AI ベースのニュース評価、監査ログ（発注→約定のトレーサビリティ）などを提供します。

主な特徴
--------
- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）と冪等保存
- ニュース収集（RSS）と記事前処理 / 銘柄紐付け
- OpenAI を利用したニュースセンチメント（銘柄別）スコアリング（gpt-4o-mini を想定）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
- ファクター計算（モメンタム / バリュー / ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ用スキーマ（signal_events / order_requests / executions）と初期化ユーティリティ
- DuckDB を中心としたローカル DB 管理、冪等性・トランザクション考慮

セットアップ手順
----------------

1. リポジトリをクローン / ワークディレクトリへ移動
   - 例: git clone ... && cd kabusys

2. Python 仮想環境の作成（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 代表的な依存例:
     - duckdb
     - openai
     - defusedxml
     - そのほか標準ライブラリのみで動作する部分も多いですが、ネットワーク/API を使う機能は上記が必要です。
   - 例:
     pip install duckdb openai defusedxml

4. 環境変数の設定
   - プロジェクトルートに .env（または .env.local）を置くと自動的に読み込まれます（.git または pyproject.toml を探索してプロジェクトルートを決定）。
   - 自動読み込みを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必須環境変数（アプリ設定）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（get_id_token 用）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注連携を行う場合）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知を使う場合
   - OPENAI_API_KEY: OpenAI API を使う AI 機能（score_news / regime_detector）を使う場合
   - 任意 / デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db

   注意: .env のパースはシェル風（export KEY=val、引用やコメントの扱いなど）に対応しています。

使い方（代表的な例）
-------------------

以下は簡単な Python スニペット例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を開いて日次 ETL を実行する（J-Quants ID トークンは設定済みを想定）:

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニューススコアリング（特定日）の実行:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY を環境変数に設定していると api_key は不要
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書込銘柄数: {n_written}")

- 市場レジーム判定（score_regime）:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB の初期化:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで監査用テーブル(signal_events, order_requests, executions) が作成されます

- ファクター計算やリサーチ関数の利用例:

  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))

内部モジュールと責務の概略
------------------------
（主要なモジュールと担当領域）

- kabusys.config
  - 環境変数 / 設定取得、.env 自動読み込み、設定プロパティ（settings）

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レート制御・リトライ）
  - pipeline: ETL 実行（run_daily_etl / run_prices_etl / run_financials_etl 等）
  - calendar_management: 市場カレンダー管理・営業日判定
  - news_collector: RSS 収集・前処理・記事ID生成・SSRF 対策
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合）
  - audit: 監査ログスキーマ定義・初期化ユーティリティ
  - stats: 汎用統計（zscore_normalize）

- kabusys.ai
  - news_nlp: ニュース銘柄別センチメントスコア（OpenAI を使用）
  - regime_detector: マクロセンチメント＋MA200 で市場レジーム判定

- kabusys.research
  - factor_research: momentum/value/volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、統計サマリー

ディレクトリ構成（主要ファイル）
-------------------------------
以下はソースツリー（主要ファイル）の抜粋です:

src/kabusys/
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
  - calendar_management.py
  - news_collector.py
  - quality.py
  - audit.py
  - stats.py
  - pipeline.py
  - etl.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/
  - factor_research.py
  - feature_exploration.py
- research/__init__.py
- data/__init__.py

（実装上はさらに細かな関数やユーティリティが各モジュールに含まれます。上は概観です。）

運用上の注意
------------
- Look-ahead バイアス回避:
  - AI モジュールや ETL は target_date より未来のデータ参照を避ける設計になっています（内部で date.today() を直接参照しないなど）。
- API キー / トークン
  - J-Quants のリフレッシュトークンは settings.jquants_refresh_token（JQUANTS_REFRESH_TOKEN）で管理され、自動で id_token を取得・キャッシュします。
  - OpenAI API キーは OPENAI_API_KEY（環境変数）か score_news/score_regime の api_key 引数で指定可能。未指定の場合は ValueError を投げます。
- .env の自動ロード
  - プロジェクトルートに .env / .env.local を置けば自動ロードされます（OS 環境変数は優先）。特殊な読み込みルール（export 形式、引用の取り扱い、コメント）に対応しています。
  - テスト等で自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB について
  - 保存関数は冪等（ON CONFLICT DO UPDATE）であり、ETL は差分更新・バックフィルをサポートします。
  - executemany に空リストを渡せないバージョンへの互換性を考慮している箇所があります（DuckDB 0.10 など）。

ライセンス / 貢献
-----------------
（この README にはライセンス情報が含まれていません。リポジトリの LICENSE ファイルを参照してください。貢献方法は CONTRIBUTING.md をご確認ください。）

付録: よく使う関数一覧（参照）
--------------------------------
- kabusys.data.pipeline.run_daily_etl(conn, target_date, id_token=None, ...)
- kabusys.data.pipeline.run_prices_etl(...)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(conn, records)
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.data.audit.init_audit_db(path) / init_audit_schema(conn)

最後に
------
この README はコードベース（モジュールの docstring / 実装）に基づいた概要ドキュメントです。各モジュールのより詳しい使い方・設定例は個別モジュールの docstring と実装を参照してください。必要であれば、実行コマンド例や .env.example、requirements.txt の作成を支援します。