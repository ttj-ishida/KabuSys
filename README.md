# KabuSys

日本株のデータプラットフォームと自動売買（研究・シグナル・監査）を支援する Python パッケージです。  
DuckDB をバックエンドに、J-Quants（マーケットデータ）・OpenAI（ニュースNLP）・kabuステーション（発注）などと連携するコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を提供します。

- データ取得・ETL（J-Quants からの株価／財務／市場カレンダー取得）
- ニュース収集・NLP（RSS 収集・OpenAI による銘柄別センチメント）
- 市場レジーム判定（ETF とマクロニュースを組み合わせた判定）
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー等）
- データ品質チェック
- 発注フローの監査ログ（監査テーブル初期化・監査用 DB）
- 設定管理（.env 自動読み込み等）

設計上の留意点（抜粋）：
- ルックアヘッドバイアスを避けるように日付の扱いに注意（関数は内部で date.today() に依存しない）
- J-Quants / OpenAI の呼び出しにはリトライやレート制御を実装
- DuckDB への保存は冪等（ON CONFLICT）で実施
- RSS の取り込みは SSRF／XML 脆弱性対策あり

---

## 機能一覧

主な機能（モジュール）：

- kabusys.config
  - 環境変数の読み込み・設定参照（.env/.env.local の自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- kabusys.data
  - ETL パイプライン（kabusys.data.pipeline.run_daily_etl 等）
  - J-Quants クライアント（fetch_* / save_*）
  - 市場カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（news_collector.fetch_rss / raw_news 保存ロジック）
  - データ品質チェック（quality.run_all_checks）
  - 監査ログ初期化（audit.init_audit_schema / init_audit_db）
  - 統計ユーティリティ（stats.zscore_normalize）
- kabusys.ai
  - ニュース NLP（news_nlp.score_news：銘柄ごとの ai_score を ai_scores に書き込み）
  - 市場レジーム判定（regime_detector.score_regime：1321 の MA とマクロ記事のセンチメントを合成）
- kabusys.research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特性解析（calc_forward_returns / calc_ic / factor_summary / rank）

その他：
- Audit テーブル DDL とインデックス、監査用 DB 初期化ユーティリティ
- J-Quants API 用の堅牢な HTTP / レート制御 / トークン管理

---

## セットアップ手順

前提：
- Python 3.10+（型ヒントに union types 等を使用）
- DuckDB が使用可能（Python パッケージ duckdb を使用）
- 必要な外部 API キー（J-Quants refresh token / OpenAI API key / Slack token 等）

1. リポジトリをクローン（またはパッケージのソースを取得）
   - 例: git clone <リポジトリ>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - 最小例:
     pip install duckdb openai defusedxml
   - 開発用に他パッケージがある場合はプロジェクトの requirements.txt / pyproject.toml を参照して下さい。
   - 開発中は editable install:
     pip install -e .

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（config モジュールの仕組み）。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（ETL の認証に使用）
   - OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector 等で使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注周り）
   - SLACK_BOT_TOKEN: Slack 通知用トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - （DB パスは省略可能、デフォルトを用いる: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db）

   例 .env（テンプレート）:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

---

## 使い方（概要と実例）

ここでは主要な操作例を示します。いずれも Python スクリプト / REPL 内で実行します。

- DuckDB 接続の作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行（run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を指定することでルックアヘッドバイアスを制御できます
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュース NLP（指定日のニュースをスコアリングして ai_scores に書き込む）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written {n_written} scores")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（研究用途）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB の初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit_duckdb.duckdb")
  # init_audit_db はテーブル・インデックスを作成します
  ```

- 設定値を参照
  ```python
  from kabusys.config import settings

  print(settings.duckdb_path)
  print(settings.is_live, settings.log_level)
  ```

注意点：
- OpenAI の呼び出しはコストとレート制限があるため、テスト時はモックしてください。モジュール内の `_call_openai_api` はテストでパッチ可能です。
- J-Quants の API 呼び出しはレート制限（120 req/min）とリトライロジックが組み込まれています。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要ファイル一覧（抜粋）です：

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュースのセンチメントスコアリング
    - regime_detector.py          — 市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py           — J-Quants API クライアント（fetch/save）
    - news_collector.py           — RSS 収集・前処理
    - calendar_management.py      — 市場カレンダー管理
    - quality.py                  — データ品質チェック
    - audit.py                    — 監査テーブル DDL / 初期化
    - stats.py                    — 共通統計ユーティリティ
    - etl.py                      — ETLResult の公開（短縮）
  - research/
    - __init__.py
    - factor_research.py          — ファクター計算（momentum/volatility/value）
    - feature_exploration.py      — 将来リターン / IC / 統計サマリー 等

各サブモジュール内にさらにヘルパー関数や詳細実装が含まれます。README に載せきれない詳細はソースコードの docstring を参照してください。

---

## 運用上の注意

- 機密情報（API キー等）は .env に直接保存する場合は権限管理に注意してください。CI/CD や本番環境ではセキュアなシークレット管理を推奨します。
- OpenAI / J-Quants の API 使用量には注意（コスト、レート）。生産環境での利用は適切なレート制御・エラーハンドリングを確認してください（ライブラリ側で実装済み）。
- news_collector は外部 RSS を取得するため、SSRF や XML 脆弱性対策を実装していますが、ソース追加時は信頼できるフィードを優先してください。
- DB スキーマや DDL は既定の動作で冪等に作られるよう配慮していますが、マイグレーションやスキーマ変更時はバックアップを取得してから作業してください。

---

もし README に追加してほしい具体的な使い方（例: 発注フロー、Slack 通知の使い方、docker-compose 定義等）があれば教えてください。必要に応じてサンプル .env.example や簡易起動スクリプトも作成します。