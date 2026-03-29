# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL・データ品質チェック・ニュース NLP（LLM）・市場レジーム判定・監査ログなどのユーティリティ群を提供します。

---

## 概要

KabuSys は以下の機能を組み合わせ、バックテスト・研究・運用に利用できるデータ基盤と分析ツールを提供します。

- J-Quants API を使った株価・財務・カレンダーの差分取得（ETL）
- DuckDB を用いたデータ保存・参照
- ニュース収集（RSS）とニュース単位／銘柄単位の NLP スコアリング（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）スキーマ初期化

このリポジトリはモジュール群として設計されており、既存の運用システムやジョブフローへ容易に組み込めます。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数）
  - ニュース収集（RSS 安全対策・SSRF 回避）
  - 市場カレンダー管理（営業日判定・next/prev/get_trading_days）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news）
  - 市場レジーム判定（score_regime）
  - OpenAI（gpt-4o-mini）を JSON Mode で呼び出すためのラッパーとリトライ/フォールバック
- research
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索・IC 計算・統計サマリー

---

## 要件

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging など

（プロジェクトに requirements ファイルがあればそちらを利用してください）

例:
```
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. Python 3.10 以上を用意する。

2. 依存パッケージをインストールする:
   ```
   pip install duckdb openai defusedxml
   ```

3. プロジェクトルートに `.env`（および必要であれば `.env.local`）を作成する。サンプル `.env.example` を参考にしてください。

4. 必要な環境変数（一部）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）

   自動で `.env` ロードされます（プロジェクトルートに .git または pyproject.toml がある場合）。自動ロードを無効にするには:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方（概略）

以下は代表的なユーティリティの簡単な使い方例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() が返す接続）を受け取ります。

- DuckDB 接続の作成:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL の実行:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- 株価差分 ETL（個別実行）:
  ```python
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
  ```

- ニュース NLP スコアリング（OpenAI API キーが環境変数にある前提）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査用独立 DB を作る場合）:
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- カレンダー更新バッチ（J-Quants から取得して保存）:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn, lookahead_days=90)
  ```

- 研究用ファクター計算:
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  recs = calc_momentum(conn, date(2026,3,20))
  # recs は [{ "date": ..., "code": "...", "mom_1m": ..., ... }, ...]
  ```

注意:
- AI 周り（score_news / score_regime）は OpenAI API を呼び出します。API キーは引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL の多くは外部 API（J-Quants）へアクセスします。J-Quants の認証は JQUANTS_REFRESH_TOKEN を通じて行われます。

---

## 環境変数の自動読み込み

パッケージは起動時にプロジェクトルート（.git または pyproject.toml）を探索し、`.env` → `.env.local` の順で自動読み込みします。OS 環境変数は上書きされません（`.env.local` は上書き可）。自動読み込みを止めるには環境変数を設定します:

```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

.env の値のパースはシェル風の書式（export を含む行や引用符、コメント）に対応します。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダー管理、営業日判定
    - news_collector.py      — RSS ニュース収集（SSRF 対策等）
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ初期化
    - etl.py                 — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility
    - feature_exploration.py — forward returns / IC / summary / rank

---

## 設計上の注意点・フェイルセーフ

- ルックアヘッドバイアス回避のため、内部実装は date / target_date を明示的に受け取る設計です。datetime.today()/date.today() の直接参照を避けています（ETL のデフォルトは today を用いますが、テスト時は明示指定が推奨）。
- OpenAI / J-Quants 等の外部 API 呼び出しはリトライ / バックオフ / フェイルセーフ（API 失敗時はスコアを 0 にフォールバック、例外を上位へ送らない箇所あり）を備えています。
- ニュース収集は SSRF 対策・XML パースの安全化・受信サイズ制限（Gzip 含む）を実装しています。
- DuckDB へは冪等的に保存（ON CONFLICT DO UPDATE / DO NOTHING）を行います。

---

## 開発・テストについて

- 単体テストは含まれていません（存在する場合は tests/ 等を参照）。
- モジュール内部のネットワークリクエストはモックしやすい設計（関数差し替え / unittest.mock.patch）になっています。

---

## 参考

- 設定は kabusys.config.settings から取得できます:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```
- 詳細な関数仕様や SQL は各モジュールの docstring を参照してください（ソース内に詳細な設計・前提が記載されています）。

---

この README はコードベースの主要ポイントをまとめたものです。運用・デプロイ時には API キー・シークレット管理やジョブログ・監視・バックテスト用データの準備など、環境固有の追加設定が必要です。必要であれば各モジュールの利用例や運用テンプレート（systemd / cron / Airflow ジョブ例等）も作成します。