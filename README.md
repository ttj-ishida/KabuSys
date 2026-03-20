# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
DuckDB をデータレイクとして用い、J-Quants API と RSS によるデータ収集、特徴量生成、シグナル作成、発注監査用スキーマなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とする Python モジュール群です。

- J-Quants API から株価・財務・市場カレンダーを取得して DuckDB に保存（差分 ETL、冪等保存）
- RSS からニュースを収集しニュース本文と銘柄紐付けを保存
- 各種ファクター（モメンタム／ボラティリティ／バリュー等）を計算し特徴量テーブルを生成
- 正規化済み特徴量と AI スコアを統合して売買シグナルを作成（BUY/SELL）
- 発注・約定・ポジション・監査ログ用のスキーマを提供
- 研究用ユーティリティ（IC 計算、将来リターン、統計要約 など）

設計方針としてルックアヘッドバイアスの排除、冪等性、トレーサビリティ、ネットワーク/SSRF 対策、API レート制御等を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（認証自動更新、リトライ、ページネーション、保存ユーティリティ）
  - pipeline: 差分 ETL（prices / financials / calendar）、日次 ETL 実行
  - schema: DuckDB スキーマ初期化（Raw / Processed / Feature / Execution 層）
  - news_collector: RSS 収集、前処理、raw_news 保存、銘柄抽出・紐付け（SSRF 対策、gzip/サイズ制限）
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - stats: Z スコア正規化など統計ユーティリティ
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン・IC・ファクターサマリー
- strategy/
  - feature_engineering: 研究で得た raw factor を正規化・フィルタして features テーブルへ保存
  - signal_generator: features と ai_scores を統合して final_score を算出、BUY/SELL シグナル生成
- config: .env 読み込み・環境変数管理（自動ロード・保護・必須チェック）
- audit: 発注から約定までの監査ログスキーマ（UUID トレーサビリティ）

---

## 必要条件 / 依存

最低限必要な Python パッケージ（プロジェクトに明記されたもの）：
- duckdb
- defusedxml

（実行環境やテスト内容により他パッケージが必要になる場合があります。requirements.txt がある場合はそちらを使用してください。）

ネットワークアクセス:
- J-Quants API（認証トークン必要）
- RSS フィード（ニュース収集）

---

## 環境変数（主なもの）

config.Settings により以下の環境変数が参照されます。README の例のように `.env` に設定してください。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注層を使う場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知連携がある場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID

オプション（デフォルトあり）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化したい場合は `1` を設定

注意: config モジュールはプロジェクトルート（.git または pyproject.toml）を検出して `.env` / `.env.local` を自動読み込みします。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例（.env.example）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトで requirements.txt があればそれを使用）

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成（上記例参照）

5. DuckDB スキーマ初期化
   - 以下の Python スクリプト/REPL を実行して DB を作成します。

例:
```python
from kabusys.data.schema import init_schema, get_connection, init_schema
from kabusys.config import settings

# デフォルトパスを使う場合
conn = init_schema(settings.duckdb_path)
# またはインメモリ（テスト用）
# conn = init_schema(":memory:")
```

---

## 使い方（主要なユースケース）

ここでは代表的な呼び出し例を示します。各関数は DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。

- 日次 ETL（市場カレンダー、株価、財務、品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量構築（strategy.build_features）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

- シグナル生成（strategy.generate_signals）
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {n}")
```

- RSS ニュース収集と銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"calendar rows saved: {saved}")
```

---

## 実装上の注意点 / 運用メモ

- DuckDB のパスは settings.duckdb_path で指定。デフォルトは `data/kabusys.duckdb`。
- J-Quants の API レート制限（120 req/min）を内部でスロットリングしていますが、大量並列実行は避けてください。
- jquants_client は 401 を検知すると自動でリフレッシュトークンを使い ID トークンを更新します。
- news_collector は SSRF 対策（スキーム検証、プライベートアドレス拒否、gzip/サイズ上限）を実装しています。
- features / signals の処理はルックアヘッドバイアス回避のため target_date 時点のデータのみを参照するよう設計されています。
- schema.init_schema は冪等的にテーブル作成を行います。既存 DB を上書きしません（ただしスキーマ互換性は確認してください）。
- 環境変数の自動読み込みはプロジェクトルート検出に依存し、テスト時などで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュールとファイル構成の抜粋です。

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - calendar_management.py
    - features.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/  (モニタリング用モジュール等を想定)

（上記構成は現在の実装ファイル群に基づく抜粋です）

---

## 開発・テスト

- 単体テストや CI の設定があればそれに従ってください。テストで環境変数の自動読み込みが干渉する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用してください。
- DB を破壊するテストは必ずインメモリ (`":memory:"`) で行うことを推奨します。

---

## ライセンス / 貢献

このリポジトリのライセンス・貢献ガイドラインはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

必要であれば README に以下を追記できます：
- 詳しい .env.example（全キーの説明）
- CLI ラッパー（もし存在すれば）
- 具体的な ETL スケジュール例（cron / Airflow）
- 運用時の Slack 通知例

追加で記載したい項目や、サンプルスクリプトを README に含めたい場合は教えてください。