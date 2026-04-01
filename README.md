KabuSys
=======

KabuSys は日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
DuckDB ベースのデータレイク、J-Quants からの ETL、ニュース収集と LLM によるニュースセンチメント評価、ファクター計算、監査（トレーサビリティ）スキーマなどを提供します。

主な目的
- 株価・財務・市場カレンダーの差分 ETL（J-Quants API）
- RSS ニュース収集・前処理と銘柄紐付け
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント／市場レジーム判定
- ファクター（モメンタム / バリュー / ボラティリティ等）と研究用ユーティリティ
- 監査ログ（signal → order_request → execution の追跡を可能にするテーブル群）
- データ品質チェック・カレンダー管理などの運用ユーティリティ

機能一覧
--------
- data.jquants_client
  - J-Quants API から株価（OHLCV）、財務、カレンダーを取得／保存（ページネーション・リトライ・レート制限対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- data.pipeline / etl
  - 日次 ETL パイプライン（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新・バックフィル対応
- data.news_collector
  - RSS フィード取得、URL 正規化、前処理、記事 ID 作成、raw_news への冪等保存
  - SSRF 対策・受信サイズ制限・XML セキュリティ対策（defusedxml）
- ai.news_nlp / ai.regime_detector
  - 銘柄別ニュースをまとめて LLM に送りセンチメント（ai_scores）を計算
  - ETF（1321）200 日 MA とマクロニュースセンチメントを合成して市場レジームを判定
  - OpenAI SDK を用いた JSON-mode 呼び出し、リトライ・フォールバック設計
- research.*
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- data.quality
  - 欠損・スパイク・重複・日付不整合チェック（QualityIssue オブジェクトで報告）
- data.audit
  - 監査ログ用のテーブル定義・初期化（signal_events, order_requests, executions）
  - init_audit_db で DuckDB を初期化可能
- data.calendar_management
  - market_calendar を参照した営業日判定 / next/prev_trading_day / get_trading_days
  - JPX カレンダーの夜間更新ジョブ（calendar_update_job）

セットアップ手順
--------------
前提
- Python 3.10 以上（PEP 604 の | 型ヒント等を使用しているため）
- ネットワーク経由で J-Quants / OpenAI を利用するための API キー

1. リポジトリを取得
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   （プロジェクトに requirements.txt がない場合は主要依存を個別に）
   ```
   pip install duckdb openai defusedxml
   ```
   - 実運用では slack SDK（slack_sdk）やその他ツールを追加することがあるかもしれません。

4. 環境変数設定
   - プロジェクトはルートの .env / .env.local（または OS 環境変数）を自動で読み込みます。
     自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   - 必須（本コードで参照される主要な環境変数）
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
     - KABU_API_PASSWORD      : kabu API 用パスワード（kabu が使われる場合）
     - SLACK_BOT_TOKEN        : Slack 通知に使う場合
     - SLACK_CHANNEL_ID       : Slack チャンネル ID
     - OPENAI_API_KEY         : OpenAI API キー（ai.news_nlp / ai.regime_detector）
   - 任意 / デフォルト有り
     - KABUSYS_ENV (development | paper_trading | live) 既定: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ...)
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (例: data/monitoring.db)
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. DB 初期化（監査ログなど）
   Python で監査 DB を作成する例:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成されます
   ```

使い方（例）
------------
以下は主要なユースケースの簡単な Python サンプルです。CWD に依存せず settings が .env を自動ロードします（プロジェクトルートの判定に .git / pyproject.toml を利用）。

- 日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースセンチメントを計算して ai_scores に書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
  print(f"wrote {written} ai scores")
  ```

- 市場レジームを判定する
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))  # market_regime テーブルへ書き込む
  ```

- 監査スキーマを既存 DB に追加
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

注意点 / 設計上のポイント
- Look-ahead bias を避ける設計:
  - 多くの関数は datetime.today() / date.today() を内部で参照しない（外部から日付を渡す設計）。
  - ETL・AI モジュールは target_date に基づいて過去データのみを参照します。
- LLM 呼び出しは JSON mode を使い、パースエラーや API 失敗時にはフォールバック（0.0 等）するよう設計されています。
- J-Quants API クライアントはレート制限（120 req/min）とリトライ、401 のトークン自動更新に対応しています。
- RSS の取得では SSRF / XML 攻撃対策（スキーム検証、ホスト判定、defusedxml、受信サイズ制限）を実装しています。

ディレクトリ構成
----------------
以下は主要なファイル・モジュールの概要（src/kabusys 以下）です。

- kabusys/
  - __init__.py          : パッケージ情報（__version__ 等）
  - config.py            : 環境変数 / 設定読み込みロジック（.env 自動ロード等）
  - ai/
    - __init__.py
    - news_nlp.py        : ニュースセンチメント（OpenAI 経由）と ai_scores 書込ロジック
    - regime_detector.py : マクロニュース + ETF ma200 を合成して market_regime を判定
  - data/
    - __init__.py
    - jquants_client.py  : J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py        : ETL パイプライン（run_daily_etl 等）
    - etl.py             : ETLResult の再公開
    - news_collector.py  : RSS 収集・前処理
    - quality.py         : データ品質チェック（QualityIssue）
    - stats.py           : 汎用統計ユーティリティ（zscore_normalize 等）
    - calendar_management.py : 市場カレンダー管理・営業日判定
    - audit.py           : 監査ログ（テーブル DDL / init 関数）
  - research/
    - __init__.py
    - factor_research.py : ファクター計算（momentum/value/volatility）
    - feature_exploration.py : 特徴量解析（forward returns / IC / stats）
  - ai, strategy, execution, monitoring 等のサブパッケージ（コードベースに応じて追加）

開発・運用のヒント
------------------
- テスト時に .env の自動読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI の呼び出し部分は _call_openai_api をパッチしてモック可能です（ユニットテスト向け）。
- DuckDB の executemany は空リストを受け付けないバージョンの対応がコード内にあるため、空パラメータ送信に注意してください。
- 監査ログは削除しない前提で設計されています（ON DELETE RESTRICT）。運用での永続化方針を確立してください。

ライセンス・貢献
----------------
（このリポジトリにライセンス情報がある場合はここに記載してください）

お問い合わせ
-----------
不具合報告や提案はリポジトリの Issue に記載してください。主要な外部サービスの API キー（J-Quants, OpenAI 等）は取り扱いに注意してください（秘密情報は公開しない）。

以上が KabuSys の概要と基本的な使い方です。必要であればサンプルの .env.example、requirements.txt、簡易 CLI スクリプトなどのテンプレートを追加する README 版を用意します。どの部分を詳しく追記しますか？