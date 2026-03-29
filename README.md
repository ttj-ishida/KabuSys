# KabuSys — 日本株自動売買プラットフォーム（簡易 README）

このリポジトリは日本株のデータプラットフォームと自動売買のためのライブラリ群です。データ収集（J-Quants、RSS）、ETL、データ品質チェック、特徴量・ファクター計算、ニュースの NLP（OpenAI）によるセンチメント評価、市場レジーム判定、監査ログ（取引トレーサビリティ）などの機能を含みます。

## プロジェクト概要
KabuSys は以下を目的としたモジュール群です。

- J-Quants API を使った株価・財務・カレンダーの差分取得と DuckDB への保存（ETL）
- RSS ニュースの収集と前処理（SSRF や XML の安全対策を含む）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント／市場レジーム判定のバッチ化
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 研究用ファクター計算、将来リターン、IC 等の統計ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）を DuckDB に初期化・管理
- 環境変数管理と簡易設定（.env 自動読み込み機能あり）

パッケージは `src/kabusys` に実装されています。各モジュールは DuckDB 接続を受け取り DB に対する操作を行う設計で、バックテストや本番での Look-ahead バイアス対策が施されています。

---

## 主な機能一覧
- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証・ページネーション・レートリミット・保存関数）
  - カレンダー管理（営業日判定、next/prev trading day、calendar_update_job）
  - ニュース収集（RSS fetch + 前処理、安全対策）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（Zスコア正規化）
- ai/
  - ニュース NLP（score_news: 銘柄ごとのセンチメントを ai_scores に書込）
  - 市場レジーム判定（score_regime: ETF の MA乖離 と マクロニュースで bull/neutral/bear を判定）
- research/
  - ファクター計算（momentum, value, volatility）
  - 特徴量解析（将来リターン、IC、統計サマリー 等）
- config.py
  - 環境変数設定クラス（settings）と .env 自動ロードロジック

---

## セットアップ手順

前提
- Python 3.10+（型注釈に `|` が使われているため）を推奨
- ネットワークアクセス（J-Quants / OpenAI / RSS）環境

1. リポジトリをクローンし、開発環境を作成
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -U pip
   ```

2. 必要パッケージをインストール（例）
   必須ライブラリ（実装コードより）:
   - duckdb
   - openai
   - defusedxml
   例:
   ```bash
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt があればそれを使用してください）

3. 環境変数の設定
   プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと、自動的に読み込まれます（テスト等で無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   主な環境変数（Settings 参照）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu API パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack のチャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime の呼び出し時に使用）

   例 `.env`（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DB の準備（監査ログなど）
   監査ログ用 DB を初期化する例:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # 以降 conn をアプリケーションで利用
   ```

---

## 使い方（簡単な例）

以下は Python スクリプト/REPL での利用例です。すべて DuckDB 接続（duckdb.connect）を渡す設計です。

- ETL（日次実行）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースセンチメントをスコア化して ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # Noneなら環境変数 OPENAI_API_KEY を参照
  print(f"written scores: {written}")
  ```

- 市場レジーム判定（market_regime テーブルへ書き込み）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved calendar records:", saved)
  ```

- 監査ログスキーマ初期化（既存接続へ）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- RSS フィード取得（ニュース収集の一部処理）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["datetime"], a["title"])
  ```

注:
- OpenAI を使う関数（score_news, score_regime）は API 呼び出し失敗時に安全にフォールバックする設計ですが、API キーが未設定だと ValueError を送出します。api_key 引数か環境変数 OPENAI_API_KEY を設定してください。
- ETL / J-Quants 呼び出しはネットワーク依存でレート制御・リトライ・トークン自動リフレッシュを組み込んでいます。

---

## .env 自動読み込みについて
`kabusys.config` はプロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env のパースはシェル互換の `export KEY=value` やクォート、コメントなどに対応しています。

---

## ディレクトリ構成（主要ファイル）
以下は `src/kabusys` の主要モジュールと役割です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメントのバッチ評価（ai_scores へ書込）
    - regime_detector.py  — 市場レジーム判定（ma200 + マクロニュース）
  - data/
    - __init__.py
    - pipeline.py         — ETL パイプラインの実装（run_daily_etl 等）
    - etl.py              — ETLResult の公開エイリアス
    - jquants_client.py   — J-Quants API クライアント（fetch / save）
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - news_collector.py   — RSS フィード取得、前処理（SSRF 対策あり）
    - quality.py          — データ品質チェック
    - stats.py            — 統計ユーティリティ（zscore_normalize）
    - audit.py            — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py  — モメンタム / ボラティリティ / バリュー の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

各モジュールは docstring に詳細な設計方針・前提が記載されています。実装は DuckDB を中心に SQL と Python を組み合わせた構成です。

---

## 注意事項 / ベストプラクティス
- 本ライブラリは DB（DuckDB）を直接書き換えるため、バックテストでの Look-ahead を避けるための制約（API 呼び出し日時保存、日付フィルタ等）に留意して利用してください。
- OpenAI の呼び出しはコストとレートに注意してください（バッチ単位での利用、リトライロジックあり）。
- J-Quants の利用には API トークンが必要です。`JQUANTS_REFRESH_TOKEN` を安全に管理してください。
- RSS の取得は外部 URL を扱うため、`fetch_rss` は SSRF 対策や受信サイズ制限を組み込んでいますが、運用時はソースの許可設定・監視を行ってください。

---

もし README に追加したい「実行スクリプト例」「CI 設定」「テストの書き方」などがあれば、その要望を教えてください。README を用途に合わせて拡張します。