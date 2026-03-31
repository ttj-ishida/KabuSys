# KabuSys

日本株向けのデータプラットフォーム＋リサーチ／自動売買補助ライブラリです。  
J-Quants API と DuckDB を中心に、ニュース収集・NLP スコアリング・市場レジーム判定・ETL パイプライン・データ品質チェック・監査ログ（約定トレーサビリティ）などの機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()／datetime.today() を不必要に参照しない）
- DuckDB をローカル永続ストアとして使用、SQL と Python の組合せで高速処理
- API 呼び出しにはリトライ・レート制限対策を実装
- ETL / 品質チェックは部分障害に強い（個別フェーズでエラーを収集して継続）
- 監査ログ（signal → order_request → execution）でトレース可能にする

---

## 機能一覧

- データ取得・ETL
  - J-Quants からの日次株価（OHLCV）取得、財務データ、JPX カレンダー取得（pagination/認証/リトライ対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（カレンダー → 株価 → 財務 → 品質チェック）
- データ品質チェック
  - 欠損（OHLC）検出、前日比スパイク検出、主キー重複、日付整合性（未来日/非営業日）検出
- ニュース収集
  - RSS フィード取得（SSRF対策、トラッキングパラメータ除去、前処理）と raw_news 保存・銘柄紐付け
- ニュース NLP（AI）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント算出（ai_scores テーブルへ）
  - 批処理・トークン肥大対策・レスポンス検証・リトライ機構
- 市場レジーム判定（AI + 指標）
  - ETF(1321)の200日MA乖離（70%）とマクロニュースセンチメント（30%）の合成で日次レジーム判定（bull/neutral/bear）
  - LLM 呼び出しのリトライ・フォールバック実装
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の DDL とインデックス、初期化ユーティリティ
- リサーチユーティリティ
  - ファクター計算（Momentum/Value/Volatility 等）、将来リターン、IC（Spearman）計算、Zスコア正規化

---

## セットアップ手順

前提:
- Python 3.10+
- DuckDB（Python パッケージ）
- OpenAI SDK（gpt-4o-mini を利用するためのクライアント／API キー）
- defusedxml（RSS 安全パース）

1. リポジトリをクローンし、開発環境を用意する
   - 例（pipenv / venv 等は任意）:
     ```
     git clone <repo-url>
     cd <repo-root>
     python -m venv .venv
     source .venv/bin/activate
     pip install -U pip
     pip install duckdb openai defusedxml
     pip install -e .
     ```
   - （パッケージ化されている場合は requirements.txt / pyproject.toml に従ってください）

2. 環境変数（または .env）を設定する
   必須（機能に応じて）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注等を使う場合）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合
   - SLACK_CHANNEL_ID: Slack 通知先
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を使う場合）

   データベースや監視の既定値（任意で上書き可）:
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PID_FILE_PATH (デフォルト: data/execution.pid)
   - KABUSYS_ENV (development | paper_trading | live)
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

   .env の自動読み込み:
   - パッケージはプロジェクトルート（.git または pyproject.toml を基準）にある .env/.env.local を自動で読み込みます。
   - 自動読み込みを無効化する場合は環境変数を設定:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

3. データディレクトリを作成（DuckDB パスの親ディレクトリ）
   ```
   mkdir -p data
   ```

---

## 使い方（代表的な操作例）

以下は Python REPL やスクリプトから利用する例です。import 名は kabusys です。

- DuckDB 接続の作成（デフォルトパスを使う）
  ```python
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（ai_scores へ書き込み）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None: 環境変数 OPENAI_API_KEY を使用
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（専用 DB を用いる）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成されます
  ```

- データ品質チェックの実行（ETL の一部としても実行されます）
  ```python
  from kabusys.data import quality
  issues = quality.run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

注意:
- OpenAI を使う関数は API キーが必要です。引数で api_key を渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL の run_daily_etl は内部でカレンダーを取得し、それに基づいて営業日に調整して株価等を取得します。

---

## 環境変数（主要な一覧）

必須（利用する機能に依存）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- OPENAI_API_KEY

任意:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PID_FILE_PATH — default: data/execution.pid
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視の閾値

サンプル .env（最低限の例）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## ディレクトリ構成（主要ファイル）

（パッケージのルートは src/kabusys）

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py        — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース）
- src/kabusys/data/
  - __init__.py
  - pipeline.py        — ETL パイプライン（run_daily_etl 等）
  - jquants_client.py  — J-Quants API クライアント（取得・保存関数）
  - calendar_management.py — 市場カレンダー管理（営業日判定等）
  - quality.py         — データ品質チェック
  - etl.py             — ETL インターフェース（ETLResult の再輸出）
  - stats.py           — 共通統計ユーティリティ（zscore_normalize）
  - news_collector.py  — RSS 収集（SSRF 対策・前処理）
  - audit.py           — 監査ログテーブル DDL と初期化
- src/kabusys/research/
  - __init__.py
  - factor_research.py       — ファクター計算（momentum/value/volatility）
  - feature_exploration.py   — 将来リターン、IC、統計サマリー等

（上記以外に strategy / execution / monitoring 等のサブパッケージを __all__ で公開する設計です。コードベースに応じて追加されます。）

---

## 開発・運用上の注意

- DuckDB の executemany に空リストを渡せないバージョン依存の挙動に注意（コード中でガードあり）。
- OpenAI 呼び出しは JSON mode を利用し、レスポンスのバリデーションを厳密に行っています。API エラー時のフォールバックやリトライは実装されていますが、コストとレイテンシに注意してください。
- news_collector は RSS の URL 正規化／トラッキングパラメータ除去／SSRF 対策を実装していますが、外部フィードの整合性は各ソースに依存します。
- 本リポジトリはバックテストでのルックアヘッドバイアスを避ける設計を強く意識しています。バッチ処理やテスト時には target_date を明示的に指定して使用してください。
- 自動環境変数ロードは .git または pyproject.toml を基準にプロジェクトルートを探索して .env を読み込みます。CI／テスト等で読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

問題報告・貢献:
- バグや改善案は Issue を作成してください。Pull Request は歓迎します。設計方針に沿ったテストと docstring の更新をお願いします。

以上。README のサンプル実行コマンド・スニペットは実行環境の設定（API キー・ネットワーク）に依存します。必要であれば具体的なユースケース（ETL 周期化 cron / systemd / コンテナ化 / 発注フロー例）についての追記も作成します。