# KabuSys

日本株向け自動売買プラットフォームのライブラリ群（分析・ETL・特徴量生成・シグナル生成・データ収集など）。  
このリポジトリは戦略研究・データパイプライン・発注管理を分離した3層設計（Raw / Processed / Feature + Execution）で実装されています。

バージョン: 0.1.0

---

## 概要

KabuSys は次の要素を提供します。

- J-Quants API から株価・財務・カレンダーを取得するクライアント（rate limit / retry / token refresh 対応）
- RSS によるニュース収集と銘柄抽出（SSRF対策・トラッキングパラメータ除去）
- DuckDB ベースのスキーマ定義と初期化ユーティリティ
- ETL パイプライン（差分取得・バックフィル・品質チェックフック）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ・features テーブルへの保存）
- シグナル生成（特徴量 + AIスコア統合 → BUY/SELL の決定）
- カレンダー管理・監査ログ・実行層（テーブル定義）などの補助機能
- 環境変数ベースの設定管理（.env 自動ロード対応）

設計方針としては「ルックアヘッドバイアスの排除」「冪等性（DB挿入は ON CONFLICT）」「API 利用に伴う実用的な堅牢性（レート制御・リトライ）」を重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API からのデータ取得（daily quotes / financial statements / market calendar）
  - 保存関数（DuckDB への冪等保存: raw_prices / raw_financials / market_calendar）
- data/news_collector.py
  - RSS フィード取得・前処理・raw_news 保存・記事→銘柄紐付け
  - SSRF / xml 攻撃対策、受信サイズ制限
- data/schema.py
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema() で DB を初期化
- data/pipeline.py
  - 差分取得・バックフィルを行う日次 ETL（run_daily_etl）
- data/calendar_management.py
  - market_calendar の管理と営業日判定ユーティリティ
- research/factor_research.py / feature_exploration.py
  - モメンタム・ボラティリティ・バリューなどのファクター計算
  - 将来リターン計算、IC（Spearman ρ）や統計サマリー
- strategy/feature_engineering.py
  - 生ファクターの正規化、ユニバースフィルタ、features テーブルへの upsert
- strategy/signal_generator.py
  - features + ai_scores を統合して final_score を算出、BUY/SELL シグナル生成
- config.py
  - 環境変数読み込み（.env 自動ロード）および settings オブジェクト

---

## 必要条件

- Python >= 3.10（Union 型のパイプ構文などを使用）
- 必須ライブラリ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード など）

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# またはプロジェクトに requirements.txt があれば:
# pip install -r requirements.txt
```

---

## 環境変数（.env）

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます。無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:

- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabuステーション API パスワード（実行層で必要）
- KABU_API_BASE_URL      : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID       : Slack 送信先チャンネル ID（必須）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              : ログレベル（DEBUG/INFO/...）

例（.env）:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化
2. 必要パッケージをインストール（duckdb, defusedxml 等）
3. プロジェクトルートに `.env` を作成（上記の環境変数を設定）
4. DuckDB のスキーマ初期化:

Python REPL またはスクリプトで:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # :memory: も可
```

---

## 使い方（代表的な API）

- 日次 ETL（市場カレンダー→株価→財務→品質チェック）:

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量構築:

```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"features updated: {n}")
```

- シグナル生成:

```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date.today())
print(f"signals written: {count}")
```

- RSS ニュース収集:

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes = set([...]) を渡すと本文から銘柄抽出を行い news_symbols へ保存
res = run_news_collection(conn)
print(res)
```

- カレンダー更新ジョブ:

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("market_calendar saved:", saved)
```

- 設定参照:

```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント + 保存
    - news_collector.py              — RSS ニュース収集・保存
    - schema.py                      — DuckDB スキーマ定義・init_schema
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - features.py                    — 再エクスポート（zscore_normalize）
    - calendar_management.py         — market_calendar 管理・営業日ロジック
    - audit.py                       — 監査ログ用 DDL（signal_events 等）
    - pipeline.py (ETL)              — 差分更新・quality チェック呼び出し
  - research/
    - __init__.py
    - factor_research.py             — ファクター計算（mom/vol/value）
    - feature_exploration.py         — IC/forward returns/summary
  - strategy/
    - __init__.py
    - feature_engineering.py         — features 作成（正規化 / ユニバース）
    - signal_generator.py            — final_score 計算 / signals 書き込み
  - execution/                       — 発注・実行関連（初期ファイル）
  - その他（monitoring 等）

---

## 補足・運用上の注意

- DuckDB ファイルは durable なパス（例: data/kabusys.duckdb）を指定してください。初回実行で親ディレクトリが自動作成されます。
- J-Quants のレート制限・認証エラーやネットワーク障害に耐える設計ですが、実運用では API キー管理やリトライポリシーの監視を推奨します。
- 実際の発注を行う execution 層を稼働させる際は、KABU_API_PASSWORD と KABU_API_BASE_URL を適切に設定し、paper_trading 環境で入念にテストしてください（settings.is_paper / is_live を利用）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を探索）から行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を推奨します。

---

必要に応じて README にコマンド例や CI・デプロイ手順、要求パッケージ一覧（requirements.txt）を追加することをお勧めします。必要であればその草案も作成します。