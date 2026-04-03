KabuSys
=======

概要
----
KabuSys は日本株のデータ収集・品質管理・ファクター計算・AI によるニュースセンチメント評価・市場レジーム判定・監査ログを含む自動売買／リサーチ基盤のコアライブラリです。  
DuckDB をデータストアに用い、J-Quants API からのデータ取得、RSS ニュース収集、OpenAI（gpt-4o-mini）を用いたニュース NLP、研究用ファクター計算等の機能を提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（date.now 等を無闇に参照しない実装）
- DuckDB を用いたローカルデータレイク設計（冪等保存・トランザクション管理）
- 外部 API 呼び出しに対するリトライ・レート制御・フォールトトレランス
- テストしやすいように API 呼び出し等を差し替え可能に設計

機能一覧
-------
- データ取得・ETL
  - J-Quants から日足（OHLCV）、財務データ、JPX カレンダーを差分取得（ページネーション対応）
  - ETL 実行結果を ETLResult で集約（品質チェック含む）
- データ品質チェック
  - 欠損、重複、スパイク、日付整合性チェック
- ニュース収集
  - RSS 取得・前処理・raw_news テーブルへの冪等保存、銘柄紐付け
  - SSRF 対策、XML インジェクション対策（defusedxml 使用）
- ニュース NLP（AI）
  - 銘柄ごとのニュースセンチメントを OpenAI（gpt-4o-mini）で評価し ai_scores へ書き込み（score_news）
  - マクロ経済ニュースを用いた市場レジーム判定（score_regime）
  - API コールに対するリトライ・レスポンス検証・フェイルセーフ設計
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials ベース）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、Z スコア正規化
- 監査（Audit）
  - signal_events / order_requests / executions 等の監査テーブル作成・初期化（init_audit_schema / init_audit_db）
  - 発注トレースのための UUID ベースのトレーサビリティ設計
- ユーティリティ
  - 環境設定管理（kabusys.config.Settings）
  - .env 自動ロード（プロジェクトルート基準、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）

前提条件
-------
- Python 3.9+
- 必要な Python パッケージ（少なくとも以下）
  - duckdb
  - openai
  - defusedxml

セットアップ手順
--------------
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに pyproject.toml がある場合）pip install -e .
4. 環境変数 / .env ファイルの準備
   - プロジェクトルートに .env（または .env.local）を置くと自動的に読み込まれます（README と同階層に .git または pyproject.toml がある場合）。
   - 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 必要な環境変数（主なもの）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news, score_regime 等で使用）
     - KABU_API_BASE_URL: kabu API ベース URL（省略時 http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
     - DUCKDB_PATH: DuckDB ファイルパス（省略時 data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（省略時 data/monitoring.db）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
     - KABUSYS_ENV: development / paper_trading / live

使い方（簡易サンプル）
-------------------

- DuckDB に接続して日次 ETL を実行する例

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（AI）スコアを生成する例

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
  print(f"wrote {n_written} ai_scores")

- 市場レジーム判定を実行する例

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")

- 監査 DB の初期化（監査専用 DB を作る場合）

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って order_requests 等を操作できます

環境変数と自動ロードの挙動
-------------------------
- ライブラリ起動時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、.env と .env.local を自動的に読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - OS 側に既存のキーがある場合、.env による上書きは行われません（ただし .env.local は override）。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- settings オブジェクトからアプリ設定を参照できます。
  - 例: from kabusys.config import settings; settings.jquants_refresh_token

ディレクトリ構成（概要）
----------------------
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメント（OpenAI 呼び出し、score_news）
    - regime_detector.py         — マクロ + MA200 を使った市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得 / 保存 / レート制御）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETLResult の再エクスポート
    - news_collector.py          — RSS 収集・前処理・raw_news 保存
    - calendar_management.py     — JPX カレンダー管理・営業日判定・更新ジョブ
    - stats.py                   — zscore_normalize 等の統計ユーティリティ
    - quality.py                 — データ品質チェック（複数チェック + run_all_checks）
    - audit.py                   — 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py         — Momentum/Value/Volatility ファクター計算
    - feature_exploration.py     — 将来リターン / IC / 統計サマリー 等
  - ai/、research/ などは商用運用と研究環境での使い分けを想定

注意点 / 運用上のヒント
-----------------------
- OpenAI 呼び出しは API コストとレート制限が発生します。バッチサイズやモデル・温度などはコード内定数で管理しています（news_nlp._BATCH_SIZE 等）。
- J-Quants API 呼び出しにはレート制御とトークン自動リフレッシュ機構があります。JQUANTS_REFRESH_TOKEN を必ず設定してください。
- ETL や AI スコアリングの実行は、定期バッチ（夜間）やワークフロー管理ツール（Airflow 等）から呼ぶことを想定しています。
- DuckDB のファイルは適切にバックアップ・ローテーションしてください。デフォルトファイルパスは DUCKDB_PATH 環境変数で変更可能です。
- テスト用には環境変数 OPENAI_API_KEY をモックやパッチで差し替えたり、kabusys.ai.news_nlp._call_openai_api を unittest.mock.patch で差し替えることが可能です。

ライセンス / 貢献
-----------------
（ここにライセンス情報や貢献方法を記載してください。プロジェクトヘッダやリポジトリの指定に従って追記してください。）

補足
----
README はコードベース（src/kabusys）に基づいた概要ドキュメントです。実運用時は本リポジトリに含まれる DataPlatform.md / StrategyModel.md 等の設計書、.env.example、pyproject.toml を併せて参照してください。