# KabuSys

日本株向けの自動売買システム用ライブラリ（KabuSys）。  
市場データの取得・ETL、ファクター計算、特徴量生成、シグナル生成、ニュース収集、監査ログ等を含むデータ・戦略基盤を提供します。

---

## プロジェクト概要

KabuSys は次のレイヤーを想定したモジュール群を提供します。

- Data Layer（data/）: J-Quants など外部APIからの生データ取得、DuckDB スキーマ、ETL パイプライン、ニュース収集、カレンダー管理、品質チェック。
- Research Layer（research/）: ファクター計算・探索（モメンタム、ボラティリティ、バリュー等）、IC・統計サマリ。
- Feature / Strategy（strategy/）: ファクターを正規化して特徴量を作成（features テーブルへ保存）、特徴量と AI スコアを組み合わせて売買シグナルを生成。
- Execution（execution/）: 発注/約定/ポジション管理用テーブル・ユーティリティ（モジュール雛形）。
- Monitoring（monitoring）: 監視・通知用の入口（Slack 等）を想定（実装箇所あり）。

設計の基本方針として、「ルックアヘッドバイアスの排除」「DuckDB を用いた冪等な保存」「外部依存最小化（可能な限り標準ライブラリ）」「API レート制御とリトライ」「トレーサビリティ（監査ログ）」を採用しています。

---

## 主な機能一覧

- J-Quants API クライアント（取得、トークンリフレッシュ、ページング、レート制御、保存用ユーティリティ）
  - fetch_daily_quotes / save_daily_quotes
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
- DuckDB スキーマ定義・初期化
  - init_schema / get_connection
- ETL パイプライン
  - run_daily_etl（カレンダー→株価→財務→品質チェック）
  - run_prices_etl, run_financials_etl, run_calendar_etl
- ニュース収集（RSS）
  - fetch_rss, save_raw_news, run_news_collection
  - トラッキングパラメータ除去、SSRF対策、gzip サイズチェック、記事IDは正規化URLのSHA-256
- ファクター計算（Research）
  - calc_momentum, calc_volatility, calc_value
  - 将来リターン calc_forward_returns、IC 計算 calc_ic、統計サマリ factor_summary
- 特徴量作成（Strategy）
  - build_features（Zスコア正規化、ユニバースフィルタ、features テーブルへUPSERT）
- シグナル生成（Strategy）
  - generate_signals（特徴量と ai_scores を統合して final_score を計算、BUY/SELL シグナル生成、signals テーブルへUPSERT）
- 統計ユーティリティ
  - zscore_normalize 等
- 監査ログ（audit モジュール）
  - signal_events / order_requests / executions 等のテーブル定義（トレーサビリティ）

---

## 必要条件（主な依存）

- Python >= 3.10（PEP 604 の型注釈などを使用）
- duckdb
- defusedxml
- （標準ライブラリ: urllib, datetime, logging, math 等）

pip インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージを開発インストールする場合:
# pip install -e .
```

---

## 環境変数 / 設定

設定は環境変数、またはプロジェクトルートに配置した `.env` / `.env.local` から自動読み込みされます（自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須の環境変数（Settings により参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャネルID（必須）

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視DB 等）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）

注意: Settings クラスは未定義の必須環境変数があれば ValueError を送出します。

例 .env:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=~/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（例）

1. リポジトリをクローンし、仮想環境を作成・有効化。
2. 必要なパッケージをインストール（duckdb, defusedxml など）。
3. プロジェクトルートに `.env` を作成して必要な環境変数を設定。
4. DuckDB スキーマを初期化。

Python REPL またはスクリプト例:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は .env の DUCKDB_PATH を参照（未設定なら data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)  # ファイルとディレクトリを自動作成し、テーブルを作成します
```

テスト用にインメモリ DB を使う場合:
```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
```

---

## 使い方（主要ユースケースの例）

1) 日次 ETL（J-Quants から差分取得して保存 → 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量（features）を作成
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

3) シグナルを生成
```python
from datetime import date
from kabusys.strategy import generate_signals

conn = get_connection(settings.duckdb_path)
total = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {total}")
```

4) ニュース収集ジョブ（既知銘柄リストを渡して銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection(settings.duckdb_path)
known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

5) J-Quants から外部データを直接取得して保存する（テスト的に）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"saved {saved} price records")
```

注意点:
- すべての「書き込み」処理は可能な限り冪等（ON CONFLICT / トランザクション）に設計されています。
- ETL やジョブは個別に失敗しても他の処理を続行するよう設計されています（エラーは結果に記録）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- __init__.py — パッケージ定義（version 等）
- config.py — 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
- data/
  - jquants_client.py — J-Quants API クライアント & 保存ユーティリティ
  - news_collector.py — RSS ニュース収集・前処理・保存ロジック
  - schema.py — DuckDB スキーマ定義・init_schema / get_connection
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py — マーケットカレンダー管理ユーティリティ
  - audit.py — 監査ログ用テーブル定義
  - features.py — data.stats のエクスポート
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - (他: quality.py 等を想定)
- research/
  - factor_research.py — calc_momentum / calc_volatility / calc_value
  - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
- strategy/
  - feature_engineering.py — build_features（Zスコア正規化・ユニバースフィルタ）
  - signal_generator.py — generate_signals（final_score 計算・BUY/SELL 生成）
- execution/ — 発注・約定・ポジション管理用の階層（エントリポイント）
- monitoring/ — 監視・通知に関するモジュール（Slack 連携等を想定）

---

## 開発 / テストのヒント

- settings は環境変数参照時に必須チェックを行うため、テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自前で環境変数を注入するか、必要な変数を設定しておいてください。
- DuckDB の初期化は `init_schema(":memory:")` でメモリ DB を使用可能。ユニットテストで高速に利用できます。
- 外部 API 呼び出し（jquants_client.fetch_* や RSS fetch）はモックしやすいように id_token 注入や内部 _urlopen を差し替えられる設計になっています。
- ログはモジュール内 logger を使用しているため、テストや運用で標準 logging を設定してください（ログレベルは LOG_LEVEL 環境変数で制御可能）。

---

もし README に追加したい内容（API リファレンス、運用手順、品質チェックの仕様、CI/CD の設定、サンプル .env.example の追加など）があればお知らせください。必要に応じてセクションを拡張します。