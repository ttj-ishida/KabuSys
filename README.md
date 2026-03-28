# KabuSys

日本株向け自動売買フレームワーク（KabuSys）。データ取得（J-Quants）、ETL、ニュース収集・NLP、ファクター研究、監査ログ、マーケットカレンダーなどを備え、戦略実装・監視・発注レイヤと連携できるよう設計されています。

バージョン: 0.1.0

---

## 概要

KabuSys は次の目的を持つモジュール群を提供します。

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL（DuckDB 保存）
- RSS ベースのニュース収集と前処理（raw_news / news_symbols）
- OpenAI を用いたニュースセンチメント（ai_scores）・市場レジーム判定
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と研究用ユーティリティ
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）を管理する DuckDB スキーマ
- マーケットカレンダー管理（JPX カレンダーの取得/判定）
- 設定管理（.env / 環境変数自動ロード）

設計上の特徴:
- ルックアヘッドバイアスを避ける（内部で datetime.today()/date.today() を不用意に参照しない）
- API 呼び出しにはリトライ・レート制御・フェイルセーフを実装
- DuckDB を中心としたローカルデータレイク設計（冪等な保存）

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API から daily quotes / financial statements / market calendar / listed info を取得・保存
  - レートリミッティング・認証リフレッシュ・ページネーション対応
- data.pipeline
  - run_daily_etl: 市場カレンダー・価格・財務の差分 ETL + 品質チェック一括実行
  - 個別 ETL ヘルパー（run_prices_etl / run_financials_etl / run_calendar_etl）
- data.news_collector
  - RSS 取得・前処理・ID 正規化・SSRF 対策など
- ai.news_nlp
  - ニュースを銘柄ごとにまとめ、OpenAI（gpt-4o-mini）でセンチメントを評価し ai_scores へ保存
- ai.regime_detector
  - ETF 1321 の 200 日 MA 乖離 + マクロニュースの LLM センチメントを合成して日次で market_regime を評価
- research
  - calc_momentum / calc_value / calc_volatility 等のファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank 等の研究ユーティリティ
- data.quality
  - 欠損・重複・スパイク・日付不整合検出（QualityIssue）
- data.audit
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
- config
  - .env 自動読み込み（プロジェクトルート検出）と Settings クラス（必須環境変数検証）

---

## 必要条件（Prerequisites）

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API・RSS・OpenAI など）
- J-Quants リフレッシュトークン、OpenAI API キー、kabu API などの資格情報

（実際の setup.py/pyproject.toml に依存関係を記載してください）

---

## セットアップ手順（Quick start）

1. リポジトリをクローンして開発インストール:

   git clone <repository-url>
   cd <repository>
   pip install -e .

2. 環境変数を設定（.env をプロジェクトルートに作成するのが推奨）:

   必須（Settings._require により未設定時は ValueError）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   推奨・オプション:
   - OPENAI_API_KEY（ai.score_news / regime_detector で必要）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（デフォルト）
   - KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi

   例 .env:
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG

   補足: テスト等で自動 .env の読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

3. DuckDB データベース用ディレクトリを作成（必要に応じて）:

   mkdir -p data

---

## 使い方（主要ユースケース例）

以下は極めて簡単な呼び出し例です。実際はログ設定・エラーハンドリング・運用ロジックを追加してください。

- 日次 ETL を実行する

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースのスコアリング（ai.news_nlp.score_news）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
  print("書き込み銘柄数:", n_written)

- 市場レジーム判定（ai.regime_detector.score_regime）

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20))

- 監査 DB の初期化

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成されます

- RSS 収集（news_collector.fetch_rss）

  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])

- カレンダー判定

  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect(str(settings.duckdb_path))
  print(is_trading_day(conn, date(2026,3,20)))
  print(next_trading_day(conn, date(2026,3,20)))

注意点:
- OpenAI を使う関数は api_key 引数を受け取るので、テスト時に明示的なキーの注入やモック差し替えが可能です。
- 多くのデータ処理関数は date を外部から注入する設計のため、ルックアヘッドバイアスを防ぎます。

---

## 設定（Environment / .env）

config.Settings 経由でアクセスします。主な設定:

- JQUANTS_REFRESH_TOKEN: 必須
- KABU_API_PASSWORD: 必須
- KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
- SLACK_BOT_TOKEN: 必須
- SLACK_CHANNEL_ID: 必須
- DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
- SQLITE_PATH: デフォルト "data/monitoring.db"
- KABUSYS_ENV: "development" / "paper_trading" / "live"（デフォルト development）
- LOG_LEVEL: "INFO" 等（デフォルト INFO）
- OPENAI_API_KEY: AI モジュールで必要

.env 自動読み込み:
- プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を読み込みます。
- OS 環境変数が優先されます。
- 自動ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（抜粋）

以下はリポジトリ内の主要なモジュール構成（提供されたファイル群に基づく抜粋）:

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - quality.py
  - stats.py
  - calendar_management.py
  - audit.py
  - pipeline.py
  - etl.py
  - audit.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/__init__.py
- その他（strategy / execution / monitoring 等は最初のパッケージ __all__ に含まれるが、この抜粋には未掲載）

（実際のリポジトリでは tests/、scripts/、pyproject.toml や README のトップレベルファイルがあるはずです）

---

## 運用上の注意

- ETL / AI 周りは外部 API（J-Quants / OpenAI）へのアクセスを伴うため、資格情報管理とレート制御に注意してください。
- ai モジュールは OpenAI のレスポンスが必ずしも期待通りでない可能性を考慮し、レスポンスのバリデーションやフェイルセーフ（0.0 フォールバック）を実装しています。
- DuckDB executemany は空リストを受け入れないバージョンがあるため、コード内で空チェックを行っています。
- 監査ログは削除しない前提で設計されています。運用上バックアップやアーカイブ戦略を検討してください。
- 本リポジトリは実際の発注を行うモジュール（kabu ステーション連携など）と組み合わせる前に、ペーパートレード環境で十分にテストすることを推奨します。

---

## 開発・テスト

- 環境変数自動ロードを無効化してユニットテストを実行するには:

  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- OpenAI / J-Quants への外部呼び出しはユニットテストではモックしてください（各モジュール内で _call_openai_api / _urlopen 等を patch できるよう設計されています）。

---

## 参考・補足

- この README は提供されたソースコードのスニペットに基づいて作成しています。実際の運用やパッケージ配布時は pyproject.toml / setup.cfg / requirements.txt に依存関係やエントリポイントを明記してください。
- ご希望があれば、README にさらに次の項目を追加できます:
  - 詳細な .env.example
  - CI / デプロイ手順
  - CLI スクリプトや systemd / cron ジョブ例
  - モジュール別の API ドキュメント（関数引数・戻り値の一覧）

--- 

開発者向けに追加で整備したいセクションがあれば教えてください（例: .env.example、運用 runbook、具体的な CLI コマンド例など）。