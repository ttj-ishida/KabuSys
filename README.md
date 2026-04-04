KabuSys
=======

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集と
LLM を用いたニュース NLP、ファクター計算、監査ログ（発注フローのトレース）など、
運用・研究両面で必要なユーティリティ群を提供します。

要点
- 言語: Python
- 主な依存: duckdb, openai, defusedxml（他に標準ライブラリを多用）
- パッケージ構成: src/kabusys 以下にモジュール群（data, ai, research, config, ...）

機能一覧
--------
- 環境設定管理
  - .env / .env.local / OS 環境変数から設定を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - settings オブジェクト経由で設定項目にアクセス
- データ ETL（J-Quants）
  - 株価日足（raw_prices）の差分取得 / 保存（ページネーション・レート制御・リトライ）
  - 財務データ（raw_financials）の差分取得 / 保存
  - JPX 市場カレンダー取得 / 保存
  - 日次パイプライン run_daily_etl による一括処理
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合の検出（quality モジュール）
- ニュース収集
  - RSS からのニュース取得、前処理、raw_news への冪等保存
  - SSRF 対策、受信サイズ制限、トラッキングパラメータ除去など
- ニュース NLP（OpenAI）
  - 銘柄ごとのセンチメントスコアを ai_scores へ書き込む（score_news）
  - 市場マクロセンチメントと ETF 200 日 MA を合成して市場レジーム判定（score_regime）
  - API 呼び出しはリトライ・バックオフ・フェイルセーフが実装済み
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクターサマリ
  - zscore_normalize 等の統計ユーティリティ
- 監査ログ（audit）
  - シグナル → 発注要求 → 約定までを追跡するテーブル定義と初期化関数
  - init_audit_db で専用 DuckDB を初期化可能

セットアップ手順
----------------

1. リポジトリをクローン（あるいはパッケージを配置）  
   （本 README は src/ 配下にパッケージがある前提です）

2. 仮想環境を作成して有効化（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - その他、プロジェクトで要求するパッケージがあれば適宜追加してください。

   （プロジェクトに requirements.txt や pyproject.toml がある場合はそちらを参照してインストールしてください）

4. 環境変数の設定
   - .env（および .env.local）をプロジェクトルートに置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロードを無効化できます）。
   - 主な環境変数（必須 / 任意）:

     必須:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 実行に必要）
     - KABU_API_PASSWORD     : kabu ステーション API を使う場合のパスワード（発注等で必要）

     任意（デフォルトあり）:
     - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - OPENAI_API_KEY        : OpenAI 呼び出しを行う場合（関数呼び出し時に api_key 引数で上書き可）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : LINE 通知を使う場合
     - DUCKDB_PATH           : DuckDB パス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH           : SQLite（監視用）パス（デフォルト data/monitoring.db）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, ...（監視関連）

   - .env の書式は quotes や export プレフィックス等、柔軟にパースされます（config モジュール参照）。

5. データベース初期化（監査ログ等）
   - 監査ログ用 DB を初期化する例:
     - python
       from kabusys.data.audit import init_audit_db
       conn = init_audit_db("data/audit.duckdb")
   - ETL で用いる DuckDB のパスは settings.duckdb_path で参照できます。

使い方（基本例）
----------------

※ 以下は最小限の呼び出し例です。実運用では例外処理・ログ管理を行ってください。

1. DuckDB へ接続して日次 ETL を実行する
   - Python REPL / スクリプト例:
     from datetime import date
     import duckdb
     from kabusys.config import settings
     from kabusys.data.pipeline import run_daily_etl

     conn = duckdb.connect(str(settings.duckdb_path))
     result = run_daily_etl(conn, target_date=date.today())
     print(result.to_dict())

   - run_daily_etl はカレンダー / 株価 / 財務の差分取得と品質チェックを順に実行します。

2. ニューススコアリング（OpenAI）を実行する
   - OpenAI API キーを環境変数 OPENAI_API_KEY にセットするか、api_key 引数で渡します。
     from datetime import date
     import duckdb
     from kabusys.config import settings
     from kabusys.ai.news_nlp import score_news

     conn = duckdb.connect(str(settings.duckdb_path))
     written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数を使用
     print(f"written: {written}")

3. 市場レジーム判定
     from datetime import date
     import duckdb
     from kabusys.ai.regime_detector import score_regime

     conn = duckdb.connect(str(settings.duckdb_path))
     score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

   - score_regime は ETF (1321) の MA200 とニュースマクロセンチメントを合成して market_regime テーブルへ書き込みます。

4. 監査ログ初期化
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

5. 研究用ファクター計算
     from datetime import date
     import duckdb
     from kabusys.research import calc_momentum, calc_value, calc_volatility

     conn = duckdb.connect("data/kabusys.duckdb")
     res = calc_momentum(conn, date(2026,3,20))
     # res: list of dict (date, code, mom_1m, mom_3m, mom_6m, ma200_dev)

設計上の注意
------------
- ルックアヘッドバイアス回避のため、モジュールは基本的に datetime.today() / date.today() を内部で参照せず、target_date を引数で受け取る実装が多くあります。バックテスト等では target_date を明示的に与えてください。
- OpenAI 呼び出しは各関数でリトライ・バックオフ・フェイルセーフを実装しています。API レスポンスの不整合時はスコアを 0 にフォールバックする仕様の箇所があります。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に行われます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、実装側は空リストチェックを行っています（互換性対策）。

主要モジュール・ディレクトリ構成
------------------------------

src/kabusys
- __init__.py
- config.py
  - settings: 環境変数とアプリ設定の集中管理（J-Quants トークン、OpenAI、DB パス等）
- ai/
  - __init__.py
  - news_nlp.py         : ニュースの LLM ベースセンチメント分析（score_news）
  - regime_detector.py  : マクロセンチメントと ETF MA を合成した市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py   : J-Quants API クライアント（取得・保存ロジック、レート制御）
  - pipeline.py         : ETL パイプライン（run_daily_etl 等）
  - etl.py              : ETL 結果クラス再エクスポート
  - calendar_management.py : マーケットカレンダー管理（is_trading_day 等）
  - news_collector.py   : RSS 取得と raw_news 保存
  - stats.py            : 統計ユーティリティ（zscore_normalize）
  - quality.py          : データ品質チェック
  - audit.py            : 監査ログ（テーブル DDL・初期化関数）
- research/
  - __init__.py
  - factor_research.py  : モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py : 将来リターン・IC・統計サマリ等
- research/*（その他ユーティリティ）

ライセンス・貢献
----------------
- この README ではライセンスを明示していません。実際のリポジトリに LICENSE ファイルがある場合はそちらに従ってください。
- バグ報告・改善提案は Issue を立て、可能であれば簡単な再現例やログを添えてください。

最後に
------
この README はコードベース（src/kabusys）を参照して作成しています。実運用前に設定（.env）・テスト環境での動作確認・API キーやネットワーク周りのセキュリティ設定を必ず行ってください。必要であれば README をプロジェクトのポリシーや CI/CD 手順に合わせて追記してください。