# KabuSys

日本株向け自動売買 / データ基盤ライブラリ (KabuSys)

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ収集・ETL・品質チェック・特徴量生成・監査ログなどを提供する内部ライブラリ群です。主に以下を目的としています。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する ETL
- RSS からニュースを収集して記事保存・銘柄紐付けを行うニュースコレクタ
- 特徴量（モメンタム、ボラティリティ、バリュー等）の計算と研究用ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ用スキーマ（シグナル→発注→約定のトレーサビリティ）
- 設定管理（.env 自動読み込み / 環境変数）

設計方針としては「DuckDB を中心に SQL と純 Python を組み合わせて実装」「本番注文 API へはアクセスしない研究・データ層と、監査・実行層を分離」などがあります。

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API から日足・財務・カレンダーを取得（ページネーション対応）
  - レート制御、再試行、401 トークン自動リフレッシュ
  - DuckDB へ冪等的に保存する save_* ユーティリティ
- data/schema
  - DuckDB のスキーマ（Raw / Processed / Feature / Execution / Audit）定義と初期化
  - init_schema / get_connection
- data/pipeline
  - 差分 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - バックフィル、品質チェックの統合
- data/news_collector
  - RSS の取得、XML/SSRF 対策、記事正規化、raw_news への冪等保存、銘柄抽出・紐付け
- data/calendar_management
  - market_calendar の差分更新・営業日判定・next/prev_trading_day 等のユーティリティ
- data/quality
  - 欠損、スパイク、重複、日付不整合検査。QualityIssue オブジェクトで詳細を返す。
- data/stats
  - zscore_normalize：クロスセクションでの Z スコア正規化
- research
  - factor_research：モメンタム / ボラティリティ / バリュー計算
  - feature_exploration：将来リターン計算、IC（Spearman）計算、ファクターサマリ
- audit
  - 監査スキーマ（signal_events, order_requests, executions）と初期化ユーティリティ
- config
  - .env 自動読み込み（プロジェクトルートの .env / .env.local を取り込む）
  - Settings クラスで環境変数を型安全に参照

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントで `X | Y` を使用）
- Git, 基本的な Python 開発環境

例: 仮想環境作成と依存インストール（最低限）
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 他に必要なライブラリがあれば追加してください
```

.env（環境変数）の準備
- プロジェクトルートに `.env` を置くと自動で読み込まれます（.env.local の方が優先）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

推奨される最低環境変数（.env 例）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id

# 任意（デフォルト値あり）
# KABUSYS_ENV=development  # development | paper_trading | live
# LOG_LEVEL=INFO
# DUCKDB_PATH=data/kabusys.duckdb
# SQLITE_PATH=data/monitoring.db
```

DuckDB スキーマ初期化
- Python REPL かスクリプトから schema.init_schema を呼ぶと DB とテーブルが作成されます。

例:
```python
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
```

監査用 DB 初期化（別 DB に分離する場合）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

---

## 使い方（代表的な例）

1) DuckDB 接続の初期化
```python
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（J-Quants API トークンは settings から取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 市場カレンダーのみ更新（夜間バッチ等）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved:", saved)
```

4) RSS ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は既知の銘柄コード集合（抽出に利用）
known_codes = {"7203", "6758", "9984", ...}
res = run_news_collection(conn, known_codes=known_codes)
print(res)
```

5) 研究用ファクター計算
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

6) Z スコア正規化
```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "ma200_dev"])
```

7) 品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=some_date)
for issue in issues:
    print(issue)
```

補足
- jquants_client は内部でレート制御・再試行・トークンリフレッシュを行います。id_token を外部で取得して注入することも可能です（テスト容易性のため）。
- news_collector には SSRF 防止・gzip サイズ制限・XML の防御が組み込まれています。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabuステーション API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知に使用
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

注意: Settings クラスは未設定の必須変数に対して ValueError を投げます。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                            — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py                   — J-Quants API クライアント / 保存ユーティリティ
    - news_collector.py                   — RSS ニュース収集・前処理・保存
    - schema.py                           — DuckDB スキーマ定義 / init_schema
    - pipeline.py                         — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py              — market_calendar 管理・営業日ロジック
    - stats.py                            — 統計ユーティリティ（zscore_normalize）
    - features.py                         — features の公開インターフェース
    - etl.py                              — ETLResult の再エクスポート
    - audit.py                            — 監査ログスキーマ初期化
    - quality.py                          — 品質チェック
  - research/
    - __init__.py
    - factor_research.py                  — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py              — 将来リターン / IC / summary
  - strategy/                              — 戦略層（プレースホルダ）
    - __init__.py
  - execution/                             — 発注/実行層（プレースホルダ）
    - __init__.py
  - monitoring/                            — 監視関連（プレースホルダ）

---

## 開発上の注意点 / 補足

- DuckDB の SQL を多用しているため、初期化時に必要なデータディレクトリを作成する関数が用意されています（schema.init_schema）。
- ニュースの重複検出や記事 ID は URL 正規化後の SHA-256 の先頭 32 文字を使用し冪等性を担保しています。
- RSS 取得には defusedxml を使用して XML 攻撃を防ぎ、SSRF を避けるためにリダイレクト時にホスト検査を行います。
- ETL は Fail-Fast でなく「各ステップ独立にエラーハンドリングして可能な処理を継続」する設計です。戻り値の ETLResult にエラー・品質問題が集約されます。
- 本ライブラリは「データ取得・処理・監査」に重きを置いており、実際の証券会社発注ロジック（接続・認証・注文フロー）は別途実装またはラッパーを用意する想定です。

---

もし README に追加したい具体的な使用例（スクリプト）、CI 設定、または .env.example のテンプレートが必要であれば教えてください。README に含める形で追記します。