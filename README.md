# KabuSys

日本株向け自動売買／データプラットフォームライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース収集、ニュースの NLP スコアリング、ファクター計算、研究ユーティリティ、監査ログ、監視・実行層の支援機能を含みます。

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引・リサーチ基盤のためのモジュール群です。主な目的は次の通りです。

- J-Quants API からの株価・財務・マーケットカレンダー取得（ETL）
- RSS ベースのニュース収集と前処理
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（AI スコアリング）
- 市場レジーム判定（ETF の MA 乖離 × マクロニュースセンチメント）
- ファクター（モメンタム・バリュー・ボラティリティ等）計算および特徴量解析ユーティリティ
- データ品質チェック、監査ログ（トレース可能な発注／約定記録）用スキーマ
- DuckDB を中心としたローカル DB 管理

設計上の特徴：
- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を不必要に参照しない）
- 冪等性を意識した保存（ON CONFLICT / DELETE→INSERT のパターン）
- API 呼び出しに対するリトライ・バックオフを実装
- テスト容易性を意識した実装（内部呼び出しの差し替えが可能）

---

## 主な機能一覧

- 環境変数 / .env 管理（kabusys.config）
  - プロジェクトルートの .env / .env.local を自動読み込み（無効化可）
  - 必須設定を明示的に取得するユーティリティ

- データ（kabusys.data）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch_* / save_*）
  - 市場カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（RSS fetch + 前処理、SSRF/サイズ制限対策）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）

- AI（kabusys.ai）
  - ニュース NLP スコアリング（score_news） — 銘柄ごとのセンチメントを ai_scores に保存
  - 市場レジーム判定（score_regime） — ETF（1321）の MA200 乖離とマクロニュースの組合せ

- Research（kabusys.research）
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量解析（calc_forward_returns, calc_ic, factor_summary, rank）

- 監視・実行（execution / monitoring）など（パッケージに含めるためのエクスポート用プレースホルダあり）

---

## セットアップ手順

前提
- Python 3.10 以上（Union 型の `X | Y` 表記を使用）
- Git（推奨）

1. リポジトリをクローン（例）
   ```bash
   git clone <repository-url>
   cd <repository-root>
   ```

2. 仮想環境作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   （簡易的に主要依存のみ記載）
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 実プロジェクトでは requirements.txt / pyproject.toml を参照してください。

4. パッケージを開発モードでインストール（任意）
   ```bash
   pip install -e .
   ```

5. 環境変数の設定
   - ルート（プロジェクトルートに .git または pyproject.toml があると自動で .env 読み込みが行われます）
   - 自動ロードを無効にしたい場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）
   - 任意:
     - KABUSYS_ENV (development | paper_trading | live)
     - LOG_LEVEL (DEBUG | INFO | ...)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）

   例 .env（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   KABUSYS_ENV=development
   ```

---

## 使い方（簡単な例）

- DuckDB 接続を作成して ETL を実行する（日次 ETL）
  ```python
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # 引数で target_date, id_token など指定可能
  print(result.to_dict())
  ```

- ニューススコアリング（AI）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"wrote {written} ai scores")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの DuckDB 接続
  ```

- RSS フィード取得（ニュース収集のユーティリティ）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["title"], a["datetime"], a["url"])
  ```

注意点:
- OpenAI 呼び出しを行う関数は API キーの引数で上書き可能（テスト時に差し替えやモックがしやすく設計）
- DuckDB への保存は冪等性を考慮しているため、複数回実行しても既存データは上書き更新されます（ON CONFLICT 句など）
- ETL / AI 呼び出しはネットワークエラーや 5xx を考慮して内部でリトライ処理を行いますが、必要に応じて呼び出し元でのエラーハンドリングを推奨します

---

## ディレクトリ構成

プロジェクトは src/kabusys 以下にモジュールが配置されています。主要ファイル／パッケージは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env 読み込み・設定管理
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースの LLM ベースセンチメント解析（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save 系）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETL 結果クラス ETLResult のエクスポート
    - news_collector.py     — RSS 収集と前処理
    - calendar_management.py— 市場カレンダー管理・ジョブ
    - quality.py            — データ品質チェック
    - stats.py              — 汎用統計ユーティリティ（zscore）
    - audit.py              — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py    — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py— 将来リターン/IC/統計サマリー
  - ai/, data/, research/ はそれぞれのドメインロジックを含みます

その他:
- .env / .env.local （プロジェクトルートに置くと自動で読み込み）
- data/ 以下にデフォルトで DuckDB ファイル（data/kabusys.duckdb）や monitoring 用 SQLite（data/monitoring.db）を置く想定

---

## 実運用上の注意

- 環境（KABUSYS_ENV）を正しく設定してください（development / paper_trading / live）。live 時は実際の発注や外部通知に接続する想定となる部分があります。
- OpenAI 等の外部 API 呼び出しはコストが発生します。ローカルテストではモックや小さなバッチでの確認を推奨します。
- ニュース収集では外部 URL を扱うため SSRF 対策・サイズ上限等を実装していますが、プロダクション運用時はネットワークアクセス制御を併用してください。
- DuckDB のバージョン差異により executemany の挙動が変わる可能性があるため、デプロイ先の環境での検証を推奨します。

---

## 開発・テストのヒント

- AI 呼び出し内部関数（_call_openai_api 等）はモジュール内で差し替え可能な実装になっており、unittest.mock.patch で外部 API をモックしてユニットテストが可能です。
- 設定読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。CI 環境やユニットテストで自前で環境を制御したい場合に便利です。

---

必要であれば、README に以下を追加できます:
- pyproject.toml / requirements.txt の推奨依存バージョン
- より具体的な ETL 運用手順（cron / Airflow 例）
- Slack 通知・監視ジョブの使用例
- リファレンス（関数一覧と引数の簡潔な説明）

ご希望があれば追加・拡張します。