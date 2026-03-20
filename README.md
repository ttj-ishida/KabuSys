# KabuSys

日本株自動売買プラットフォームのコアライブラリ（プロトタイプ）。  
データ取得（J-Quants）、データベース（DuckDB）スキーマ、ETLパイプライン、研究用ファクター計算、特徴量エンジニアリング、シグナル生成、ニュース収集などの主要コンポーネントを含みます。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコア実装要素を集約したライブラリ群です。以下を目的としています。

- J-Quants API からの株価・財務・カレンダーの取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB を用いたデータスキーマ定義と永続化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量生成（Zスコア正規化、ユニバースフィルタ）
- シグナル生成（コンポーネントスコア合成、Bear レジーム抑制、エグジット判定）
- ニュース収集（RSS 取得・前処理・銘柄紐付け）
- カレンダー管理・監査ログ等の補助機能

設計上のポイント:
- ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）
- 冪等（idempotent）な DB 保存（ON CONFLICT / INSERT ... DO UPDATE 等）
- 本番 API（発注）層への直接依存を持たない（戦略層と実行層を分離）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レートリミット・リトライ・トークン管理）
  - schema: DuckDB スキーマ定義と初期化（Raw/Processed/Feature/Execution 層）
  - pipeline: 日次 ETL（市場カレンダー・株価・財務の差分取得と保存）
  - news_collector: RSS からのニュース収集・正規化・DB 保存・銘柄抽出
  - calendar_management: 営業日判定、next/prev_trading_day、カレンダー更新ジョブ
  - stats: Zスコア正規化などの統計ユーティリティ
  - audit: 発注〜約定までの監査ログ用 DDL（トレーサビリティ）
- research/
  - factor_research: モメンタム・ボラティリティ・バリューなどのファクター計算
  - feature_exploration: 将来リターン計算 / IC / 統計サマリー
- strategy/
  - feature_engineering: 生ファクターの正規化・ユニバース適用・features テーブル書込
  - signal_generator: final_score 計算、BUY/SELL シグナル生成、signals テーブル書込
- config: 環境変数・設定管理（.env / .env.local 自動ロード, Settings オブジェクト）
- その他: execution/ monitoring/ （発注・監視関連の拡張ポイント）

---

## 必要条件（推奨）

- Python 3.10+
- duckdb
- defusedxml
- （標準ライブラリの urllib 等を使用）

pip インストール例（最低限）:
```bash
pip install duckdb defusedxml
```

プロジェクト配布形態によっては、`pip install -e .` などでインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン / 取得

2. 仮想環境作成（任意）
```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows
```

3. 依存パッケージをインストール
```bash
pip install duckdb defusedxml
# その他開発用: pytest 等を追加
```

4. 環境変数を設定
- プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（config モジュール参照）。
- 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（Settings が参照するもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD       : kabuステーション API パスワード（発注等で使用）
- SLACK_BOT_TOKEN         : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID        : Slack 通知先チャネル ID

任意（デフォルト値あり）
- KABUSYS_ENV             : development / paper_trading / live （デフォルト: development）
- LOG_LEVEL               : DEBUG/INFO/...（デフォルト: INFO）
- DUCKDB_PATH             : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH             : SQLite（monitoring 等）パス（デフォルト: data/monitoring.db）

5. DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # ファイルを作成してスキーマを作る
conn.close()
```

---

## 使い方（主要ワークフロー）

以下は最も一般的な日次処理の例です。

1) 日次 ETL の実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.pipeline import run_daily_etl

# 初回のみスキーマ作成
conn = init_schema(settings.duckdb_path)

# 指定日（省略時は今日）の ETL を実行
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

2) 特徴量の構築（features テーブルへの書き込み）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
conn.close()
```

3) シグナル生成（signals テーブルへの書き込み）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection(settings.duckdb_path)
num_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {num_signals}")
conn.close()
```

4) ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = get_connection(settings.duckdb_path)
# known_codes は銘柄抽出に使用する有効なコードセット（省略可）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
print(results)
conn.close()
```

5) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
conn.close()
```

6) DB 操作補助
- スキーマ初期化: `init_schema(db_path)`
- 既存 DB へ接続: `get_connection(db_path)`

---

## ディレクトリ構成（src/kabusys）

主要ファイルとモジュールを抜粋して示します。

- kabusys/
  - __init__.py
  - config.py                     — 環境変数・Settings
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（fetch/save）
    - schema.py                   — DuckDB スキーマ定義・初期化
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - news_collector.py           — RSS 取得・保存・銘柄抽出
    - calendar_management.py      — 営業日判定, calendar_update_job
    - features.py                 — zscore_normalize の再エクスポート
    - stats.py                    — zscore_normalize 等
    - audit.py                    — 監査ログ用 DDL（signal_events, order_requests, executions）
    - quality.py?                 — （品質チェックモジュール想定）
  - research/
    - __init__.py
    - factor_research.py          — calc_momentum, calc_volatility, calc_value
    - feature_exploration.py      — calc_forward_returns, calc_ic, factor_summary, rank
  - strategy/
    - __init__.py
    - feature_engineering.py      — build_features
    - signal_generator.py         — generate_signals
  - execution/                    — 発注・約定・ポジション管理（拡張用）
  - monitoring/                   — 監視・アラート用（拡張用）

注: 上記はコードベース内の実装を反映しています。実運用では `execution` 層（実際の発注インテグレーション）や `monitoring`（Prometheus, Slack 通知等）を追加実装してください。

---

## 開発者向けメモ

- 自動 .env 読み込み
  - config._find_project_root() によりプロジェクトルート（.git または pyproject.toml）を探索し、`.env` / `.env.local` を自動ロードします。
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Settings
  - `from kabusys.config import settings` でアプリ設定にアクセスできます（プロパティは必要時に ValueError を投げます）。
- 冪等性
  - API から取得したデータは `ON CONFLICT DO UPDATE` や `DO NOTHING` を用いて DB に冪等保存されます。
- ロギング
  - `LOG_LEVEL` 環境変数でログレベルを制御できます（DEBUG/INFO/...）。デフォルトは INFO。
- テスト
  - ETL / API 呼び出しは id_token の注入や `_urlopen` のモックなど、外部依存を差し替え可能な設計です。

---

## 参考・補足

- 戦略仕様（StrategyModel.md）、データプラットフォーム設計（DataPlatform.md）等のドキュメントに準拠した設計を反映しています（コード内コメント参照）。
- 実運用ではバックテスト、リスク管理、発注の冪等性（二重送信防止）や SLA を満たす監視が必須です。
- このリポジトリはコアライブラリであり、運用バイナリ・ジョブスケジューラ・Broker インテグレーションは個別に実装してください。

---

必要であれば README に以下を追加できます：
- インストール用 requirements.txt / pyproject.toml の例
- CI / GitHub Actions 用ワークフローサンプル
- さらなる使用例（cron ジョブ、Dockerfile、systemd サービス）