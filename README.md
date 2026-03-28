# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。本リポジトリはデータ取得（J-Quants）、ETL、ニュースNLP（OpenAI 経由のセンチメント解析）、市場レジーム判定、研究用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などを目的にしたユーティリティ群を提供します。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つ Python パッケージ群です:

- J-Quants API からの株価・財務・カレンダー取得（ページング／レート制御／自動リフレッシュ）
- DuckDB を用いた差分 ETL（保存は冪等：ON CONFLICT DO UPDATE）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- RSS ベースのニュース収集・前処理（SSRF 対策、トラッキング除去、gzip 制限）
- OpenAI（gpt-4o-mini など）を用いたニュースセンチメント解析（銘柄別 ai_score）
- ニュース + ETF MA を使った市場レジーム判定（bull / neutral / bear）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ
- 監査ログ（signal_events / order_requests / executions）の初期化ユーティリティ（DuckDB）

設計方針として、ルックアヘッドバイアスを避けるために内部で date.today() 等の暗黙参照を避け、DB クエリや呼び出し時の target_date に基づいて deterministic に動作します。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - jquants_client（API 呼び出し、レート制御、リトライ、保存関数）
  - news_collector（RSS 取得・前処理・raw_news 保存）
  - quality（データ品質チェック）
  - calendar_management（営業日判定、next/prev_trading_day 等）
  - audit（監査ログテーブル作成 / init_audit_db）
  - stats（zscore_normalize 等）
- ai/
  - news_nlp.score_news(conn, target_date[, api_key]) — 銘柄別ニュースセンチメントを ai_scores テーブルへ書き込み
  - regime_detector.score_regime(conn, target_date[, api_key]) — ETF(1321) MA200 とマクロニュース LLM スコアを合成して market_regime テーブルへ書き込み
- research/
  - factor_research (calc_momentum, calc_value, calc_volatility)
  - feature_exploration (calc_forward_returns, calc_ic, factor_summary, rank)

---

## セットアップ手順

前提:
- Python 3.10+（| 型ヒント、match なしだが union 型表記を使用しているため 3.10 以降を想定）
- pip

1. リポジトリをクローン / コピーして、パッケージインストール（開発モード推奨）:

   ```
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

2. 依存パッケージ（例）:
   - duckdb
   - openai
   - defusedxml

   直接インストールするなら:

   ```
   pip install duckdb openai defusedxml
   ```

   （必要に応じて他のライブラリを追加してください）

3. 環境変数の設定:
   - プロジェクトルートに `.env` / `.env.local` を置くことで自動的にロードされます（優先順: OS 環境 > .env.local > .env）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 主要な環境変数（例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=CXXXXXXX
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb    # デフォルト
     SQLITE_PATH=data/monitoring.db     # デフォルト（監視系）
     KABUSYS_ENV=development            # development | paper_trading | live
     LOG_LEVEL=INFO
     ```

4. データベースディレクトリ作成（必要なら）:
   - DuckDB ファイルの親ディレクトリが存在しない場合、init 関数が自動作成しますが、手動で用意することも可能です。

---

## 使い方（簡単な例）

以下は主要なユースケースの呼び出し例（概念コード）。実行は適切な環境変数・DB 初期化が済んでいることを前提にしています。

- DuckDB 接続例:

  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（run_daily_etl）:

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュース NLP スコアリング（銘柄別 ai_scores に書き込む）:

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（market_regime に書き込む）:

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB 初期化（監査専用の DuckDB を作る）:

  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # init_audit_db はテーブル群・インデックスを作成して接続を返す
  ```

- 研究用ファクター計算例:

  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  rows = calc_momentum(conn, target_date=date(2026,3,20))
  # rows: list[dict] - (date, code, mom_1m, mom_3m, mom_6m, ma200_dev)
  ```

ログレベルや実行環境は環境変数 `LOG_LEVEL`, `KABUSYS_ENV` で調整します。`KABUSYS_ENV` は "development" / "paper_trading" / "live" のいずれかを指定してください。

---

## ディレクトリ構成

主要なファイル・モジュール（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数と自動 .env ロード、設定ラッパー
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント解析（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py            — ETL パイプライン（run_daily_etl 他）
    - etl.py                 — ETLResult の再エクスポート
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - news_collector.py      — RSS 取得・前処理
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - quality.py             — データ品質チェック（QualityIssue）
    - stats.py               — zscore_normalize 等
    - audit.py               — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー
    - feature_exploration.py — forward returns, IC, factor summary, rank

各モジュールは概ね DuckDB 接続（duckdb.DuckDBPyConnection）を引数として受け取り、DB に対する読み書きを行います。OpenAI API を使う関数は `OPENAI_API_KEY` を環境変数で参照するか、関数パラメータで API キーを渡すことができます。

---

## 注意点・運用上のポイント

- 環境変数の自動読み込み:
  - 実装はプロジェクトルート（.git または pyproject.toml が存在する親ディレクトリ）を探索し、`.env` → `.env.local` を順に読み込みます（.env.local は上書き）。テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI API:
  - news_nlp / regime_detector は OpenAI の Chat Completions JSON Mode を利用する設計です。API 呼び出しはリトライやフォールバックが実装されていますが、利用時はコスト・レート制限に注意してください。API キーは `OPENAI_API_KEY` または関数引数で注入できます。
- J-Quants API:
  - jquants_client は ID トークンのリフレッシュ、レート制御（120 req/min）、リトライ（408/429/5xx）等を備えています。`JQUANTS_REFRESH_TOKEN` が必要です。
- DuckDB の互換性:
  - 一部コードは DuckDB の executemany / リストバインドの挙動に合わせて実装されています（空リストの executemany を避ける等）。DuckDB のバージョンによっては挙動が異なる場合があるため注意してください。
- セキュリティ:
  - news_collector は SSRF 対策や XML パースの安全化（defusedxml）を組み込んでいます。外部 URL を扱う場合は追加の運用ルールを設けてください。

---

## 貢献 / 開発者向け

- コーディング規約・テスト:
  - 現段階の README では詳細テスト手順を記載していません。ユニットテストを追加する場合は、API キーを直接使わずにモック（unittest.mock）で外部呼び出しを差し替えることを推奨します（本コードもテスト容易性を考え、内部の API 呼び出しを差し替え可能に実装しています）。
- マイグレーション・スキーマ変更:
  - DuckDB スキーマ変更は既存データに影響を与えるため、スキーマ更新時はバックアップ・互換性の検討を行ってください。

---

必要であれば、README に以下の追加情報も追記できます:
- 実行可能な CLI（もしあれば）の使い方
- サンプル .env.example
- CI / テスト実行方法
- ライセンス情報

追記や修正したい箇所があれば教えてください。