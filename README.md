KabuSys
=======

概要
----
KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。  
主に以下の機能を持ち、データ取得（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ等を提供します。  
コードは DuckDB を主なデータストアとして想定しています。

主な特徴
--------
- J-Quants API 経由での株価・財務・カレンダー取得（ページネーション・認証自動リフレッシュ・レート制御）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）と記事前処理（SSRF 対策、トラッキングパラメタ除去、受信サイズ制限）
- ニュースの LLM（OpenAI gpt-4o-mini）による銘柄別センチメント算出（batch・冪等保存）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）と統計ユーティリティ（Zスコア正規化、IC 計算）
- 監査ログ（signal → order_request → execution のトレーサビリティ）を確保する DuckDB スキーマ初期化ユーティリティ
- 設定は .env または環境変数で管理（自動読み込み機能あり）

対応モジュール（抜粋）
- kabusys.config: 環境変数読み込み／Settings
- kabusys.data: ETL（pipeline）、J-Quants クライアント、ニュース収集、カレンダー管理、品質チェック、監査ログ初期化
- kabusys.ai: news_nlp（ニューススコアリング）、regime_detector（市場レジーム判定）
- kabusys.research: ファクター計算・特徴量探索ユーティリティ
- kabusys.data.stats: 汎用統計ユーティリティ（zscore_normalize）

必要環境
--------
- Python 3.10+
- DuckDB（Python パッケージ: duckdb）
- OpenAI Python SDK（openai）
- defusedxml（XML パースの安全化）
- 標準ライブラリ（urllib 等）

インストール
------------
1. 仮想環境を作成して有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（最低限）
   - pip install duckdb openai defusedxml

   （プロジェクト用に requirements.txt / pyproject.toml がある場合はそちらを使用してください）

3. ソースを editable インストール（任意）
   - pip install -e .

環境変数（主なもの）
--------------------
プロジェクトは .env（および .env.local）または OS 環境変数から設定を読み込みます。自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL     : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector で使用）
- SLACK_BOT_TOKEN       : Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 実行環境 (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL             : ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）

基本的なセットアップ手順
-----------------------
1. .env を作成する（.env.example を参考に必要なキーを記載）
   例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

2. DuckDB 接続ファイル用のディレクトリを作成（自動で作られることもあります）
   - mkdir -p data

3. 監査ログ用 DB を初期化する（任意）
   - Python スクリプト例:
     ```
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

使い方（代表的な API）
---------------------

- Settings（環境設定）の参照
  ```
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path
  ```

- DuckDB 接続を作って日次 ETL を実行
  ```
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアリングを実行（OpenAI API キーは環境変数か引数で指定）
  ```
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print(f"scored {n} symbols")
  ```

- 市場レジーム判定（regime_detector）
  ```
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 監査スキーマ初期化（既存接続に対して）
  ```
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- J-Quants の ID トークン取得（内部で settings.jquants_refresh_token を使用）
  ```
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()
  ```

注意点 / 運用上のポイント
------------------------
- Look-ahead バイアス防止: 多くの処理（news window、regime 判定、ETL 等）は内部で date.today() を不用意に参照しない設計になっています。API 呼び出し時には target_date を明示してください。
- OpenAI 呼び出しは冪等性やリトライが考慮されていますが、モデルレスポンスの検証（JSON パース等）で失敗した場合はフェイルセーフ（0.0 スコア等）にフォールバックする実装です。
- J-Quants API はレート制限（120 req/min）を守る RateLimiter を備えています。大量の連続リクエスト時は十分注意してください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI／テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って無効化できます。
- DuckDB の executemany に関する互換性（空リスト不可）等、実運用での注意（コード中に考慮済み）があります。

ディレクトリ構成 (主要ファイル)
------------------------------
src/kabusys/
- __init__.py
- config.py                         — 環境変数・Settings 管理
- ai/
  - __init__.py
  - news_nlp.py                      — ニュースの LLM スコアリング（batch・検証・書き込み）
  - regime_detector.py               — 市場レジーム判定（MA200 + マクロニュース LLM）
- data/
  - __init__.py
  - jquants_client.py                — J-Quants API クライアント（取得・保存・認証）
  - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
  - etl.py                           — ETLResult の再エクスポート
  - news_collector.py                — RSS 収集・前処理・保存
  - calendar_management.py           — 市場カレンダー管理・営業日判定
  - quality.py                       — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py                         — 統計ユーティリティ（zscore_normalize）
  - audit.py                         — 監査ログ（スキーマ定義と初期化）
- research/
  - __init__.py
  - factor_research.py               — モメンタム / バリュー / ボラティリティ等
  - feature_exploration.py           — 将来リターン / IC / 統計サマリー等

（上記は主要モジュールの抜粋です。詳細は各ファイルの docstring を参照してください。）

開発・貢献
----------
- まずはユニットテストや linters を用いて静的解析・動作確認を行ってください。
- 外部 API の統合部分（J-Quants / OpenAI / RSS）はモック可能なように実装されており、テストでの差し替えを想定しています（例: _call_openai_api のパッチ等）。
- 重大な変更を行う場合は Look-ahead バイアスや DB 書き込みの冪等性、トランザクション管理に留意してください。

補足
----
この README はコードベースの主要機能と利用方法の概要を説明しています。個々の関数やクラスの詳細な引数・返り値・例外挙動は該当ソース（src/kabusys 以下の各ファイル）に記載された docstring を参照してください。質問や追加説明が必要であればお知らせください。