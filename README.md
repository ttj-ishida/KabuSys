# KabuSys

日本株向けの自動売買・データ基盤ライブラリ KabuSys のリポジトリ用 README（日本語）

---

## プロジェクト概要

KabuSys は日本株取引向けに設計されたデータパイプライン、ファクター／リサーチ、AI 支援のニュースセンチメント評価、監査ログといったコンポーネントを備えたソフトウェア基盤です。主な目的は以下です。

- J-Quants API から株価・財務・市場カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- ニュースを収集して LLM（OpenAI）で銘柄ごとのセンチメントを算出する機能
- ETF とマクロニュースを組み合わせた市場レジーム判定
- ファクター計算（モメンタム／バリュー／ボラティリティ）や将来リターン・IC 計算によるリサーチ用ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）を DuckDB に初期化・管理する仕組み
- データ品質チェック（欠損・スパイク・重複・日付不整合）など

この README はコードベースの主要機能と導入方法、基本的な使い方をまとめたものです。

---

## 主な機能一覧

- data
  - J-Quants クライアント（fetch/save 日足・財務・カレンダー・上場銘柄情報）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - カレンダー管理（営業日判定・next/prev trading day 等）
  - ニュース収集（RSS → raw_news の前処理・保存、SSRF や Gzip 対策）
  - 監査ログ（監査用テーブル定義・初期化、監査 DB 初期化ユーティリティ）
  - 汎用統計ユーティリティ（Z スコア正規化など）
  - データ品質チェック（missing / spike / duplicates / date consistency）
- ai
  - news_nlp.score_news: ニュースを LLM で銘柄単位にスコアリングして ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュースセンチメントを合成して市場レジームを判定
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（forward returns / IC / summary / rank）
- audit
  - 監査スキーマ初期化（init_audit_schema / init_audit_db）
- （パッケージ API には strategy / execution / monitoring 名のサブパッケージを公開）

---

## 前提（依存・前提条件）

- Python 3.10+（typing 機能を含む）
- 外部依存パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml
- J-Quants API および OpenAI API の利用にはそれぞれトークンが必要
- DuckDB をローカルファイルで使用する場合は書き込み権限のあるディレクトリが必要

（実際の requirements.txt はプロジェクトに合わせて用意してください）

---

## 環境変数（主要）

必須および推奨の環境変数：

- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID       : 通知先 Slack チャンネル ID（必須）
- OPENAI_API_KEY         : OpenAI API キー（ai モジュール使用時に必要）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            : 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL              : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

自動的に .env/.env.local をプロジェクトルートからロードします（.git または pyproject.toml を基準に探索）。
自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須変数が取得できない場合は Settings プロパティが ValueError を投げます。

---

## セットアップ手順

1. リポジトリをクローン／取得

   git clone <repo-url>
   cd <repo-dir>

2. Python 仮想環境の作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows

3. 依存パッケージをインストール

   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. 環境変数を設定（.env を作成）

   プロジェクトルートに .env を作り、必要な環境変数を記載します（例）：

   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

   ※ .env.local を用いることでローカル上書きが可能（.env.local は .env より優先される）。

5. DuckDB ファイルディレクトリ作成

   mkdir -p data

6. （オプション）監査 DB 初期化（下記参照）

---

## 使い方（抜粋、コード例）

以下は代表的なユースケースの簡単な使い方例です。各関数は DuckDB 接続（duckdb.connect()）を受け取ります。

- DuckDB 接続の作成例

  from pathlib import Path
  import duckdb
  db_path = Path("data/kabusys.duckdb")
  db_path.parent.mkdir(parents=True, exist_ok=True)
  conn = duckdb.connect(str(db_path))

- ETL（日次 ETL の実行）

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  # target_date を None にすると今日が対象（内部で営業日に調整される）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（ai.news_nlp.score_news）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定済みであれば api_key=None でも可
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"scored {count} symbols")

- 市場レジーム判定（ai.regime_detector.score_regime）

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を利用
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログスキーマの初期化（監査専用 DB を作成）

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # init_audit_db は transactional=True 相当でDDLを作成します

- カレンダー関連ユーティリティ（営業日判定など）

  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))

- 研究系ユーティリティ（ファクター計算）

  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))

---

## 注意点 / トラブルシューティング

- OpenAI 呼び出しはネットワークエラーやレート制限を考慮したリトライやフェイルセーフを実装しています。API エラーが続く場合は OPENAI_API_KEY の確認やレート制限の緩和をご検討ください。
- J-Quants API はレート制限（120 req/min）を守る実装ですが、トークンや権限切れ時は get_id_token で例外が発生します。JQUANTS_REFRESH_TOKEN の設定を確認してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から行われます。CI 等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany に空リストを渡すとバージョン依存で例外になるため、内部で空チェックを行ってありますが、独自に操作する際は注意してください。
- ニュース収集は外部 URL を扱うため SSRF 対策やサイズ制限が入っています。RSS の最終 URL がプライベートアドレスになる場合は取得をスキップします。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の src/kabusys 以下の主なファイル一覧（この README が参照しているファイル群ベース）：

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数／設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュースセンチメント（score_news）
    - regime_detector.py               — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント + 保存関数
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - etl.py                           — ETL インターフェース再エクスポート
    - news_collector.py                — RSS ニュース収集
    - calendar_management.py           — 市場カレンダー管理
    - quality.py                       — データ品質チェック
    - stats.py                         — 統計ユーティリティ（zscore_normalize）
    - audit.py                         — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py               — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py           — 将来リターン・IC・サマリー
  - ai (上記)
  - research (上記)
  - (その他) strategy/, execution/, monitoring/ パッケージ名で公開予定

---

## 開発 / 貢献

- コードの変更はユニットテストとスタイルチェック（lint）を通すことを推奨します。
- 環境変数や外部 API に依存するため、テスト時は環境読み込みを無効にしてモックを用いることを推奨します（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

補足: README は実際の運用に合わせて追記・調整してください。特にインストール可能なパッケージ名（PyPI）や requirements.txt、CI/CD 情報、.env.example の内容などはプロジェクトルートに合わせて整備すると導入が容易になります。