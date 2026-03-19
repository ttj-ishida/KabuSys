# KabuSys

日本株向けの自動売買システム（ライブラリ）。データ収集（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査ログ・実行層のスキーマ等を含むモジュール群を提供します。

主な設計方針は「ルックアヘッドバイアス回避」「冪等性（idempotent）」「DuckDB を用いたローカルデータベース」「外部発注層への直接依存を持たないモジュール化」です。

---

## 機能一覧

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、JPXマーケットカレンダー
  - レート制限対応（120 req/min）、リトライ、トークン自動リフレッシュ
- データ保存（DuckDB）
  - Raw / Processed / Feature / Execution 層のスキーマを提供（冪等保存）
- ETL パイプライン
  - 差分取得（バックフィル対応）・保存・品質チェック（quality モジュールと連携）
  - 日次 ETL 実行エントリ（run_daily_etl）
- 研究（research）機能
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - Z スコア正規化ユーティリティ
- 戦略（strategy）
  - 特徴量構築（build_features）：research で算出した raw ファクターを正規化し features テーブルへ
  - シグナル生成（generate_signals）：features と ai_scores を統合して BUY/SELL シグナルを生成
- ニュース収集（news_collector）
  - RSS 収集、URL 正規化（トラッキング除去）、SSRF 対策、記事保存、銘柄抽出
- カレンダー管理
  - 営業日判定、次/前営業日の取得、期間内営業日リスト取得、calendar 更新ジョブ
- 監査・実行用スキーマ（audit、signal_queue、orders、trades、positions 等）

---

## 必要条件 / 推奨環境

- Python 3.10+
- duckdb
- defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード取得）

（パッケージ化されている場合は requirements.txt / pyproject.toml を参照してください）

---

## 環境変数（主なもの）

以下は Settings クラスで必須/参照される主要な環境変数です（詳細は `kabusys.config.Settings` を参照）。

必須（未設定時は起動時にエラーになります）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション等の API パスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意/デフォルト値あり:
- KABUSYS_ENV — 実行環境: `development` / `paper_trading` / `live`（デフォルト `development`）
- LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト `INFO`）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト `data/monitoring.db`）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動的に読み込みます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（例）

1. リポジトリをクローンし、仮想環境を作成
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

2. 必要な依存パッケージをインストール
（プロジェクトに pyproject.toml / requirements.txt があればそれを使用）
```bash
pip install duckdb defusedxml
# または
pip install -e .
```

3. 環境変数を設定
- プロジェクトルートに `.env` を作成するか、環境変数として設定してください。例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=zzzz
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

4. DuckDB スキーマの初期化
Python REPL またはスクリプトで:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # デフォルト: data/kabusys.duckdb
# もしくはインメモリ:
# conn = init_schema(":memory:")
```

---

## 使い方（主要な操作例）

- 日次 ETL の実行（市場カレンダー、株価、財務の差分取得・保存と品質チェック）:
```python
from datetime import date
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# 初期化済みでない場合は init_schema(settings.duckdb_path)
conn = init_schema(settings.duckdb_path)

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量の構築（features テーブル生成）
```python
from datetime import date
from kabusys.data.schema import get_connection, init_schema
from kabusys.strategy import build_features
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
n = build_features(conn, target_date=date.today())
print(f"build_features: {n} 銘柄処理")
```

- シグナル生成（signals テーブル生成）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
count = generate_signals(conn, target_date=date.today())
print(f"generate_signals: total {count}")
```

- ニュース収集ジョブ（RSS 取得・保存・銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes は抽出対象となる銘柄コード集合（例: 上場銘柄リスト）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)
```

- カレンダー更新ジョブ（夜間バッチ想定）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"calendar_update_job: saved={saved}")
```

注意:
- 各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。アプリ側で接続管理（シングルトン化、トランザクション境界など）を行ってください。
- strategy モジュールは発注 API への直接依存を持たず、signals テーブルへの書き込みまで行います。実際の発注は execution 層（別実装）で行います。
- J-Quants API 呼び出しには rate limiter / retry / token refresh の仕組みが組み込まれています。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトの `src/kabusys` 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得・保存）
    - news_collector.py           — RSS 収集・保存・銘柄抽出
    - schema.py                   — DuckDB スキーマ定義・初期化
    - stats.py                    — 統計ユーティリティ（zscore_normalize）
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py      — カレンダー管理・更新ジョブ
    - audit.py                    — 監査ログ用スキーマ
    - features.py                 — data の feature インターフェース（再エクスポート）
  - research/
    - __init__.py
    - factor_research.py          — ファクター計算（momentum/volatility/value）
    - feature_exploration.py      — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py     — features テーブル作成（build_features）
    - signal_generator.py        — シグナル生成ロジック（generate_signals）
  - execution/                   — 発注・モニタリング等（パッケージプレースホルダ）
  - monitoring/                  — 監視・通知等（パッケージプレースホルダ）

---

## 注意事項 / 実運用のヒント

- Settings は必須環境変数を _require() で取得します。CI / デプロイ環境では .env を漏洩させないように注意してください。
- データベース（DuckDB）ファイルのバックアップやアクセス制御を考慮してください。デフォルトは `data/kabusys.duckdb`。
- J-Quants API のレート制限やリトライロジックが組み込まれていますが、運用時は API 使用ポリシーに従ってください。
- strategy 層・execution 層を分離しているため、実売買を行う場合は execution の実装（証券会社 API 連携、発注の冪等化、監査ログの連携）を別途実装する必要があります。
- テスト用途では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動 .env ロードを無効化できます。

---

## 開発・貢献

- コードはモジュール単位で分割されており、DuckDB 接続を注入することでユニットテストが容易です。
- 外部 API 呼び出し部分（jquants_client._request、news_collector._urlopen 等）はモック可能に設計されています。

---

この README はコードベースの主要機能と使い方をまとめたものです。詳細な設計仕様（StrategyModel.md、DataPlatform.md、Research/README 等）がプロジェクトに含まれている場合はそちらも合わせて参照してください。必要であればセットアップスクリプトや例示的な CLI の追加 README を作成します。