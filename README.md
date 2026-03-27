# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、データ品質チェック、特徴量・ファクター計算、ニュースNLP、LLM を用いた市場レジーム判定、監査ログ（トレーサビリティ）など、運用に必要なコンポーネントを提供します。

---

## 主な機能

- データ取得（J-Quants）
  - 株価日足（OHLCV）取得・保存（差分取得・ページネーション対応）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
- ETL パイプライン
  - run_daily_etl による日次差分取得 + 品質チェック
  - 差分／バックフィル制御、品質チェックの集約
- データ品質チェック
  - 欠損（OHLC）・スパイク検出・重複チェック・日付不整合チェック
- ニュース収集
  - RSS フィード収集、前処理、raw_news への冪等保存
  - SSRF / Gzip / XML 攻撃対策実装済み
- ニュースNLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（ai_scores への書き込み）
  - バッチ処理、リトライ、レスポンスバリデーション
- 市場レジーム判定（LLM + テクニカル）
  - ETF(1321) の 200 日移動平均乖離とマクロセンチメントを組み合わせてレジーム判定
- 監査ログ（audit）
  - signal_events / order_requests / executions を含む監査スキーマの初期化ユーティリティ
  - order_request_id を冪等キーとするトレーサビリティ設計
- ユーティリティ
  - Z スコア正規化、将来リターン計算、IC（Spearman）計算等の研究用ユーティリティ

---

## 要件

- Python 3.10 以上（PEP 604 の `X | Y` 型注釈を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 環境変数（下記参照）や .env を利用

※ 実行環境に合わせて依存をインストールしてください（requirements.txt は本リポジトリに含まれていない想定）。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト、パッケージをインストール
   - ローカル開発:
     ```
     git clone <repo-url>
     cd <repo>
     pip install -e .
     ```
   - または必要なパッケージを個別にインストール:
     ```
     pip install duckdb openai defusedxml
     ```

2. 環境変数（.env）を作成する  
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先、.env.local は .env を上書き）。自動ロードを止めたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（必須は README 内で明示）:

   - J-Quants / データ
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - kabu ステーション（発注等）
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
   - Slack 通知
     - SLACK_BOT_TOKEN (必須)
     - SLACK_CHANNEL_ID (必須)
   - OpenAI
     - OPENAI_API_KEY (score_news / regime_detector を使う場合は必須)
   - データベースパス
     - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
   - 実行設定
     - KABUSYS_ENV (development|paper_trading|live, デフォルト: development)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)

   サンプル (.env):
   ```
   JQUANTS_REFRESH_TOKEN=eyJ...
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要な API と例）

下記はライブラリを直接インポートして利用する簡単な例です。実運用ではジョブスケジューラ（cron、Airflow 等）から呼び出すことを想定しています。

- 共通: 設定・DuckDB 接続
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄ごと）を生成して ai_scores に保存
  ```python
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", n_written)
  ```

- 市場レジーム判定（ma200 + マクロセンチメント）
  ```python
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用の DuckDB を初期化（監査スキーマ作成）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # init_audit_db は transactional=True 相当でスキーマを作成して接続を返す
  ```

- カレンダー関連ユーティリティ
  ```python
  from kabusys.data.calendar_management import (
      is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
  )

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  # カレンダー更新ジョブ（J-Quants から差分取得して保存）
  calendar_update_job(conn)
  ```

- RSS フィードの取得（ニュース収集の一部分）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

注意:
- OpenAI を使う関数（score_news, score_regime）は OPENAI_API_KEY が必要です。引数で api_key を渡すこともできます。
- DB 書き込みは基本的に冪等（ON CONFLICT 等）を考慮していますが、本番運用前にバックアップ・テストを推奨します。

---

## 自動 .env ロードについて

- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を探索）から `.env` と `.env.local` を自動で読み込みます。
- 優先順位: OS 環境変数 > .env.local > .env
- 無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / 設定管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュース NLU / ai_scores 生成
    - regime_detector.py — マーケットレジーム判定（MA200 + LLM）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント / 保存ロジック
    - pipeline.py           — ETL パイプライン / run_daily_etl 等
    - etl.py                — ETLResult 再エクスポート
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - quality.py            — データ品質チェック（QualityIssue）
    - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
    - news_collector.py     — RSS 収集・前処理
    - audit.py              — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py     — モメンタム・バリュー・ボラティリティ等
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー等
  - (その他) strategy/ execution/ monitoring パッケージ用のエクスポートが __all__ に含まれていますが、今回抜粋されているソースでは data/ research/ ai/ config/ の主要実装が中心です。

---

## 運用上の注意点

- Look-ahead bias を避ける設計になっています（関数内で date.today() を参照しない、DB クエリで排他条件を付ける等）。
- OpenAI / J-Quants 呼び出しはリトライやバックオフが組み込まれていますが、API キー管理とレート管理は運用側でも必ず監視してください。
- ETL・品質チェックの結果（ETLResult、QualityIssue）はログ・監査に残して、問題発生時に手動介入できるようにしてください。
- DuckDB スキーマに依存するため、スキーマ初期化の順序やマイグレーションを運用ルールとして定義してください。

---

この README はコードベースの主要コンポーネントと基本的な使い方をまとめたものです。実装の細部（パラメータや追加機能）については各モジュールの docstring を参照してください。何か追記してほしい部分があれば教えてください。