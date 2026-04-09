# KabuSys

バージョン: 0.1.0

日本株向けの自動売買 / データ基盤ライブラリ。ETL、データ品質チェック、ファクター計算、ニュース NLP、OpenAI を用いた市場レジーム判定や銘柄ごとのニュースセンチメント評価、監査ログ（発注→約定のトレーサビリティ）などを提供します。

---

## 概要

KabuSys は以下のような機能を備えた内部向けライブラリです。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いた ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集 / 前処理（RSS）と OpenAI を用いたニュースセンチメント解析（銘柄単位）
- 市場レジーム判定（ETF の MA とマクロニュースを融合）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）とリサーチ用ユーティリティ
- 監査ログ（signal → order_request → executions）の初期化・管理
- 設定は環境変数 / .env から管理（自動読み込み機能あり）

設計上の特徴:
- ルックアヘッドバイアスを避けるため、内部で datetime.today()/date.today() を直接参照しない実装が採用されています（関数に target_date を与える形）。
- DuckDB を中心とした SQL ベースの処理で、外部ライブラリへの依存を最小化しています。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch/save 系）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS fetch_rss / raw_news 保存ロジック）
  - 品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - score_news(conn, target_date, api_key=None): ニュース NLU により銘柄ごとの ai_score を ai_scores テーブルへ書き込み
  - score_regime(conn, target_date, api_key=None): ETF の MA とマクロニュースで市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込み
- research
  - calc_momentum / calc_value / calc_volatility
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、ランク化
- config
  - Settings クラスで環境変数をラップして提供（自動 .env ロード機能）

---

## 前提 / 必要条件

- Python 3.10 以上（型ヒントで `X | Y` を使用）
- 必要なライブラリ（代表例）:
  - duckdb
  - openai (OpenAI SDK)
  - defusedxml
  - （標準ライブラリ以外の依存は setup.py / pyproject.toml に記載されている想定です）

実行環境によって追加のライブラリが必要になる場合があります（例: ネットワークアクセス、SSL、system time settings など）。

---

## セットアップ手順

1. リポジトリをクローン / checkout

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (macOS / Linux) または .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - pip install -e .    # プロジェクトがパッケージ化されている前提
   - もしくは requirements.txt / pyproject.toml があればそれに従う

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと、自動で読み込まれます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. .env の例（プロジェクトルートに `.env` を作成）
   必須:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password

   推奨 / オプション:
   - OPENAI_API_KEY=sk-...
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_FILL_MODE=instant
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - LOG_LEVEL=INFO
   - KABUSYS_ENV=development

   注意:
   - settings.jquants_refresh_token / settings.kabu_api_password はプロジェクト内で必須プロパティです。未設定時には ValueError が発生します。

6. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトから利用する例です。DuckDB 接続は duckdb.connect(<path>) を使用します。

- 日次 ETL を実行する（データ取得・保存・品質チェックを一括で実行）

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアを計算する（OpenAI API キーが必要）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を明示的に渡すか環境変数 OPENAI_API_KEY を設定
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書込み銘柄数: {written}")

- 市場レジーム判定

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB の初期化（監査用専用 DB を作る）

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を用いて insert / query 可能

- RSS フィード取得（ニュース収集）例

  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])

注意点:
- score_news / score_regime は OpenAI を呼ぶため API キーを必要とします。引数で api_key を渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL / save 系関数は DuckDB のスキーマが事前に用意されていることを前提に動作します。スキーマ初期化はプロジェクトの別スクリプトやマイグレーションで行ってください（このコードベースはスキーマ DDL を内包するモジュールがあるため、init_audit_schema などを参考に実装できます）。

---

## 重要な環境変数（一覧）

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（settings.jquants_refresh_token）
- KABU_API_PASSWORD: kabuステーション API のパスワード（settings.kabu_api_password）

OpenAI 関連:
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で使用

ログ / パス / モード:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（監視用、デフォルト: data/monitoring.db）
- PAPER_FILL_MODE: paper trading の fill モード（instant | partial | never | reject）

自動 .env ロード:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化

---

## ディレクトリ構成（主要ファイル説明）

src/kabusys/
- __init__.py
  - パッケージ公開 API。バージョン情報等。
- config.py
  - Settings クラス、.env 自動ロードロジック、必須設定チェック
- ai/
  - __init__.py
  - news_nlp.py: ニュースを銘柄ごとに集約して OpenAI に投げ、ai_scores に書き込むロジック
  - regime_detector.py: ETF (1321) の MA とマクロニュースを組み合わせて市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline.py: ETL パイプライン（差分取得・保存・品質チェック）
  - etl.py: ETLResult の再エクスポート
  - calendar_management.py: 市場カレンダー管理（営業日判定等）
  - news_collector.py: RSS 取得・前処理・保存ロジック
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py: 統計ユーティリティ（zscore_normalize）
  - audit.py: 監査ログテーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py: モメンタム／バリュー／ボラティリティ等を計算
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー、rank
- ai/regime_detector.py, ai/news_nlp.py の実装は OpenAI との堅牢なインタラクション（リトライ、エラー処理、レスポンス検証）を含みます。

---

## 運用上の注意

- OpenAI 呼び出しと外部 API にはリトライやフェイルセーフ（失敗時はスコア 0.0 等）の実装がありますが、コストやレート制限に注意して運用してください。
- DuckDB に対する executemany の空引数などバージョン依存の注意点があり、コードは互換性に気をつけて実装されています。duckdb のバージョンに依存する挙動がある場合は README に追記してください。
- ニュース収集では SSRF 対策や XML パースの安全化（defusedxml）を実施しています。RSS ソース追加時は信頼できるソースを登録してください。
- 監査ログは削除しない前提で設計されています（FK は ON DELETE RESTRICT）。監査テーブルのサイズ管理（アーカイブ等）は運用で対応ください。

---

## 貢献 / 拡張のヒント

- スキーマ初期化スクリプトの提供や CLI ラッパー（ETL ジョブ、カレンダー更新、監視プロセス起動）を作ると運用が容易になります。
- OpenAI モデルやプロンプトのチューニング、Batch サイズやトークン制限の調整を検討してください。
- テスト: OpenAI / 外部 API 呼び出し部分はモック可能な抽象化を取り入れているため、ユニットテストの実装がしやすい構造です（例: _call_openai_api を patch）。

---

README の内容について補足や、実際に使うための CLI やサンプル起動スクリプト作成などをご希望であれば、その用途に合わせて具体例（systemd ユニット、cron、GitHub Actions ワークフローなど）を作成します。