# KabuSys — 日本株自動売買システム

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
データ取り込み（J-Quants）、ETL、特徴量生成、戦略シグナル生成、ニュース収集、監査ログなどを層別に実装しており、研究（research）→ 本番（execution）までのワークフローを想定しています。

主な設計方針:
- レイヤードアーキテクチャ（Raw / Processed / Feature / Execution）
- 冪等性（DB 保存は ON CONFLICT / upsert を多用）
- ルックアヘッドバイアス防止（時点データのみを使用）
- 外部 API 呼び出しは明示的に注入可能（テスト容易性）
- 最小限の外部依存（標準ライブラリ + 必要なパッケージ）

---

## 機能一覧

- J-Quants API クライアント（取得・リトライ・レート制御・トークン自動リフレッシュ）
  - 株価日足 / 財務データ / 市場カレンダーの取得・保存
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- DuckDB スキーマ定義と初期化（init_schema）
- ニュース収集（RSS → raw_news、URL 正規化、SSRF 防御、記事と銘柄の紐付け）
- 研究用モジュール（ファクター計算、将来リターン、IC, 統計サマリー）
- 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ、features テーブルへの UPSERT）
- シグナル生成（ファクター結合、AI スコア統合、BUY/SELL 生成、SELL 優先ポリシー）
- マーケットカレンダー管理（営業日判定、next/prev/get_trading_days）
- 監査ログ（signal_events, order_requests, executions 等の初期 DDL）

---

## 前提／必要環境

- Python 3.10+
- duckdb
- defusedxml（RSS パーシング用）
- 標準ライブラリ（urllib 等）を中心に実装

インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージを開発モードでインストールする場合
pip install -e .
```

（プロジェクトに requirements.txt がある場合はそれに従ってください）

---

## 環境変数（必須 / 任意）

自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須（実行に必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注連携を使う場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 実行モード: `development` / `paper_trading` / `live`（デフォルト: `development`）
- LOG_LEVEL — `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト: `INFO`）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite（デフォルト: `data/monitoring.db`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（値は任意）

.env の例（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=xxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. 仮想環境を作成・有効化
3. 依存パッケージをインストール（duckdb, defusedxml 等）
4. プロジェクトルートに `.env` を作成して必須環境変数を設定
5. DuckDB スキーマを初期化

DuckDB スキーマ初期化例:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数に基づくデフォルトパスを返します
conn = init_schema(settings.duckdb_path)
```

※ テスト用途ではインメモリ DB を使用できます:
```python
conn = init_schema(":memory:")
```

---

## 基本的な使い方（API 例）

日次 ETL を実行して features を作り、シグナルを生成する典型的なフロー:

```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from kabusys.strategy import build_features, generate_signals

# 1. DB 初期化（初回のみ）
conn = init_schema(settings.duckdb_path)

# 2. 日次 ETL（J-Quants からデータ取得して保存）
etl_result = run_daily_etl(conn, target_date=date.today())
print(etl_result.to_dict())

# 3. 特徴量生成
n_features = build_features(conn, target_date=date.today())
print(f"features upserted: {n_features}")

# 4. シグナル生成
num_signals = generate_signals(conn, target_date=date.today())
print(f"signals written: {num_signals}")
```

ニュース収集ジョブ（RSS）:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema(":memory:")  # または実 DB
known_codes = {"7203", "6758", "9984"}  # 銘柄抽出に使う既知コード集合
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

J-Quants クライアントを直接使う（テストで id_token を注入可能）:
```python
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
```

ETL のテスト時は id_token を呼び出し元で生成して inject することができます（get_id_token を直接呼ぶか、run_* 関数の id_token 引数に渡す）。

---

## テスト／デバッグのヒント

- DB を破壊したくない場合は ":memory:" を使って init_schema してください。
- 自動 .env ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- 外部 API 呼び出しは関数引数（id_token）で注入可能なので、モックを使って単体テストが可能です。
- ログレベルは `LOG_LEVEL` で制御できます。

---

## ディレクトリ構成（概要）

以下は主要なパッケージ / モジュール（src/kabusys 以下）の概観です。

- kabusys/
  - __init__.py
  - config.py                  — 環境変数・設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - schema.py                — DuckDB スキーマ定義と初期化
    - jquants_client.py        — J-Quants API クライアント（取得/保存関数）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - news_collector.py        — RSS ニュースの収集・保存・銘柄抽出
    - calendar_management.py   — 市場カレンダー更新 / 営業日ユーティリティ
    - features.py              — features 周りユーティリティ（再エクスポート）
    - stats.py                 — zscore_normalize 等の統計ユーティリティ
    - audit.py                 — 監査ログ用 DDL・初期化（signal_events 等）
    - quality.py               — （品質チェックモジュールが想定される）
    - pipeline.py              — ETL 実行ロジック
  - research/
    - __init__.py
    - factor_research.py       — momentum / volatility / value の計算
    - feature_exploration.py   — 将来リターン / IC / 要約統計
  - strategy/
    - __init__.py
    - feature_engineering.py   — features テーブル生成ロジック
    - signal_generator.py      — final_score から signals を生成
  - execution/
    - __init__.py              — 発注実行レイヤ（将来的に broker 統合）
  - monitoring/                — 監視・アラート用モジュール（別途実装）

（上記はソース内の主要ファイルに基づく簡略表示です）

---

## 開発・貢献

- バグ報告や機能要望は issue を立ててください。
- 単体テストは外部 API の呼び出し部分をモックして実行してください（id_token を注入可能な設計です）。
- DB 依存部分は :memory: を使うことで高速なテストが可能です。

---

## 参考（主要 API の一言説明）

- kabusys.config.settings — 環境設定（プロパティ経由で安全に取得）
- init_schema(db_path) — DuckDB スキーマを初期化して接続を返す
- run_daily_etl(conn, target_date, ...) — 日次 ETL（calendar / prices / financials + 品質チェック）
- build_features(conn, target_date) — features を計算・正規化して features テーブルへ upsert
- generate_signals(conn, target_date, threshold, weights) — signals テーブルへ BUY/SELL を出力
- jquants_client.fetch_* / save_* — API 取得・DB 保存のユーティリティ
- news_collector.fetch_rss / save_raw_news / run_news_collection — RSS 収集と DB 保存

---

必要であれば README にサンプル .env.example、CI やデプロイ手順、より詳細な API 使用例（関数ごとの引数説明）を追加できます。どの情報を優先して追記しますか？