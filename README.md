KabuSys — 日本株向けデータプラットフォーム & 自動売買支援ライブラリ
=================================================================

概要
----
KabuSys は日本株のデータ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI を用いたセンチメント評価）、市場レジーム判定、監査ログ（発注→約定のトレーサビリティ）などを統合した Python モジュール群です。  
設計上の特徴として、ルックアヘッドバイアス回避、冪等性（DB 保存時の ON CONFLICT 処理）、堅牢な API リトライ・レートリミット、SSRF 対策など運用を意識した実装を備えます。

主な機能
--------
- J-Quants API クライアント（価格・財務・マーケットカレンダー取得、トークン自動リフレッシュ、ページネーション対応、レート制御）
- ETL パイプライン（差分フェッチ、バックフィル、品質チェック、日次一括実行 run_daily_etl）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- ニュース収集（RSS 取得、前処理、SSRF 対策、raw_news への保存ロジック）
- ニュースNLP（OpenAI を用いた銘柄別センチメント scoring、JSON モード + バッチ処理・リトライ）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースセンチメントの合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化 等）
- 監査ログ（signal_events / order_requests / executions テーブル・初期化ユーティリティ）
- 設定管理（.env 自動ロード、環境変数取得ラッパー）

動作要件（想定）
----------------
- Python 3.10+
- 必要パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

（実際の requirements.txt に合わせて pip install を行ってください）

環境変数 / 設定
----------------
パッケージ起動時にルートプロジェクトの .env/.env.local を自動で読み込みします（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主な環境変数（必須／デフォルト含む）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード（発注等で使用）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — 通知先チャンネル ID
- DUCKDB_PATH — DuckDB のデータファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視設定
- KABUSYS_ENV — 実行環境 (development / paper_trading / live)
- LOG_LEVEL — ログレベル (DEBUG/INFO/...)

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - pip install -r requirements.txt
   または開発・ローカル利用:
   - pip install -e .

   （requirements.txt がない場合は上の「動作要件」にある主要パッケージを個別にインストールしてください）

4. .env を作成
   - ルートに .env を作成し、必要な環境変数を設定します。
   例:
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb

   - 自動読み込みを無効化したいテストなどでは:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

基本的な使い方（抜粋）
--------------------

- DuckDB 接続を作る（多くの関数が DuckDB 接続を受け取る）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェックを一括で実行）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出して ai_scores テーブルへ書き込む
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を利用
  print("written:", written)
  ```

- 市場レジーム判定（ma200 + マクロセンチメント）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用スキーマ初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意点 / デザインノート
-----------------------
- ルックアヘッドバイアス回避: 多くの関数は内部で date.today() 等を直接参照せず、target_date を明示して扱います。バックテスト等での安全な利用を意図しています。
- 冪等性: ETL や save_* 関数は DB 側で ON CONFLICT を使って上書きするため、再実行しても重複しません。
- OpenAI 呼び出し: API の失敗時はフェイルセーフとして一部処理をスキップ（0.0 を返す等）し、例外により全体が停止しないように設計されています。
- セキュリティ: RSS 取得では SSRF 対策（プライベート IP 拒否・リダイレクト検査）を実装しています。

ディレクトリ構成（主なファイル）
-------------------------------
以下は src/kabusys 配下の主要モジュールを要約した構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数 / .env 自動ロード / settings
  - ai/
    - __init__.py
    - news_nlp.py                  -- ニュースセンチメント（OpenAI）
    - regime_detector.py           -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API client & save_* 関数
    - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
    - etl.py                       -- ETLResult 再エクスポート
    - news_collector.py            -- RSS 収集・前処理
    - calendar_management.py       -- 市場カレンダー管理 / 営業日判定
    - quality.py                   -- データ品質チェック
    - stats.py                     -- zscore_normalize 等共通統計関数
    - audit.py                     -- 監査ログテーブル初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py           -- Momentum / Volatility / Value 等
    - feature_exploration.py       -- 将来リターン / IC / 統計サマリー
  - ai、data、research 以外にも strategy / execution / monitoring 等の公開を想定

例: もっと詳細な tree（抜粋）
- src/
  - kabusys/
    - ai/
      - news_nlp.py
      - regime_detector.py
    - data/
      - jquants_client.py
      - pipeline.py
      - news_collector.py
      - quality.py
      - audit.py
      - calendar_management.py
      - stats.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - config.py
    - __init__.py

よくある質問（FAQ）
------------------
Q: OpenAI API キーはどこで指定しますか？  
A: api_key 引数に渡すか、環境変数 OPENAI_API_KEY を設定してください。

Q: .env は自動で読み込まれますか？  
A: はい。プロジェクトルート（.git または pyproject.toml のある親ディレクトリ）から .env / .env.local を自動読み込みします。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Q: DuckDB の初期スキーマはどう作りますか？  
A: 本 README のスニペットにある init_audit_db / init_audit_schema のような関数を使って必要な監査テーブルを初期化します。ETL 実行前にスキーマ作成ユーティリティが別途提供されている想定です（data.schema.* 等）。

貢献・開発
----------
- コーディング規約・テストはプロジェクト内の CONTRIBUTING.md / pyproject.toml を参照してください（存在する場合）。
- 自動テスト、型チェック、CI の導入を推奨します（DuckDB による統合テストはローカルファイルを利用すること）。

付記
----
この README はソースコードのコメント・ドキュメント文字列に基づいて作成しています。実環境での運用前に .env の整備、API キーの発行、DuckDB ファイルの配置、外部サービス（J-Quants / OpenAI）へのアクセス確認を行ってください。何か追加で README に含めたい具体的な使用例（例: ETL を cron 化する手順、Slack 通知の流れ、kabu API と発注フローの例）などがあれば教えてください。