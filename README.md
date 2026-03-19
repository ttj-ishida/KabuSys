# KabuSys

KabuSys は日本株の自動売買・データ基盤・リサーチ用ユーティリティ群を集めたライブラリです。J-Quants や RSS などからデータを収集して DuckDB に格納し、特徴量計算・品質チェック・ETL パイプライン・監査ログなどを提供します。発注／モニタリング／ストラテジー層との連携を想定した設計になっています。

---

## プロジェクト概要

主な目的は以下です。

- J-Quants API から株価日足・財務データ・マーケットカレンダーを安全に取得して DuckDB に保存する
- RSS を用いたニュース収集と銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ETL（差分取得・バックフィル）と夜間バッチ処理
- リサーチ用のファクター計算（モメンタム・ボラティリティ・バリュー等）と IC / 統計サマリー
- 発注 / 監査ログスキーマ（監査トレース用）を提供

設計上の注力点は安全性（SSRF対策、XML攻撃対策）、冪等性（ON CONFLICT）、レート制御・リトライ、Look-ahead バイアス防止（fetched_at の記録）などです。

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、無効化オプションあり）
  - 必須環境変数取得時のバリデーション（例: JQUANTS_REFRESH_TOKEN）

- Data 層
  - J-Quants クライアント（ページネーション、レート制御、リトライ、トークン自動リフレッシュ）
  - DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
  - ETL パイプライン（差分取得、バックフィル、品質チェック統合）
  - カレンダー管理（営業日判定、next/prev trading day 等）
  - ニュース収集（RSS パース、URL 正規化、SSRF 対策、記事保存と銘柄抽出）
  - 品質チェック（欠損、スパイク、重複、日付不整合）

- Research 層
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank
  - 共通統計: zscore_normalize

- Execution / Monitoring / Strategy
  - それぞれの名前空間が存在し、発注や監視・戦略実装を置ける構造（骨組みを提供）

---

## セットアップ手順

前提
- Python 3.10 以上（型アノテーションで `|` 記法を使用）
- 必要パッケージ: duckdb, defusedxml（ネットワーク/DB/XML 関連機能で使用）

例: 仮想環境作成とパッケージインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 開発中はプロジェクトを editable install する場合:
# pip install -e .
```

環境変数
- .env（または .env.local）をプロジェクトルートに配置すると、自動で読み込まれます（デフォルト）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須な代表的環境変数（README 用の例。実際は機能を使う箇所に応じて必須変数が異なります）:
- JQUANTS_REFRESH_TOKEN = "<your_jquants_refresh_token>"
- SLACK_BOT_TOKEN = "<your_slack_bot_token>"
- SLACK_CHANNEL_ID = "<your_slack_channel_id>"
- KABU_API_PASSWORD = "<kabu_station_password>"
- KABUSYS_ENV = development | paper_trading | live
- LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL
- DUCKDB_PATH = data/kabusys.duckdb  (デフォルト)
- SQLITE_PATH = data/monitoring.db    (デフォルト)

.env.example（参考）
```
JQUANTS_REFRESH_TOKEN=xxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## 使い方（主要な例）

以下はライブラリを直接インポートして使う基本例です。実運用ではエントリポイントスクリプトやジョブスケジューラ（cron / Airflow 等）から呼び出します。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリがなければ作成される）
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ:
# conn = schema.init_schema(":memory:")
```

2) 日次 ETL 実行（J-Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl, ETLResult
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# known_codes は銘柄コードセット（抽出精度向上のため）
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)
```

4) 研究用ファクター計算
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
t = date(2024, 1, 31)
mom = calc_momentum(conn, t)
vol = calc_volatility(conn, t)
val = calc_value(conn, t)

# Zスコア正規化
from kabusys.data.stats import zscore_normalize
norm = zscore_normalize(mom, ["mom_1m", "ma200_dev"])
```

5) J-Quants から日足を直接フェッチして保存
```python
from kabusys.data import jquants_client as jq
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"saved {saved} records")
```

6) 監査ログスキーマ初期化（監査用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

ログ・環境情報
- 環境種別（development, paper_trading, live）は `KABUSYS_ENV` で指定され、settings.is_live などで参照可能です。
- ログレベルは `LOG_LEVEL`（デフォルト INFO）で制御されます。

注意点
- J-Quants API のレート制限（120 req/min）をモジュール内で制御しますが、大量フェッチ等は設計に応じて時間管理してください。
- news_collector は defusedxml を利用し XML 攻撃を防止します。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成

主要ファイル／モジュールのツリー（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数・設定管理（.env 自動ロード、settings）
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント（取得・保存）
    - news_collector.py            -- RSS ニュース収集と銘柄抽出・保存
    - schema.py                    -- DuckDB スキーマ定義・初期化
    - stats.py                     -- 統計ユーティリティ（zscore_normalize）
    - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
    - features.py                  -- 特徴量ユーティリティの公開インターフェース
    - calendar_management.py       -- マーケットカレンダー管理（営業日判定等）
    - audit.py                     -- 監査ログスキーマ / 初期化
    - etl.py                       -- ETL API エクスポート
    - quality.py                   -- データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py       -- 将来リターン・IC・summary 等
    - factor_research.py           -- momentum/volatility/value 等の計算
  - strategy/
    - __init__.py                  -- ストラテジー層用スペース（拡張用）
  - execution/
    - __init__.py                  -- 発注・実行層用スペース（拡張用）
  - monitoring/
    - __init__.py                  -- 監視機能（拡張用）

各モジュールは「DuckDB 接続を受け取る」「外部発注 API へ直接アクセスしない（Research 等）」といった方針で実装されています。ETL / Data モジュールは DuckDB のテーブル名（raw_prices, prices_daily, raw_financials, market_calendar, raw_news, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）に依存します。スキーマは schema.init_schema() で一括作成できます。

---

## 追加メモ／運用上の注意

- 環境ごとの挙動: KABUSYS_ENV により is_live/is_paper/is_dev を切り替えて、発注処理等で安全措置を入れてください（本実装は発注ロジックの骨組みを提供しますが、実運用での追加の安全チェックが必要です）。
- レート制御・リトライ: jquants_client は固定間隔スロットリングと指数バックオフを備え、401 時はトークンを自動リフレッシュして再試行します。
- DB バックアップとロック: DuckDB ファイルを複数プロセスで扱う場合は運用ポリシーを検討してください（同時書き込み等の注意）。
- テスト: .env の自動ロードを無効化してテスト専用環境を用いることを推奨します（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

もし README に加えたい具体的な運用手順、CI/CD の設定例、cron / Airflow ジョブ例、または各 API の詳細な使用例（個別関数のパラメータ説明やサンプル）などがあれば教えてください。必要に応じてドキュメントを拡張します。