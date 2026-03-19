# KabuSys

日本株向けの自動売買／データパイプライン基盤ライブラリです。J-Quants API などから市場データを取得して DuckDB に格納し、リサーチ／特徴量生成、シグナル作成、ニュース収集、発注監査ログまでのワークフローをサポートします。

主な設計方針
- ルックアヘッドバイアス回避（target_date 時点のデータのみを使用）
- DuckDB を中心としたローカル DB（冪等な INSERT/UPSERT）
- 外部依存を最小限にし、標準ライブラリ＋必要な最小パッケージで実装
- API レート制御・リトライ・安全対策（SSRF 対策、XML defuse 等）

バージョン: 0.1.0

---

## 機能一覧

- データ取得・保存
  - J-Quants から日次株価（OHLCV）、財務データ、マーケットカレンダーを取得（jquants_client）
  - 取得データを raw テーブルに冪等保存（ON CONFLICT / upsert）
- ETL パイプライン（差分更新）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（data.pipeline）
  - 品質チェックフック（quality モジュールと連携）
- スキーマ管理
  - DuckDB スキーマ初期化（data.schema.init_schema）
  - 各層のテーブル定義（Raw / Processed / Feature / Execution / Audit）
- 特徴量計算・正規化（strategy / research）
  - ファクター計算（momentum / volatility / value）（research.factor_research）
  - Zスコア正規化ユーティリティ（data.stats）
  - ファクター合成 → features テーブルへの UPSERT（strategy.feature_engineering.build_features）
- シグナル生成（strategy.signal_generator）
  - features / ai_scores / positions を用いて final_score を計算
  - BUY / SELL シグナルの生成と signals テーブルへの保存（冪等）
  - Bear レジーム抑制、ストップロス等のエグジット判定を実装
- ニュース収集（data.news_collector）
  - RSS フィード取得・前処理・raw_news への冪等保存
  - 記事から銘柄コード抽出、news_symbols への紐付け
  - SSRF / XML Bomb / 大容量応答対策を実装
- 監査ログ（data.audit）
  - signal → order_request → executions までのトレース可能な監査テーブル群

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 記法等を使用）
- pip が利用可能

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   必要最低限:
   - duckdb
   - defusedxml
   ```
   pip install duckdb defusedxml
   ```

   （プロジェクトに requirements.txt がある場合はそちらを使用してください）

4. 環境変数 / .env の準備
   必須環境変数（本番実行に必要）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD      : kabu API パスワード（発注連携する場合）
   - SLACK_BOT_TOKEN        : Slack 通知に使う Bot トークン
   - SLACK_CHANNEL_ID       : Slack チャネル ID

   その他オプション:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db

   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動読み込みを無効化できます）。

---

## 使い方（主要な操作例）

以下はライブラリの主要 API を使った簡単な利用方法例です。実際の運用ではログ設定や例外処理、スケジューラ（cron / Airflow 等）での呼び出しを組み合わせてください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化（親ディレクトリは自動作成される）
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) ニュース収集ジョブ実行（RSS から raw_news へ）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes を渡すと記事から銘柄抽出して news_symbols に紐付けする
known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄セット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

4) 特徴量の構築（features テーブルに保存）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2025, 3, 15))
print(f"features upserted: {count}")
```

5) シグナル生成（signals テーブルに保存）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
total_signals = generate_signals(conn, target_date=date(2025, 3, 15))
print(f"signals generated: {total_signals}")
```

6) スキーマや ETL を組み合わせたワークフロー（簡易）
- 夜間: calendar_update_job → run_daily_etl（市場データ更新）
- 朝: build_features → generate_signals → signal_queue / execution 層へ送出
- 随時: run_news_collection（ニュース→AI解析→ai_scores に反映）

---

## 環境変数の自動読み込みについて

- パッケージはプロジェクトルート（.git または pyproject.toml が存在する場所）を基準に `.env` と `.env.local` を自動で読み込みます。
- 読み込み順序（優先度）:
  1. OS 環境変数
  2. .env.local（上書き）
  3. .env
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

必須値が不足している場合は Settings プロパティから例外が発生します（例: settings.jquants_refresh_token が未設定だと ValueError が投げられます）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境設定 / .env 自動読み込み / Settings
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存関数）
    - news_collector.py — RSS ニュース収集・保存
    - schema.py — DuckDB スキーマ定義 & init_schema / get_connection
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - pipeline.py — 日次 ETL（run_daily_etl, run_prices_etl 等）
    - calendar_management.py — カレンダー更新 / 営業日判定ユーティリティ
    - features.py — features ヘルパ（zscore 再エクスポート）
    - audit.py — 監査ログテーブル定義
    - (その他: quality, execution 用の補助モジュール 等 想定)
  - research/
    - __init__.py
    - factor_research.py — momentum / value / volatility 等のファクター計算
    - feature_exploration.py — forward returns, IC, 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features 作成（build_features）
    - signal_generator.py — generate_signals（BUY/SELL 判定）
  - execution/  （発注や broker 連携はここに実装する想定）
  - monitoring/  （監視・アラート用のコードを想定）

（実際のファイル群はリポジトリのソースを参照してください）

---

## 開発・運用上の注意

- Python バージョン: 3.10 以上を推奨（| 型注釈等を使用）
- DuckDB: ファイル DB（デフォルト data/kabusys.duckdb）を使う場合はバックアップや権限設定に注意
- J-Quants API レート制限（120 req/min）に従って RateLimiter を適用済み
- ニュース収集では SSRF、XML インジェクション、Gzip/応答サイズ制限等の防御を実装
- ETL/ジョブは外部ネットワークに依存するため、リトライや適切な監視を組み合わせて運用してください
- 学習用や検証環境では KABUSYS_ENV=development を用い、paper_trading/live の切替は慎重に行ってください

---

## 参考: 主要 API（抜粋）

- Settings
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.kabu_api_base_url, settings.duckdb_path, settings.env など

- スキーマ初期化
  - from kabusys.data.schema import init_schema, get_connection

- ETL
  - from kabusys.data.pipeline import run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl

- データ取得・保存
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, fetch_financial_statements, ...

- ニュース
  - from kabusys.data.news_collector import fetch_rss, save_raw_news, run_news_collection

- リサーチ / 特徴量
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

- 戦略
  - from kabusys.strategy import build_features, generate_signals

---

## ライセンス / 貢献

（ここにプロジェクト固有のライセンス・コントリビュート手順を追加してください）

---

README の内容はコードベースの現状に合わせて更新してください。追加で「運用例」「CI/CD 設定」「監視ダッシュボード」「実証実験（backtest）手順」などの章が必要であれば、要件に合わせて追記します。