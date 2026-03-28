# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants からのデータ取得（ETL）、ニュース収集・NLP による銘柄スコアリング、研究用ファクター計算、監査ログ（発注→約定トレース）などを提供します。

主な設計方針は「ルックアヘッドバイアス回避」「DuckDB ベースのローカル DB」「API 呼び出しに対するフェイルセーフとリトライ」「冪等性（Idempotency）」です。

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 環境変数（.env）設定
- 基本的な使い方（例）
- ディレクトリ構成
- 補足・注意事項

---

## プロジェクト概要

KabuSys は日本株のデータパイプラインと研究・戦略実行のための共通ユーティリティ群を提供する Python パッケージです。主に以下を目的とします。

- J-Quants API からの株価・財務・市場カレンダー取得（差分 ETL、冪等保存）
- RSS からのニュース収集と記事と銘柄の紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / マクロセンチメント評価
- ファクター（モメンタム/バリュー/ボラティリティ等）計算と探索用ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログテーブル（signal → order_request → executions）の初期化と管理

---

## 機能一覧

- config: .env / 環境変数の自動読み込み、設定取得（KABUSYS_ENV / LOG_LEVEL 等）
- data:
  - jquants_client: J-Quants API 呼び出し、トークン自動リフレッシュ、リトライ、DuckDB への保存（raw_prices, raw_financials, market_calendar など）
  - pipeline/etl: 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - news_collector: RSS 取得／前処理／raw_news への冪等保存、SSRF 対策、gzip サイズチェック等
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - audit: 発注〜約定を追跡する監査用テーブルの DDL と初期化ユーティリティ
  - stats: Zスコア正規化など統計ユーティリティ
- ai:
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュース LLM スコアを合成して市場レジーム（bull/neutral/bear）を計算・保存
- research:
  - factor_research: calc_momentum / calc_value / calc_volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、統計サマリー

---

## 必要条件

- Python 3.10+
- 必要な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード、OpenAI）
- J-Quants リフレッシュトークン、OpenAI API キー 等の環境変数（後述）

---

## セットアップ手順

1. リポジトリをクローン、作業ディレクトリへ移動:
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（任意）:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール（pyproject.toml / requirements.txt が用意されている想定）:
   ```
   pip install -e .          # 開発インストール（パッケージがセットアップされている場合）
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定（.env をプロジェクトルートに置くことで自動ロードされます。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）:
   - 必須:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注連携時）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャネル ID
   - 任意 / 推奨:
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に使用）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

以下は主要なユースケースの簡単な利用例です。実行前に env をセットしてください。

- DuckDB に接続して日次 ETL を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（ai_scores）を作成する:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n_written} codes")
  ```

- 市場レジーム（market_regime）をスコアリングする:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査用 DuckDB を初期化する:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit_duck.db")
  # これで signal_events / order_requests / executions テーブルが作成される
  ```

- ファクター計算（例: モメンタム）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

---

## 環境変数と自動 .env 読み込み

- パッケージ起動時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` と `.env.local` を自動でロードします（OS 環境変数 > .env.local > .env の優先順位）。
- 自動ロードを無効化する場合: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時等に便利）。
- 必須の設定に不足があると、Settings プロパティ（kabusys.config.settings）アクセス時に ValueError が発生します。
- 主要な設定:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OPENAI_API_KEY: score_news / score_regime で使用（関数引数で上書き可）
  - KABUSYS_ENV: "development" / "paper_trading" / "live"
  - LOG_LEVEL: ログレベル

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/設定読み込みロジック（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に保存
    - regime_detector.py — MA200 とマクロニュースを合成して market_regime を評価
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（認証、リトライ、保存ロジック）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 取得 / 前処理 / raw_news 保存（SSRF/サイズ対策）
    - calendar_management.py — market_calendar 管理・営業日判定・更新ジョブ
    - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログ DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - research/ 以下は分析・研究用関数群

---

## 補足・注意事項

- OpenAI 呼び出しは gpt-4o-mini（JSON mode）を利用する設計です。API 失敗時はフェイルセーフとしてスコア 0.0 を返す等の挙動をしますが、API キーは必須です（関数引数で明示的に渡すことも可能）。
- J-Quants API はレート制限（120 req/min）を尊重するよう内部でスロットリングを実装しています。get_id_token はリフレッシュ処理を内包します。
- DuckDB に対する複数行挿入や executemany の空リストは一部バージョンで制約があるため、空チェックをしてから executemany を実行しています。
- 全体として「外部 API 呼び出しに対して堅牢に」「Look-ahead bias を避ける」ことを重視した実装方針です。バックテスト等で使用する際はデータ取得日時（fetched_at）・ETL 実行日の扱いに注意してください。
- テスト環境では環境変数自動ロードを無効化するか、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してテスト用の環境を整えてください。

---

この README はコードの説明を抜粋した概観です。各モジュールの詳細な仕様（引数、戻り値、エラー条件など）は該当ソースファイルのドキュメント文字列（docstring）を参照してください。必要があれば各機能ごとのサンプルスクリプトや運用手順（cron / Airflow など）を追加で作成します。