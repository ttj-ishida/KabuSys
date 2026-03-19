# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買プラットフォームのコンポーネント群です。データ取得/保存（DuckDB）、ETL パイプライン、データ品質チェック、ニュース収集、ファクター（特徴量）計算、監査ログなど、研究〜実行までのワークフローを想定したモジュール群を提供します。

主な設計方針:
- DuckDB を用いた軽量で冪等なデータレイヤ（Raw / Processed / Feature / Execution）
- J-Quants API からのデータ取得はレート制限・リトライ・トークンリフレッシュを考慮
- ニュース収集はセキュリティ（SSRF/ZIP bomb/XML 脆弱性）に配慮
- ETL/品質チェックは Fail-Fast ではなく全件収集（呼び出し元が対処）

---

## 機能一覧

- 環境変数管理（.env 自動ロード / 保護）
- J-Quants API クライアント
  - 日足 (OHLCV)、財務データ、マーケットカレンダー取得（ページネーション対応）
  - レートリミット制御・リトライ・トークン自動リフレッシュ
- DuckDB スキーマ定義 / 初期化（冪等）
- ETL パイプライン（差分取得・バックフィル・保存）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- ニュース収集（RSS → raw_news, news_symbols への保存、記事中の銘柄抽出）
- 監査ログ（signal / order_request / executions 等の監査用テーブル群）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー系ファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - Zスコア正規化ユーティリティ

セキュリティ/運用上の配慮:
- J-Quants のレート制限（120 req/min）をガイドラインとして実装
- RSS フィード取得に SSRF 対策、gzip サイズチェック、defusedxml の使用
- DB への保存は ON CONFLICT/トランザクションを使い冪等化

---

## 必要条件（依存）

最低限必要な Python パッケージ（コード中の import より）:
- Python 3.9+
- duckdb
- defusedxml

（その他は標準ライブラリのみ使用。J-Quants クライアントは urllib を使用しており追加 HTTP クライアントは不要です。）

インストール例（仮）:
pip install duckdb defusedxml

プロジェクトとして配布する場合は setup/pyproject に依存が明記されている想定です。

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージをインストール）
2. Python 環境を準備（推奨: venv / poetry）
3. 依存ライブラリをインストール:
   pip install duckdb defusedxml
4. 環境変数を設定（.env をプロジェクトルートに配置）
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

.env の例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
# DB パスは省略可（デフォルトを使う）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

5. DuckDB スキーマを初期化:
Python REPL やスクリプトから init_schema を呼び出す（例は下記「使い方」参照）。

---

## 使い方（サンプル）

以下は代表的な使い方例です。プロジェクトをパッケージとして import して利用します。

- DuckDB スキーマ初期化（最初の一回）
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection オブジェクト
```

- 日次 ETL 実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # あるいは init_schema 後の conn
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes: 抽出許可する銘柄コードセット（例: all codes）
known_codes = {"7203", "6758", ...}
res = run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)  # 各ソースごとの新規保存数
```

- 研究用ファクター計算 / 正規化 / IC 計算
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
t = date(2025, 1, 31)
mom = calc_momentum(conn, t)
vol = calc_volatility(conn, t)
val = calc_value(conn, t)
fwd = calc_forward_returns(conn, t, horizons=[1,5,21])

# 例: mom_1m と fwd_1d の IC
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])

# Zスコア正規化
normed = zscore_normalize(mom, ["mom_1m", "ma200_dev"])
```

- 監査ログ初期化（別DBに分けたい場合）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABUSYS_ENV (任意) — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（使用する機能がある場合）
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視等で使用する sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効にできます（テスト時等）

注意: Settings で必須とされている環境変数が未設定だと起動時に ValueError が発生します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なモジュール構成です（完全な一覧ではありません）。

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                # 環境変数管理（.env 自動ロード含む）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント + DuckDB 保存ユーティリティ
    - news_collector.py      # RSS ニュース収集・前処理・保存・銘柄抽出
    - schema.py              # DuckDB スキーマ定義と init_schema / get_connection
    - stats.py               # 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - features.py            # features の公開インターフェース（zscore 正規化再エクスポート）
    - calendar_management.py # マーケットカレンダー管理ユーティリティ
    - audit.py               # 監査ログ初期化（signal/order_request/executions）
    - etl.py                 # ETLResult 再エクスポート
    - quality.py             # データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py # 将来リターン計算 / IC / summary / rank
    - factor_research.py     # momentum/value/volatility 等のファクター計算
  - strategy/
    - __init__.py           # 戦略関連モジュール（未実装部分がある想定）
  - execution/
    - __init__.py           # 発注/約定処理（未実装部分がある想定）
  - monitoring/
    - __init__.py           # 監視・アラート（未実装部分がある想定）

---

## 運用上の留意点 / 実装上のメモ

- J-Quants API はレートリミット（120 req/min）を守る必要があり、モジュールは fixed-interval スロットリングとリトライを実装しています。大量の並列要求は避けてください。
- ニュース収集は外部フィードを扱うため、RSS の解析や外部 URL の検証を厳格に行っています。カスタムソースを追加する際は入力値の検証方針に留意してください。
- DuckDB での DDL 実行は冪等化していますが、監査ログの初期化など一部トランザクションに注意が必要です（init_audit_schema の transactional 引数など）。
- ETL は各ステップでエラーハンドリングを行い、品質チェックは Fail-Fast ではなく呼び出し元が判断できる形で結果を返します。
- 本コードベースは研究・ペーパートレードから実運用（live）までを想定していますが、実際のマネーを扱う場合は十分なテスト・監査・リスク管理を行ってください。

---

この README はコードベースの概要と主要な利用方法を説明するための簡易ドキュメントです。詳細な設計仕様（DataPlatform.md / StrategyModel.md 等）や運用手順は別ドキュメントで管理することを推奨します。ご要望があれば、インストール用の pyproject.toml / requirements.txt の雛形や、具体的な運用スクリプト例（systemd / cron / Airflow）も作成します。