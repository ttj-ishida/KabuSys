# KabuSys

日本株向けの自動売買・データ基盤ライブラリ KabuSys の README です。  
このドキュメントはリポジトリ内のコード（src/kabusys）を基に、プロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、ETL パイプライン、データ品質チェック、ニュース収集・NLP（OpenAI を利用したセンチメント）、市場レジーム判定、監査ログ（監査トレーサビリティ）などを備えた研究・本番両対応の自動売買基盤コンポーネント群です。  
設計上の特徴として、ルックアヘッドバイアス防止、冪等性（idempotent）実装、堅牢なリトライ/バックオフ、SSRF 対策などが取り入れられています。

主な技術／依存（実行環境により追加）:
- Python 3.10+
- duckdb
- openai（OpenAI SDK / Chat API）
- defusedxml（RSS パース用）
- 標準ライブラリ中心の実装

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルートは .git または pyproject.toml を探索）
  - 必須環境変数取得時のバリデーション
- データ取得（J-Quants クライアント）
  - 日足（OHLCV）・財務データ・マーケットカレンダーのページネーション対応取得
  - 認証（リフレッシュトークン → id_token）とトークン自動リフレッシュ
  - レート制限（120 req/min）対策、リトライ／バックオフ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 差分更新（最終取得日からの差分取得、バックフィル）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 日次 ETL の統合エントリ（run_daily_etl）
- ニュース収集
  - RSS フィード収集（SSRF 対策、gzip 制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存を想定
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを統合し LLM（gpt-4o-mini）でセンチメント算出（JSON Mode）
  - バッチ処理、リトライ、レスポンス検証、結果を ai_scores に保存
- 市場レジーム判定（regime_detector）
  - ETF(1321) の 200 日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成し 'bull'/'neutral'/'bear' を日次判定
  - LLM 呼び出しや DB 書き込みは冪等設計
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル DDL と初期化ユーティリティ
  - init_audit_db により監査用 DuckDB を初期化

---

## セットアップ手順

1. リポジトリをクローンして、プロジェクトルートに移動します（pyproject.toml または .git があることを想定）。

2. Python 仮想環境を作成・有効化し、必要なパッケージをインストールします。requirements.txt がない場合は主要依存を直接インストールしてください：

   pip install duckdb openai defusedxml

   （実際のプロダクションでは追加の依存があるかもしれません。pyproject.toml / requirements.txt を参照してください。）

3. 環境変数を設定します。リポジトリルートに `.env` または `.env.local` を作成できます。自動でロードされる仕組みがあります（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると無効化可能）。必要な環境変数（主なもの）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
   - SLACK_CHANNEL_ID: 通知先 Slack チャネル ID（必須）
   - OPENAI_API_KEY: OpenAI を利用する処理（news_nlp / regime_detector）を実行する場合は必須（関数引数でも指定可）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視データ等）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 `.env`（簡易）:
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567

4. DuckDB 初期スキーマは用途により自動作成/手動作成してください。監査ログ用 DB を初期化する場合は下記の使用方法を参照してください。

---

## 使い方（主要な実行例）

以下はライブラリの主要 API を使った簡単なサンプルです。実行前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）を設定してください。

- ETL（日次パイプライン）の実行例:

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

  run_daily_etl は市場カレンダー → 株価ETL → 財務ETL → 品質チェック の順に実行し、ETLResult を返します。

- ニュースセンチメント（銘柄ごと）スコアリング:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY が環境変数にあるか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("scored:", n_written)

- 市場レジーム判定:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

  この関数は ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime テーブルへ書き込みます。OPENAI_API_KEY を環境変数または api_key 引数で指定してください。

- 監査ログ DB の初期化:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの DuckDB 接続

- RSS フィード取得（ニュース収集ユーティリティ）:

  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"])

注意点:
- OpenAI を利用する処理（news_nlp, regime_detector）は API 呼び出しに失敗した場合にフェイルセーフで 0 などの中立値にフォールバックする設計です（例外非伝播の処理もあり）。ただし API キー自体が未設定だと ValueError が発生します。
- J-Quants API 呼び出しは内部でトークンを自動リフレッシュします。J-Quants のリフレッシュトークンは必須です。

---

## 環境変数の自動読み込みについて

- モジュール kabusys.config はプロジェクトルートを .git または pyproject.toml を基準に自動検出し、ルートにある `.env` と `.env.local` を以下の優先順で読み込みます:
  - OS 環境変数（優先）
  - .env.local（override=True なので既存 OS 環境変数は保護）
  - .env（override=False）
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 設定値は kabusys.config.settings 経由で取得できます（プロパティにより値の検証が行われます）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py          — ニュース NLP / スコアリング（OpenAI）
  - regime_detector.py   — 市場レジーム判定（MA200 + マクロセンチメント）
- data/
  - __init__.py
  - jquants_client.py    — J-Quants API クライアント（取得 / 保存）
  - pipeline.py          — ETL パイプライン（run_daily_etl 等）
  - etl.py               — ETLResult の再エクスポート
  - news_collector.py    — RSS ニュース収集（SSRF対策、前処理）
  - calendar_management.py — マーケットカレンダー管理（営業日判定など）
  - stats.py             — 統計ユーティリティ（zscore_normalize）
  - quality.py           — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py             — 監査ログテーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py   — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー等

その他:
- データベースファイルのデフォルトパスは settings.duckdb_path（data/kabusys.duckdb）等

---

## トラブルシューティング / 実運用における注意点

- OpenAI 呼び出しはモデル（gpt-4o-mini）と JSON Mode を使用しています。API レスポンスが想定外の場合はログに警告が出てフェイルセーフ動作しますが、品質の確保のためレスポンス検証を確認してください。
- J-Quants のレート制限（120 req/min）を遵守する設計です。大量データの取得や並列処理時は注意してください。
- DuckDB の executemany で空リストを渡すとエラーになるバージョンがあるため、コード中で空チェックが入っています。スキーマや DuckDB バージョンを変更する場合は注意してください。
- news_collector は RSS の巨大レスポンスや圧縮攻撃を防ぐためサイズ上限と gzip 解凍後の検査を行っています。RSS ソースの追加は DEFAULT_RSS_SOURCES を更新してください。
- テスト時には一部の内部関数（例: OpenAI 呼び出し）をモックすることが想定されています（モジュール内に差し替えポイントあり）。

---

必要があれば README に含める実行コマンド、サンプル .env.example、あるいは各モジュールの詳細な API 仕様（関数引数や戻り値のスキーマ）をさらに追記します。どの部分を詳細化するか教えてください。