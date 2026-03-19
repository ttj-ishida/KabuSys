# KabuSys

日本株向けのデータプラットフォーム＋自動売買基盤のコアライブラリです。  
DuckDB をデータレイヤに使い、J-Quants から市場データ／財務データを取得して ETL → 特徴量作成 → シグナル生成までをサポートします。戦略層と実行（発注）層は分離された設計で、研究（research）用途のユーティリティも含まれます。

主な設計方針：
- ルックアヘッドバイアス防止（対象日時点までのデータのみを使用）
- 冪等性（DB への保存は ON CONFLICT / トランザクションで安全に）
- 外部発注 API への直接依存を限定し、戦略はテーブル操作で完結する

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理（.env 自動読み込み、必須環境変数チェック）
- J-Quants API クライアント
  - 株価日足（ページネーション対応・レートリミット・リトライ・トークン自動更新）
  - 財務データ取得
  - マーケットカレンダー取得
  - DuckDB への冪等保存ユーティリティ
- DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
- ETL パイプライン（差分更新・バックフィル・品質チェック呼び出し）
- 特徴量計算（momentum / volatility / value 等）と Z スコア正規化
- シグナル生成（複数コンポーネントの加重集約、Bear レジーム抑制、BUY/SELL 判定）
- ニュース収集（RSS → 前処理 → raw_news に保存・銘柄抽出）
- マーケットカレンダー管理（営業日判定、next/prev/trading days）
- 監査ログ / 発注トレース用スキーマ（audit）

---

## 要件

- Python 3.10+
- 必須パッケージ（例）:
  - duckdb
  - defusedxml
- 標準ライブラリの urllib, datetime, logging 等を多用

（pip 用の `pyproject.toml` / `requirements.txt` がある場合はそちらに従ってください）

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   - minimal:
     ```bash
     pip install duckdb defusedxml
     ```
   - パッケージとしてインストール可能ならプロジェクトルートで:
     ```bash
     pip install -e .
     ```

4. 環境変数設定
   - プロジェクトルート（.git や pyproject.toml があるフォルダ）に `.env` / `.env.local` を置くと自動読み込みされます（自動読み込みはデフォルト有効）。
   - 自動ロードを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須設定（例、.env に記載）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - （オプション）DUCKDB_PATH / SQLITE_PATH / KABUSYS_ENV / LOG_LEVEL

   - .env.example を参考に作成してください（プロジェクトに含めてある場合）。

---

## 初期化（DB スキーマ）

デフォルトの DuckDB パスは settings.duckdb_path（デフォルト: `data/kabusys.duckdb`）です。

Python REPL やスクリプトで初期化する例：
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照
conn = init_schema(settings.duckdb_path)
```

メモリ上 DB を使う場合:
```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
```

---

## 使い方（主要ユースケース）

以下は基本的な操作と関数の呼び方の例です。実運用ではログ出力やエラーハンドリング、ジョブスケジューラ（cron / airflow 等）と組み合わせます。

1) 日次 ETL（市場カレンダー・株価・財務の差分取得と品質チェック）
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量を作成（features テーブルへ書き込み）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

3) シグナル生成（signals テーブルへ書き込み）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {n}")
```

4) ニュース収集（RSS）と DB 保存
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# sources を指定可能。既定は Yahoo Finance のビジネス RSS 等
res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(res)
```

5) J-Quants からデータ直接取得→保存（例）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,2,1))
saved = jq.save_daily_quotes(conn, records)
print(f"saved {saved} rows")
```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン（必須）
- SLACK_CHANNEL_ID — 通知先チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB 等に使う SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 で無効）

config.Settings を通じてアプリケーションから参照できます（設定未提供時は ValueError が発生します）。

---

## 主要 API 概要

- kabusys.config.Settings — 環境変数からの設定取得（必須値チェック・デフォルト値）
- kabusys.data.jquants_client — J-Quants API のラッパー（fetch_* / save_*）
- kabusys.data.schema — DuckDB スキーマ定義・init_schema / get_connection
- kabusys.data.pipeline — ETL 実行エントリポイント（run_daily_etl, run_prices_etl, ...）
- kabusys.data.news_collector — RSS 取得/前処理/DB 保存（fetch_rss / save_raw_news / run_news_collection）
- kabusys.research.* — 研究用ユーティリティ（factor 計算、forward return、IC 等）
- kabusys.strategy.build_features — features テーブル作成
- kabusys.strategy.generate_signals — signals テーブルへシグナル出力

各関数はドキュメント文字列で引数・戻り値・挙動が詳細に記載されています。実装は DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を引数に取り、テストしやすい構成です。

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得＋保存）
    - news_collector.py            — RSS ニュース収集・保存
    - schema.py                    — DuckDB スキーマ定義・初期化
    - stats.py                     — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                  — ETL パイプライン
    - calendar_management.py       — マーケットカレンダー管理
    - features.py                  — データ用ユーティリティ公開
    - audit.py                     — 監査ログスキーマ
  - research/
    - __init__.py
    - factor_research.py           — momentum/value/volatility 計算
    - feature_exploration.py       — IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py       — features テーブル構築ワークフロー
    - signal_generator.py          — final_score 計算と signals 挿入
  - execution/                      — 発注・監視など（未詳細化ファイル群）
  - monitoring/                     — 監視用 DB / ロギング関連（未詳細化）

---

## 運用時の注意事項・設計上のポイント

- DuckDB へは冪等な INSERT（ON CONFLICT）を使うため、再実行しても重複しないよう設計されています。
- J-Quants API はレート制限 (120 req/min) に従うため内部でスロットリングしています。多数の並列リクエストは避けてください。
- システム環境（KABUSYS_ENV）に応じた実行制御（paper_trading / live）をコード側で参照可能です。実際の発注（execution 層）を組む際は is_live / is_paper フラグを活用してください。
- RSS ニュース収集では SSRF 対策、受信サイズ制限、gzip 解凍後のサイズ検査等の安全対策を実装しています。
- 自動 .env 読み込みはプロジェクトルート基準で行われます（.git または pyproject.toml を検出）。

---

## 貢献 / テスト

- 既存のモジュールは関数単位で DuckDB 接続を引数に取るため、:memory: DB を用いたユニットテストが容易です。
- KABUSYS_DISABLE_AUTO_ENV_LOAD をオンにして環境依存を切り離したテストを行ってください。
- 外部 API 呼び出し（jquants_client._request や _urlopen）等はモックしやすい構造にしています。

---

この README はコードの主要部分を抜粋してまとめた概要です。詳細な設計仕様（StrategyModel.md / DataPlatform.md / DataSchema.md）や .env.example、CI / デプロイ手順がプロジェクト内にある場合はそちらも参照してください。