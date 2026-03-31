# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J‑Quants からの株価・財務・カレンダー取得）、ニュース収集と LLM を用いたニュースセンチメント、マーケットレジーム判定、ファクター計算・研究ユーティリティ、監査ログスキーマなどを提供します。

---

## 主な機能

- データ取得・ETL
  - J‑Quants API からの株価（日次 OHLCV）・財務データ・JPX カレンダーの差分取得と DuckDB への冪等保存
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質管理
  - 欠損・スパイク・重複・日付不整合のチェック（quality モジュール）
- ニュース処理（NewsCollector）
  - RSS 取得、前処理、SSRF 対策、記事ID の冪等化
- AI（LLM）分析
  - ニュース NLP（銘柄ごとのセンチメントを ai_scores に保存する設計） — score_news
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成） — score_regime
- 研究用ユーティリティ
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（情報係数）、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions といった監査テーブルの初期化・管理（init_audit_schema / init_audit_db）
- J‑Quants クライアント
  - レート制御、リトライ、トークン自動リフレッシュ、ページネーション対応

---

## 動作要件（想定）

- Python 3.10+（typing | パターンに合わせて 3.10 以上を推奨）
- 主な依存パッケージ（抜粋）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J‑Quants API / RSS / OpenAI API）

（実際の pyproject.toml / requirements.txt を参照してインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <リポジトリ URL>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 依存関係のインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements があれば `pip install -e .` または `pip install -r requirements.txt` を使用）

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   必須の環境変数（本番的に動かす場合）:
   - JQUANTS_REFRESH_TOKEN：J‑Quants のリフレッシュトークン
   - KABU_API_PASSWORD：kabu ステーション API のパスワード（発注を使う場合）
   - SLACK_BOT_TOKEN：Slack 通知を行う場合のボットトークン
   - SLACK_CHANNEL_ID：Slack の通知先チャンネル ID

   推奨 / オプション:
   - OPENAI_API_KEY：OpenAI API を使う場合（LLM 呼び出し）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PID_FILE_PATH、CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など監視用設定
   - KABUSYS_ENV（development | paper_trading | live）
   - LOG_LEVEL（DEBUG/INFO/...）

   サンプル (.env)
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な利用例）

以下は Python REPL / スクリプトから利用する例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を作る（デフォルトパスは settings.duckdb_path）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL（株価 / 財務 / カレンダーの取得・保存・品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # 今日分を取得してパイプライン実行
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（LLM を用いた銘柄別スコア取得）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY が環境変数にあること
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {n_written} ai_scores rows")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査データベースの初期化（監査ログ専用の DuckDB を作成）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算 / 研究関数の利用例
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

  target = date(2026, 3, 20)
  momentum = calc_momentum(conn, target)
  forward = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(momentum, forward, "mom_1m", "fwd_1d")
  ```

- RSS を取得する（ニュース収集モジュールのユーティリティ）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  # raw_news テーブルへ保存するロジックはプロジェクト固有の実装に従って行ってください
  ```

注意:
- score_news / score_regime は OpenAI API を呼び出します。API キーを渡すか環境変数 OPENAI_API_KEY を設定してください。
- DuckDB に書き込むテーブルスキーマはプロジェクト側で用意されている前提です（raw_prices / raw_financials / raw_news / ai_scores / market_regime 等）。

---

## 主要モジュール・ディレクトリ構成

リポジトリ内の主要なモジュールを抜粋した構成例（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・settings（J‑Quants トークン・DB パス・監視設定等）
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメント（score_news）
    - regime_detector.py  — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py   — J‑Quants API クライアント（fetch/save）
    - news_collector.py   — RSS 取得・前処理
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py          — データ品質チェック
    - stats.py            — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py            — 監査ログスキーマ初期化・DB 初期化
    - etl.py              — ETL 公開インターフェース（ETLResult 再エクスポート）
  - research/
    - __init__.py
    - factor_research.py  — ファクター計算（momentum / value / volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - ai、data、research の各モジュールはテストフレンドリーに設計され、ネットワーク呼び出し箇所は差し替え可能（モック）に作られています。

---

## 運用上の注意 / ベストプラクティス

- 環境変数を `.env` に置く場合、`.env` と `.env.local` の読み込み順序に注意してください（OS 環境 > .env.local > .env）。自動ロードはプロジェクトルートを .git または pyproject.toml から検出します。
- LLM（OpenAI）呼び出しはコスト・レイテンシ・利用制限があります。バッチサイズやリトライ方針はモジュール内で制御されていますが、運用時は API キーのレート・コスト管理を行ってください。
- J‑Quants API のレート制限に合わせて内部でスロットリングを実装していますが、長時間バッチ動作時は運用監視（CPU/メモリ/ディスク）やログの適切な設定を行ってください。
- DuckDB の schema（テーブル定義）は ETL 前に用意されていることを前提とします。テーブルがない場合は関連モジュールでエラーやスキップが発生する箇所があります。

---

README に含めるべき追加の情報（例）:
- 実際のテーブルスキーマ / マイグレーション手順
- CLI スクリプト（もしあれば）や systemd / cron による定期実行例
- テストの実行方法（pytest 等）
- ライセンス

必要であれば上の点についても README を拡張します。