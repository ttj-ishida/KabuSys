# KabuSys

日本株向けの自動売買プラットフォームのコアライブラリです。データ取得（J‑Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマなど、戦略実装・バックテスト・運用に必要な基盤機能を提供します。

---

## プロジェクト概要

KabuSys は次のレイヤーを想定したモジュール群を提供します。

- Data Layer: J‑Quants API からの株価・財務・カレンダー・ニュース取得、DuckDB への冪等保存
- Processed / Feature Layer: 日次データの集計、クロスセクション正規化、features / ai_scores テーブル
- Strategy Layer: 特徴量（feature）構築、final_score による BUY/SELL シグナル生成
- Execution / Audit Layer: シグナル / 注文 / 約定 / ポジション監査用スキーマ（DuckDB）
- Research: ファクター計算・探索ユーティリティ（IC, forward returns, factor summary）
- Utilities: 環境設定の一元管理（.env 自動ロード等）、統計ユーティリティ

設計上の特徴:
- DuckDB を主DBとし、冪等な INSERT（ON CONFLICT）でデータ整合性を確保
- J‑Quants API 呼び出しに対するレート制御・リトライ・トークン自動更新を実装
- ルックアヘッドバイアス防止（計算は target_date 時点の情報のみを利用）
- ニュース収集は SSRF 対策や XML の安全パースを行う

---

## 主な機能一覧

- 環境設定管理（kabusys.config.Settings）
  - .env / .env.local をプロジェクトルートから自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- DuckDB スキーマ初期化・接続（kabusys.data.schema.init_schema / get_connection）
- J‑Quants API クライアント（kabusys.data.jquants_client）
  - fetch/save の冪等化、ページネーション対応、レートリミット・リトライ・token refresh
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl：市場カレンダー → 株価 → 財務 → 品質チェック の一括実行
- 特徴量計算（kabusys.research.factor_research）
  - momentum / volatility / value 等を prices_daily/raw_financials から計算
- 特徴量正規化・features 保存（kabusys.strategy.feature_engineering）
- シグナル生成（kabusys.strategy.signal_generator）
  - final_score による BUY/SELL 判定、Bear レジーム抑制、SELL（エグジット）条件判定
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、raw_news 保存、銘柄コード抽出と紐付け
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev_trading_day、夜間更新ジョブ

---

## 動作環境・依存関係

- Python 3.10+
- 必須パッケージ（一例）
  - duckdb
  - defusedxml

（プロジェクト配布時に requirements.txt / pyproject.toml を用意してください。ここでは主要依存を列挙しています。）

---

## セットアップ手順

1. リポジトリを取得し、仮想環境を作成・有効化します。

```bash
git clone <repo-url>
cd <repo-root>
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate     # Windows
```

2. 必要パッケージをインストールします（例）:

```bash
pip install duckdb defusedxml
# またはプロジェクトに pyproject/requirements がある場合:
# pip install -e .
```

3. 環境変数を設定します。.env ファイルをプロジェクトルートに置くと自動読み込みされます（.env.local が存在すれば優先）。

必須の環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN      — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD         — kabu ステーション API パスワード（発注系を使う場合）
- SLACK_BOT_TOKEN           — Slack 通知を使う場合
- SLACK_CHANNEL_ID          — Slack チャンネル ID

推奨・任意:
- DUCKDB_PATH               — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH               — 監視 DB（SQLite）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV               — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL                 — DEBUG/INFO/...

例 .env:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

テストや CI で自動 .env ロードを無効化したい場合:

```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（基本的なコード例）

以下は Python から各主要機能を呼び出す最小例です。実運用ではログ設定やエラーハンドリング、スケジューラなどを組み合わせてください。

- DuckDB スキーマ初期化 / 接続

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照
conn = init_schema(settings.duckdb_path)  # ファイルなければ作成してスキーマ初期化
# 既存 DB に接続するだけなら:
# conn = get_connection(settings.duckdb_path)
```

- 日次 ETL の実行

```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

- 特徴量（features）構築

```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date(2025, 1, 15))
print(f"features upserted: {n}")
```

- シグナル生成

```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date.today())
print(f"signals generated: {count}")
```

- ニュース収集ジョブ（RSS）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes: 銘柄コードのセット（抽出に使用）
known_codes = {"7203", "6758", "9984"}  # 例

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- カレンダー夜間更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意:
- J‑Quants API 呼び出しは rate limit（120 req/min）やリトライの対象となります。`kabusys.data.jquants_client` はこれらを内部で処理します。
- settings で未設定の必須環境変数を参照すると ValueError が発生します。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 下に配置されています。代表的なファイル・モジュール:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J‑Quants API クライアント / save_* 関数
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - schema.py                  — DuckDB スキーマ定義・init_schema
    - stats.py                   — zscore_normalize 等の統計ユーティリティ
    - news_collector.py          — RSS 収集、raw_news 保存、銘柄抽出
    - calendar_management.py     — market_calendar 管理・営業日判定
    - features.py                — data 側の feature helper
    - audit.py                   — 監査ログスキーマ（signal_events / order_requests / executions）
    - pipeline.py                — ETL 実行ロジック
  - research/
    - __init__.py
    - factor_research.py         — momentum / volatility / value 計算
    - feature_exploration.py     — forward returns / IC / factor summary
  - strategy/
    - __init__.py
    - feature_engineering.py     — features テーブル構築・正規化
    - signal_generator.py        — final_score 計算・signals 書き込み
  - execution/                    — （発注実装を入れる層）
  - monitoring/                   — （監視・アラートの実装を置く層）

（上記は現行コードベースの主なファイルを抜粋したものです）

---

## よくあるトラブルと対処

- 環境変数未設定による ValueError:
  - settings（kabusys.config.Settings）は必須のキーを参照すると例外を投げます。必須キーを .env に設定してください。

- .env 自動読み込みが邪魔なとき:
  - テスト環境や特定の実行時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DuckDB ファイルパスが存在しない:
  - init_schema は親ディレクトリを自動作成します。パスにアクセス権限があるか確認してください。

- J‑Quants API 呼び出しで 401 が返る:
  - jquants_client はリフレッシュトークンから ID トークンを取得し自動リトライします。リフレッシュトークン（JQUANTS_REFRESH_TOKEN）が正しいか確認してください。

---

## 貢献・拡張について

- strategy 層では build_features / generate_signals を公開 API としているため、戦略の差し替え・パラメータ調整はこの層を中心に実装してください。
- execution 層は発注実装の差し替えポイントです。kabu ステーションやブローカーの API 連携はここに実装します。
- テストを書いて各 ETL・集計関数（duckdb のインメモリ ":memory:" を利用）を検証してください。config の自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で制御できます。

---

この README はコードベースに含まれる実装を元に作成しています。詳細な設計ドキュメント（StrategyModel.md / DataPlatform.md / DataSchema.md 等）が別途ある場合は、そちらも参照してください。必要であれば README の英語版や踏み込んだ運用手順（cron / Airflow / systemd などによる定期実行例）も用意できます。