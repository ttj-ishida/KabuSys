KabuSys
=======

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリ群です。  
主に以下を提供します。

- J-Quants API からのデータ取得（株価日足 / 財務 / 上場情報 / 市場カレンダー）
- DuckDB 上の ETL パイプライン（差分取得・保存・品質チェック）
- ニュース収集・NLP（OpenAI を利用したセンチメントスコアリング）
- 市場レジーム判定（ETF の MA とマクロニュースの LLM スコアを合成）
- ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ等）
- 監査ログ用スキーマ（シグナル → 注文 → 約定のトレーサビリティ）
- カレンダー管理（営業日判定 / 次営業日取得 等）

本パッケージは、バックテストや運用用 ETL、研究用途向けのユーティリティ群として設計されています。  
Look-ahead バイアス防止や API レート制御、冪等性（ON CONFLICT）等の実装方針が反映されています。

主な機能一覧
-------------
- データ取得 / ETL
  - J-Quants クライアント（fetch/save、ページネーション、認証リフレッシュ、レート制限）
  - run_daily_etl / 個別 ETL ジョブ（prices, financials, calendar）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース関連（news_collector, news_nlp）
  - RSS からのニュース収集（SSRF 対策、トラッキング除去、前処理）
  - OpenAI を用いた銘柄ごとのニュースセンチメント（score_news）
- AI 系（regime_detector）
  - ETF（1321）200日移動平均乖離とマクロニュースの LLM スコアを合成して市場レジーム判定（score_regime）
- Research（factor_research, feature_exploration）
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算・IC（Information Coefficient）算出・統計サマリー
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（init_audit_db）
- カレンダー管理（calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要ライブラリをインストール
   - requirements.txt が無い場合、最低限次のパッケージが必要です：
     - duckdb
     - openai
     - defusedxml
     - そのほか標準ライブラリ以外の依存があれば適宜追加してください
   - 例:
     - pip install duckdb openai defusedxml

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（CWD に依存せず __file__ を起点にプロジェクトルートを探索）。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須 / 推奨の環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等 AI 機能で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

.example .env（参考）
- JQUANTS_REFRESH_TOKEN=your_refresh_token
- OPENAI_API_KEY=sk-...
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb

使い方（代表的な例）
-------------------

基本的に DuckDB 接続を作成して各 API を呼び出します。設定は kabusys.config.settings から参照できます。

1) DuckDB 接続を作る
- 例:
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL を実行する
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn)
- result は ETLResult オブジェクト。to_dict() で詳細取得可能。

3) ニューススコアリング（OpenAI 必須）
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- n_written = score_news(conn, target_date=date(2026,3,20))
- 引数 api_key を渡すことで環境変数を使わずに実行可能。

4) 市場レジーム判定（OpenAI 必須）
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=date(2026,3,20))

5) ファクター計算 / 研究系
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
- moments = calc_momentum(conn, target_date=date(2026,3,20))

6) 監査 DB 初期化
- from kabusys.data.audit import init_audit_db
- audit_conn = init_audit_db(settings.duckdb_path)  # または別ファイルパス
- これにより signal_events, order_requests, executions テーブルが作成されます。

7) カレンダー/営業日ユーティリティ
- from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
- is_trading_day(conn, date(2026,3,20))

注意事項
- AI 関連機能（score_news, score_regime）は OpenAI API キーが必要です。api_key 引数で明示的に渡すか、OPENAI_API_KEY 環境変数を設定してください。
- J-Quants API 利用には JQUANTS_REFRESH_TOKEN が必須です。
- ETL / API 呼び出しはネットワーク/外部サービスに依存します。実行環境のネットワーク・認証設定を事前に確認してください。
- DuckDB の executemany に空リストを渡すと問題となるバージョンがあるため、内部で空チェックを行っています。スキーマや DuckDB バージョンに応じて注意してください。

ディレクトリ構成（主要ファイル）
----------------------------

src/kabusys/
- __init__.py — パッケージ定義（公開サブモジュール指定）
- config.py — 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py — ニュースを LLM で評価して ai_scores に書き込む（score_news）
  - regime_detector.py — ETF MA とマクロニュースを合成して市場レジームを判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save 関数、認証、レートリミット）
  - pipeline.py — ETL パイプライン（run_daily_etl 他）
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 取得・前処理・raw_news への保存
  - calendar_management.py — 市場カレンダー管理 / 営業日判定
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — 汎用統計（zscore_normalize）
  - audit.py — 監査ログスキーマ定義・初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py — モメンタム・ボラティリティ・バリュー等の計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー等

開発者向けメモ
---------------
- .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。テストなどで自動読み込みを抑制する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは各モジュールで独立実装されており、テスト時は内部の _call_openai_api を patch して差し替え可能です。
- J-Quants クライアントは固定間隔スロットリングでレート制限を守ります（120 req/min）。
- DuckDB に対するスキーマ変更・DDL の適用は audit.init_audit_schema 等の関数で行ってください。

ライセンス / 貢献
-----------------
- 本 README にライセンス情報は含めていません。リポジトリの LICENSE を参照してください。
- バグ報告や機能改善は Issue を作成してください。

以上がこのコードベースの概要・セットアップ・基本的な使い方とファイル構成です。必要であれば、具体的なコマンド例（requirements.txt の推奨内容、サンプル .env.example ファイル、スクリプト化された実行例）を追記します。どの部分を詳述しましょうか？