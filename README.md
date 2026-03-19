# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。J-Quants API 等からマーケットデータ・財務データ・ニュースを収集して DuckDB に格納し、研究用ファクター計算、特徴量生成、シグナル生成、発注/監査用スキーマなどを提供します。

## プロジェクト概要

KabuSys は次のレイヤーで構成される自動売買基盤のコア部分を提供します。

- Data（取得・ETL）: J-Quants からの株価・財務・カレンダー・RSS 取得、DuckDB スキーマ定義、ETL パイプライン
- Research（リサーチ）: ファクター計算、特徴量解析、IC 計算等の研究向けユーティリティ
- Strategy（戦略）: 特徴量の正規化・統合およびシグナル生成ロジック
- Execution（発注）: 発注・約定・ポジション・監査を扱うスキーマ／モジュール（骨格）

設計上のポリシー:
- ルックアヘッドバイアスの排除（target_date 時点の情報のみ使用）
- 冪等性（DB への保存は ON CONFLICT / トランザクション を利用）
- 外部依存を最小化（多くの処理は標準ライブラリ + DuckDB で完結）
- セキュリティ配慮（RSS の SSRF 対策、XML パースの安全化、API レート／リトライ管理）

## 主な機能一覧

- DuckDB スキーマ定義と初期化（data.schema.init_schema）
- J-Quants API クライアント（rate limiting / retry / token refresh 対応）
  - 日足価格取得 / 財務データ取得 / 市場カレンダー取得
- ETL パイプライン（差分取得、backfill、品質チェック）
  - run_daily_etl による日次 ETL（カレンダー→価格→財務→品質チェック）
- ファクター計算（momentum / volatility / value 等）
- 特徴量生成（正規化・ユニバースフィルタ・features テーブルへの upsert）
- シグナル生成（複数コンポーネントの重み付き統合、BUY/SELL 生成）
- ニュース収集（RSS フィード取得、SSRF 対策、記事正規化、銘柄抽出・保存）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査テーブル（signal/order/execution のトレーサビリティ骨格）

## 前提（依存関係）

最低限必要なライブラリ（pip）:
- duckdb
- defusedxml

その他は標準ライブラリのみで動作する部分が多いですが、実行環境に応じて追加パッケージが必要になる可能性があります。

例:
```
pip install duckdb defusedxml
```

プロジェクトをパッケージとして使う場合:
```
pip install -e .
```

## セットアップ手順

1. リポジトリをクローン／取得する。

2. 依存ライブラリをインストール:
   ```
   pip install -r requirements.txt   # あれば
   # or
   pip install duckdb defusedxml
   ```

3. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（使用する場合）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意・デフォルト
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/…（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視系 SQLite（デフォルト: data/monitoring.db）

   .env の簡易例:
   ```
   JQUANTS_REFRESH_TOKEN=xxx
   KABU_API_PASSWORD=yyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマを初期化
   Python REPL やスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # または ":memory:"
   ```

## 使い方（代表的な例）

以下は簡単な実行フロー例です。実稼働ではログ設定や例外処理、スケジューラ（cron / Airflow 等）を組み合わせてください。

- 日次 ETL 実行（市場カレンダー・価格・財務を差分取得して保存）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（初回）
conn = init_schema("data/kabusys.duckdb")

# ETL 実行（今日）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量作成
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

- シグナル生成
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date.today())
print(f"signals generated: {total}")
```

- ニュース収集（RSS → raw_news 保存 → news_symbols 紐付け）
```python
from kabusys.data.jquants_client import save_market_calendar  # ではなく news_collector を利用
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
res = run_news_collection(conn, sources=None, known_codes=None)
print(res)
```

- カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

## 主要 API の説明（抜粋）

- data.schema.init_schema(db_path) — DuckDB にスキーマを作成して接続を返す。
- data.pipeline.run_daily_etl(conn, target_date, ...) — 日次 ETL 実行。ETLResult を返す。
- data.jquants_client.fetch_* / save_* — J-Quants から取得・DuckDB へ保存する低レイヤ関数。
- research.calc_momentum / calc_volatility / calc_value — ファクター計算（prices_daily / raw_financials を参照）。
- strategy.build_features(conn, target_date) — features テーブルに特徴量を構築・保存。
- strategy.generate_signals(conn, target_date, threshold, weights) — signals テーブルへ BUY/SELL を書き込む。
- data.news_collector.run_news_collection(conn, sources, known_codes) — RSS 収集と保存。

## ローカル開発・テストのヒント

- テスト実行時に自動で .env を読み込ませたくない場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- 単体テストでは DuckDB のインメモリモードを使うと早く独立してテストできます:
  ```python
  conn = init_schema(":memory:")
  ```
- RSS 取得や HTTP 通信部分は関数単位でモック可能（例: news_collector._urlopen, jquants_client._request など）。

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動読み込み・設定クラス
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存関数含む）
    - news_collector.py — RSS 収集・正規化・保存
    - schema.py — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダー管理
    - features.py — data.stats の再エクスポート
    - audit.py — 監査ログテーブル定義（signal/order/execution の監査）
  - research/
    - __init__.py
    - factor_research.py — momentum/volatility/value の計算
    - feature_exploration.py — IC / forward returns / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py — features 作成ロジック
    - signal_generator.py — final_score 計算と signals 作成
  - execution/ — 発注関連（パッケージの骨組み）
  - monitoring/ — 監視・メトリクス関連（パッケージの骨組み）

（ファイル名は主要モジュールを抜粋しています。実際のリポジトリでは追加のユーティリティやテストコードが存在する可能性があります。）

## 注意事項 / 運用上のポイント

- 環境変数の管理は慎重に（API トークンやパスワードを漏洩しないこと）。
- J-Quants の API レート制限やリトライ仕様は jquants_client に実装されていますが、大量リクエスト時は外部制御（キューやバッチ化）を検討してください。
- DuckDB のファイルバックアップ・スナップショット運用を推奨します（データが破損すると再構築コストが高い）。
- 実稼働（ライブ口座）環境では KABUSYS_ENV を `live` にして安全対策（送金・発注ロギング、権限管理）を厳格にしてください。

---

ご希望があれば README に CI / テスト実行方法、より詳しい .env.example、サンプル SQL や Airflow / cron による運用例を追記します。