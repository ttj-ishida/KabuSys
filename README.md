KabuSys
=======

日本株向けのデータプラットフォーム＋自動売買基盤の一部を実装した Python パッケージです。  
本リポジトリは主に以下を提供します：

- J-Quants API を利用したデータ取得・保存（株価/財務/カレンダー）
- ETL パイプライン（差分取得・保存・品質チェック）
- ニュース収集と LLM を用いたニュースセンチメント解析
- 市場レジーム判定ロジック（ETF MA とマクロニュースの LLM スコアを合成）
- 監査ログ（注文→約定トレース）用の DuckDB スキーマ初期化ユーティリティ
- リサーチ用のファクター計算・特徴量解析ユーティリティ

この README はローカル環境でのセットアップ／基本的な使い方をまとめています。

主な機能
--------

- ETL（run_daily_etl）
  - J-Quants から株価（OHLCV）・財務・市場カレンダーを差分取得して DuckDB に保存
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）
  - RSS の取得、前処理、記事ID生成（URL 正規化 + SHA256）
  - raw_news / news_symbols への冪等保存設計（実装は一部モジュールで提供）
- ニュース NLP（score_news）
  - gpt-4o-mini を用いて銘柄ごとのセンチメント（-1.0 〜 1.0）を算出し ai_scores に保存
  - バッチ化・リトライ・レスポンスバリデーション実装
- 市場レジーム判定（score_regime）
  - ETF（1321）200 日移動平均乖離（70%）と LLM マクロセンチメント（30%）を合成して daily のレジーム判定
  - DuckDB へ冪等的に書き込み
- J-Quants クライアント（jquants_client）
  - レートリミット管理、リトライ、IDトークン自動リフレッシュ、ページネーション対応
  - DuckDB への冪等保存関数（raw_prices / raw_financials / market_calendar）
- 監査ログスキーマ（audit）
  - signal_events, order_requests, executions 等のテーブル定義と初期化ユーティリティ
- リサーチ（research）
  - モメンタム / バリュー / ボラティリティ ファクター計算、将来リターン・IC・統計サマリー等
- 共通ユーティリティ
  - 設定（kabusys.config.Settings）、統計ユーティリティ（zscore_normalize）など

前提・依存
-----------

主な Python ライブラリ（pip でインストール）:

- duckdb
- openai (OpenAI の Python SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, datetime など）

推奨: 仮想環境 (venv / virtualenv / Poetry 等) を使用してください。

セットアップ手順
---------------

1. リポジトリをクローンして作業ディレクトリへ移動

   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成・有効化（例: venv）

   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows (PowerShell では .venv\Scripts\Activate.ps1)

3. 必要パッケージをインストール

   pip install -U pip
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）
   開発インストール（パッケージを import できるようにする）:

   pip install -e .

4. 環境変数（.env）を用意する

   プロジェクトルートに .env または .env.local を置くと自動でロードされます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   最低限必要な環境変数（例）:

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXX
   OPENAI_API_KEY=sk-...

   追加設定:
   KABUSYS_ENV=development|paper_trading|live  (デフォルト development)
   LOG_LEVEL=INFO|DEBUG|...  (デフォルト INFO)
   DUCKDB_PATH=data/kabusys.duckdb  (デフォルト)
   SQLITE_PATH=data/monitoring.db

   注意:
   - config.Settings は .env.example を参照しているため、実務では .env.example をコピーして .env を作成してください（本リポジトリに .env.example が無い場合は README の例を参考に設定してください）。
   - 自動ロードはパッケージ起動時に .git または pyproject.toml を基準にプロジェクトルートを検出して .env を読み込みます。

使い方（主要なユースケース）
---------------------------

以下は簡単な利用例です。全て Python スクリプト内で実行できます。

- DuckDB 接続例

  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行

  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

  これにより市場カレンダー→株価→財務→品質チェックの流れで差分取得／保存が実行されます。

- ニュースセンチメント（銘柄別）を算出して保存

  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026,3,20))
  print(f"written {written} scores")

  注意: OPENAI_API_KEY（または api_key 引数）を設定している必要があります。

- 市場レジーム判定

  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20))
  # market_regime テーブルへ書き込みが行われます

  注意: OPENAI_API_KEY が必要です。

- 監査ログ用 DB 初期化（監査専用 DB を作る例）

  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # signal_events / order_requests / executions テーブルが作成される

- RSS 取得（ニュース収集の一部）

  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])

  取得した記事を raw_news テーブルに保存するには、DB スキーマに合わせて挿入処理を実装してください（モジュール内の保存ロジックを参考にしてください）。RSS の正規化／SSRF 対策や最大バイト制限など安全対策が組み込まれています。

設定・動作に関する注意点
----------------------

- 環境変数/設定:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（使用機能に応じて）
  - 自動 .env 読み込みは有効化済み（必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）
- OpenAI:
  - gpt-4o-mini を JSON Mode で利用しています。API レスポンス検証を行い不正なレスポンスは安全にフォールバックします（デフォルトで 0.0 など）。
- J-Quants:
  - レート制限（120 req/min）に合わせた RateLimiter を実装済み。ID トークンは自動リフレッシュされます。
- Look-ahead バイアス:
  - すべての処理は "target_date" を明示的に指定するか、DB から target 日以前のみを参照することでルックアヘッドバイアスを避ける実装方針です。
- リトライ/フェイルセーフ:
  - 外部 API 呼び出しはリトライやフォールバック（例: LLM API 失敗時は 0.0 で継続）を行い、ETL 全体が 1 件の失敗で止まらないよう設計されています。

ディレクトリ構成（概要）
----------------------

以下は主要なモジュール／ファイルとその役割の一覧です（src/kabusys 以下）:

- __init__.py
  - パッケージのバージョン等を定義

- config.py
  - 環境変数読み込み・Settings クラス（J-Quants / kabuAPI / Slack / DB パス / 実行環境フラグ等）

- ai/
  - news_nlp.py        : ニュースセンチメント算出（score_news）
  - regime_detector.py : 市場レジーム判定（score_regime）
  - __init__.py        : 公開 API（score_news 等）

- data/
  - jquants_client.py      : J-Quants API クライアント（fetch / save）
  - pipeline.py            : ETL パイプライン（run_daily_etl 等）と ETLResult
  - news_collector.py      : RSS 取得・前処理・安全対策
  - calendar_management.py : 市場カレンダー取り扱い（is_trading_day 等）
  - quality.py             : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py               : 監査ログスキーマ定義と初期化
  - stats.py               : 汎用統計ユーティリティ
  - pipeline/etl.py、etl などの補助モジュール（ETLResult 再エクスポート）

- research/
  - factor_research.py     : モメンタム / バリュー / ボラティリティ ファクター計算
  - feature_exploration.py : 将来リターン / IC / 統計サマリー等
  - __init__.py            : 主要関数のエクスポート

- （将来的/別モジュール）
  - strategy/, execution/, monitoring/ など（パッケージ __all__ には存在するが、本コードベースでは一部実装・参照あり）

README に載せておくべき追加情報・運用メモ
----------------------------------------

- テスト: 各モジュールは外部 API 呼び出しを伴うため、ユニットテストではモック（unittest.mock）を想定しています。例えば OpenAI 呼び出し関数はモック可能なラッパー関数として定義されています。
- 本番運用: KABUSYS_ENV を "live" に設定すると取引関連の保護やログ設定を厳格に行うような分岐が入る想定です（コード内で is_live / is_paper / is_dev を参照）。
- データベース管理: DuckDB ファイルはデフォルト data/kabusys.duckdb に保存されます。監査ログ用に別ファイルを作ることもできます（init_audit_db を利用）。
- ロギング: LOG_LEVEL 環境変数で制御します。実行時に適切なログ出力を確認してください。
- セキュリティ: RSS の取得では SSRF／GZip Bomb 等の対策が入っています。外部 URL の扱いには注意してください。

サンプルワークフロー（まとめ）
---------------------------

1. .env を用意して必要な API キーをセット
2. 仮想環境で依存パッケージをインストール
3. DuckDB 接続を確立（settings.duckdb_path を使用）
4. run_daily_etl を実行してデータを取得・保存
5. score_news / score_regime を実行して AI スコアやレジーム判定を生成
6. research モジュールでファクター解析を行い、戦略に渡す
7. 戦略→注文→監査ログへ記録（監査 DB を init して使用）

お問い合わせ / 貢献
-------------------

バグ報告・機能提案や PR はリポジトリの Issue / Pull Request をご利用ください。  
設計方針や API の詳細は各モジュールの docstring に記載していますので、まずは該当ファイルを参照してください。

以上。必要であれば README に含める例 .env.example のテンプレートや、より具体的な使用例（ETL Cron ジョブ、Slack 通知の実装例、kabuステーション API 連携方法など）も追加できます。希望があれば教えてください。