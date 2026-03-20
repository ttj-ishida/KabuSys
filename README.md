# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリ群です。  
データ収集（J-Quants）、ETL、特徴量生成、戦略シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含む三層（Raw / Processed / Feature）設計に基づくモジュール群を提供します。

主な目的は「研究（research）で設計したファクター・モデルを、データ基盤・戦略・発注フローへとつなぐこと」です。発注（execution）実装は分離されており、戦略モジュールは発注層に直接依存しません。

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（ページネーション・レート制限・トークン自動リフレッシュ・保存関数）
  - RSS ベースのニュース収集（SSRF・XML脆弱性対策・トラッキングパラメータ除去）
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution レイヤ）
- ETL / Data Pipeline
  - 差分取得（最終取得日に基づく差分）、バックフィル、品質チェック統合
  - 日次 ETL エントリポイント（run_daily_etl）
- 研究・特徴量
  - ファクター計算（モメンタム / バリュー / ボラティリティ / 流動性）
  - Z スコア正規化ユーティリティ
  - 将来リターン・IC・統計サマリ（research 用ユーティリティ）
- 戦略
  - 特徴量組成（build_features）：research で計算した raw factor を正規化し features テーブルへ保存
  - シグナル生成（generate_signals）：features と ai_scores を統合して BUY/SELL シグナルを生成、signals テーブルへ保存
- カレンダー管理
  - JPX マーケットカレンダーの更新・営業日判定・next/prev_trading_day 等のユーティリティ
- 監査・実行ログ（audit）
  - signal_events / order_requests / executions など、トレーサビリティ用テーブル定義
- ユーティリティ
  - 統計関数、URL 正規化、銘柄コード抽出など

---

## 必要条件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

（プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

インストール例（開発環境）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# パッケージ配布を使う場合:
# pip install -e .
```

---

## 環境変数 / 設定

自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（OS 環境変数が優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（get_id_token で使用）
  - KABU_API_PASSWORD: kabu ステーション API のパスワード（発注統合時）
  - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
  - SLACK_CHANNEL_ID: Slack チャンネル ID
- 任意（デフォルトあり）
  - KABUSYS_ENV: environment（development / paper_trading / live、デフォルト `development`）
  - LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL。デフォルト `INFO`）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
  - SQLITE_PATH: SQLite（監視用 DB）パス（デフォルト `data/monitoring.db`）

例 `.env`:

```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（概要）

1. リポジトリをクローンして仮想環境を作成
2. 依存パッケージをインストール（duckdb, defusedxml 等）
3. `.env` を作成して必要な環境変数を設定
4. DuckDB スキーマを初期化

例（Python スクリプトで初期化）:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は .env の DUCKDB_PATH の値を参照
conn = init_schema(settings.duckdb_path)
print("DuckDB initialized:", settings.duckdb_path)
```

または shell から直接:

```bash
python -c "from kabusys.config import settings; from kabusys.data.schema import init_schema; init_schema(settings.duckdb_path)"
```

---

## 使い方（代表的な API）

以下は代表的な利用例です。詳細は各モジュールの docstring を参照してください。

- 日次 ETL を実行（J-Quants から差分取得して保存 + 品質チェック）:

```python
from datetime import date
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")  # 初回のみ
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量ビルド（features テーブルへ保存）:

```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print("features upserted:", count)
```

- シグナル生成（signals テーブルへ保存）:

```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date.today(), threshold=0.6)
print("signals written:", total)
```

- RSS ニュース収集と銘柄紐付け:

```python
from kabusys.data.news_collector import run_news_collection
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# known_codes は抽出対象の有効な銘柄コード集合（例: set of "7203","6758",...）
results = run_news_collection(conn, known_codes={"7203","6758"})
print(results)
```

- カレンダー夜間更新ジョブ:

```python
from kabusys.data.calendar_management import calendar_update_job
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

- J-Quants からのデータ取得（低レベル）:

```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from kabusys.config import settings

token = get_id_token()  # settings.jquants_refresh_token を使って id_token を取得
quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date.today())
```

---

## 注意事項 / 運用上のポイント

- 環境（KABUSYS_ENV）は `development`, `paper_trading`, `live` のいずれかに設定してください。`live` 時は特に発注処理周り・ログおよび安全チェックを厳重に行ってください。
- 自動的に .env をロードしますが、CI やテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して制御できます。
- J-Quants API はレート制限が厳しいため、jquants_client は内部で固定間隔スロットリングとリトライを実装しています。大規模収集時は API 制限を意識してください。
- DuckDB のスキーマ初期化は冪等です。既存テーブルがあれば上書きしません。
- ニュース収集には外部 HTTP/リダイレクトの安全性対策（SSRF 防止）と XML パーサー保護（defusedxml）を組み込んでいます。

---

## ディレクトリ構成

リポジトリの主要ファイル/ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存）
    - news_collector.py       — RSS ニュース収集・保存
    - schema.py               — DuckDB スキーマ定義・初期化
    - stats.py                — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  — カレンダー管理・更新ジョブ
    - audit.py                — 監査ログ DDL 定義
    - features.py             — data 層の特徴量ユーティリティ公開
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py  — features テーブル構築（正規化等）
    - signal_generator.py     — final_score 計算・シグナル生成
  - execution/                — 発注関連（未詳細実装）
  - monitoring/               — 監視/メトリクス（未詳細実装）

上記はコードベースに含まれる主要モジュールです。各ファイルに詳細な docstring があり、関数単位での使い方や設計意図が記載されています。

---

## 開発・拡張ガイド

- 新しいファクターを追加する場合は `kabusys.research.factor_research` に関数を追加し、`kabusys.strategy.feature_engineering.build_features` で組み合わせて features テーブルに反映してください。
- 発注周り（execution 層）を組み込む際は、strategy 層は発注 API に直接依存しない設計を維持し、signals → signal_queue → execution のフローで冪等性と監査を確保してください。
- テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD` と `jquants_client` の HTTP 呼び出しをモックして決定論的に実行してください。

---

## 最後に

この README はコード内の docstring を基に要点をまとめたものです。詳細な利用方法・設計仕様（StrategyModel.md / DataPlatform.md / DataSchema.md 等）がプロジェクト内にあればそちらも参照してください。質問や補足したい点があれば教えてください。