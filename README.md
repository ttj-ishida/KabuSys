# KabuSys

日本株向けの自動売買/データ基盤ライブラリです。J-Quants から市場データを取得して DuckDB に保存し、研究で得られた生ファクターを正規化・合成して戦略シグナルを生成、発注ログ・監査ログを保持するためのユーティリティ群を提供します。

主な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「API レート制御」「トレーサビリティの確保」です。

バージョン: 0.1.0

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価日足 / 財務データ / 市場カレンダー）
  - 差分ETLパイプライン（バックフィル、品質チェックを含む）
  - DuckDB スキーマ初期化および idempotent 保存（ON CONFLICT）
- データ加工・統計
  - ファクター計算（Momentum / Volatility / Value / Liquidity 等）
  - Z スコア正規化ユーティリティ
  - 将来リターン・IC 計算などの研究用ユーティリティ
- 特徴量・シグナル生成
  - features テーブル構築（正規化、ユニバースフィルタ適用）
  - AI スコア統合による final_score 計算と BUY/SELL シグナル生成
  - エグジット判定（ストップロス等）
- ニュース収集
  - RSS フィード収集（SSRF 対策、XML 攻撃対策、トラッキング除去）
  - raw_news, news_symbols への冪等保存
- カレンダー管理
  - JPX 市場カレンダー更新ジョブ、営業日判定ユーティリティ
- 監査・実行層
  - signals / signal_queue / order_requests / executions / positions 等のスキーマ
  - 監査ログ（signal_events / order_requests / executions）によるトレーサビリティ

---

## 要件

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - defusedxml

（上記は最低限。利用する機能や実行環境に応じて追加パッケージが必要になることがあります。）

---

## セットアップ手順

1. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. パッケージインストール
   最低限:
   ```bash
   pip install duckdb defusedxml
   ```
   （プロジェクトに requirements.txt がある場合はそれを利用してください。）

3. 環境変数の準備
   プロジェクトルートに `.env` / `.env.local` を置いて環境変数を設定します。自動ロード機能が有効（デフォルト）なため、pyproject.toml か .git があるルートを起点に `.env` が読み込まれます。

4. DuckDB スキーマ初期化（例）
   下記の使い方例にあるように `kabusys.data.schema.init_schema()` を呼び出して DB を作成します。

注意: テスト時など自動で .env を読み込ませたくない場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数

以下は主要な設定項目（必須 = 必ず設定が必要）:

- J-Quants
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略可, デフォルト: http://localhost:18080/kabusapi)
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベース
  - DUCKDB_PATH (省略可, デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (省略可, デフォルト: data/monitoring.db)
- システム
  - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO

必須環境変数が未設定の場合、`kabusys.config.settings` のアクセサ（例: settings.jquants_refresh_token）が ValueError を投げます。`.env.example` を作成して管理してください。

---

## 使い方（サンプル）

以下は主要なユースケースの簡単な例です。詳細はコードの docstring を参照してください。

- DuckDB スキーマの初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ファイルを自動作成
  ```

- 日次 ETL の実行（J-Quants から差分取得）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量（features）テーブルの構築
  ```python
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, target_date=date.today())
  print(f"features updated: {count}")
  ```

- シグナル生成
  ```python
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date.today(), threshold=0.60)
  print(f"signals generated: {total}")
  ```

- ニュース収集ジョブ（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=None, known_codes=set(["7203", "6758"]))
  print(results)
  ```

- カレンダー更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

注意点:
- すべての処理は DuckDB 接続を受け取る形なので、テスト時は in-memory DB (`":memory:"`) を使うと便利です。
- ETL や API 呼び出しはネットワーク・外部 API に影響されるため、実行環境のトークンやネットワーク設定に注意してください。
- 環境に応じて `KABUSYS_ENV` を `paper_trading` / `live` に切り替えて運用ポリシーを分離してください。

---

## ディレクトリ構成

主要ファイルとディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存）
    - news_collector.py        — RSS ニュース収集・保存
    - pipeline.py              — ETL パイプライン（差分更新 / 品質チェック）
    - schema.py                — DuckDB スキーマ定義 & 初期化
    - stats.py                 — 統計ユーティリティ（zscore_normalize 等）
    - features.py              — data.stats の再エクスポート
    - calendar_management.py   — 市場カレンダー管理
    - audit.py                 — 発注〜約定の監査ログスキーマ
    - execution/               — 発注実行層（空パッケージ、将来的に実装）
  - research/
    - __init__.py
    - factor_research.py       — ファクター計算（momentum/volatility/value）
    - feature_exploration.py   — 研究用ユーティリティ（IC / forward returns 等）
  - strategy/
    - __init__.py
    - feature_engineering.py   — features テーブル作成ロジック
    - signal_generator.py      — final_score 計算 & signals 生成
  - monitoring/                — 監視用 DB/ロジック（別途実装想定）

（上記は現状コードベースに基づく主要構成。将来的な拡張により変化します。）

---

## 開発・運用上の注意

- トークンやパスワードは .env に保存し、ソース管理には含めないでください。
- J-Quants API のレート制限（120 req/min）に準拠する実装が組み込まれていますが、運用時はさらにバックオフやキューイングなどの工夫を検討してください。
- DuckDB のバージョンや SQL 機能に依存する箇所があるため、動作確認時は使用する DuckDB のバージョンを揃えてください。
- ニュース収集では外部 URL の検証（SSRF 対策）や XML の防御（defusedxml）を実装していますが、外部 RSS の変更や特殊フィードには注意してください。
- 本リポジトリは研究・検証用コードとプロダクション想定の処理が混在しています。実際の資金を扱う場合は十分な監査・テスト・リスク管理を行ってください。

---

以上が README の概要です。追加で「使い方の具体的な CLI」「requirements.txt の生成」「運用例（Airflow ジョブ定義 等）」を記載したい場合は、必要なフォーマットや要件を教えてください。