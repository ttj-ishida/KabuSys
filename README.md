# KabuSys

日本株の自動売買・データ基盤ライブラリ。J-Quants API や RSS ニュースを取り込み、DuckDB に保管して特徴量を計算、戦略・発注・監査ログのためのスキーマやユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株向けに設計されたデータプラットフォーム兼研究・自動売買基盤です。主に以下の役割を持ちます。

- J-Quants API から日次株価・財務データ・市場カレンダーを差分取得して DuckDB に保存
- RSS フィードからニュースを収集して記事・銘柄紐付けを保存
- データ品質チェック、マーケットカレンダー管理、ETL パイプラインを提供
- 生成された市場データからファクター（モメンタム、ボラティリティ、バリュー等）を計算
- 発注・約定・ポジション管理や監査ログスキーマを備えトレーサビリティを確保
- 研究用ユーティリティ（IC 計算、Zスコア正規化 等）を提供

設計上、ETL / データ取得モジュールは本番ブローカーや発注 API へはアクセスしません（look-ahead bias 回避のため取得時刻を記録）。

---

## 主な機能一覧

- data/jquants_client:
  - J-Quants API クライアント（ページネーション対応、レート制限・リトライ・トークン自動リフレッシュ）
  - fetch/save 関数（株価、財務、カレンダー）
- data/pipeline:
  - 差分 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - ETL 結果の集約と品質チェック
- data/news_collector:
  - RSS フィード取得（SSRF・gzip・XML 攻撃防御、URL 正規化、記事ID のハッシュ生成）
  - raw_news 保存、ニュースと銘柄の紐付け
- data/schema / data/audit:
  - DuckDB のスキーマ初期化（Raw / Processed / Feature / Execution 層、監査ログテーブル群）
  - 監査用スキーマ（signal_events / order_requests / executions）
- data/quality:
  - 欠損・スパイク・重複・日付不整合チェック
- data/calendar_management:
  - market_calendar の更新／営業日判定ユーティリティ（next_trading_day 等）
- research:
  - ファクター計算（calc_momentum、calc_volatility、calc_value）
  - 将来リターン計算 / IC（Information Coefficient）計算 / factor_summary
- data/stats:
  - zscore_normalize（クロスセクション Z スコア正規化）
- 設定管理:
  - 環境変数読み込み（.env / .env.local の自動ロード、無効化オプションあり）
  - settings オブジェクトから各種設定を取得

---

## 前提 / 依存関係

- Python 3.10+（型注釈に | を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発用にパッケージ化している場合は `pip install -e .` を利用
```

---

## 環境変数（必須）

プロジェクトは環境変数から設定を読み込みます（プロジェクトルートの `.env` / `.env.local` を自動読込。自動読込を無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主な必須環境変数:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション等の API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）

任意 / デフォルト:

- KABUSYS_ENV — 実行環境: "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

.env 作成例（簡易）:

```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローンし仮想環境を作成・有効化
2. 依存パッケージをインストール（duckdb, defusedxml など）
3. プロジェクトルートに `.env` を作成して必要な環境変数を設定
4. DuckDB スキーマを初期化

サンプル: DuckDB スキーマ初期化

```python
from kabusys.data import schema

# ファイルに保存する場合
conn = schema.init_schema("data/kabusys.duckdb")

# インメモリ DB を使う場合
# conn = schema.init_schema(":memory:")
```

監査ログ専用 DB を初期化する例:

```python
from kabusys.data import audit
conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 基本的な使い方 / API 例

以下は代表的な操作例です。すべて Python API として利用できます。

- 日次 ETL（市場カレンダー, 株価, 財務, 品質チェック）

```python
from datetime import date
from kabusys.data import schema, pipeline

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 個別 ETL（株価のみ差分取得）

```python
from datetime import date
from kabusys.data import schema, pipeline

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
fetched, saved = pipeline.run_prices_etl(conn, date.today())
print(f"fetched={fetched} saved={saved}")
```

- RSS ニュース収集ジョブ

```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# sources を渡さない場合はデフォルトソースが使われます
results = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
print(results)  # {source_name: new_count, ...}
```

- ファクター計算（研究用）

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2024, 1, 31)

mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
# IC の例（mom_1m と fwd_1d の相関）
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

- Z スコア正規化

```python
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m", "ma200_dev"])
```

- J-Quants の低レベル API 呼び出し

```python
from kabusys.data import jquants_client as jq
# fetch_daily_quotes はページネーション対応
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
# 保存は save_daily_quotes(conn, records)
```

---

## 注意点 / 実運用でのポイント

- J-Quants API:
  - レート制限 (120 req/min) はライブラリ内で制御されます（固定間隔のスロットリング）。
  - 401 時はトークン自動リフレッシュと1回のリトライ処理を行います。
  - 特定の HTTP ステータスに対して指数バックオフでリトライします。
- news_collector:
  - SSRF や XML 攻撃対策（defusedxml、ホスト/スキーム検証、受信サイズ制限、gzip 解凍後サイズ検査）を実装しています。
  - 記事ID は正規化 URL の SHA-256 ヘッダ（先頭32文字）を使用し冪等性を確保。
- 自動 .env ロード:
  - デフォルトでプロジェクトルートの `.env` および `.env.local` を読み込みます（OS 環境変数が優先）。
  - テスト等では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- DuckDB スキーマ:
  - init_schema は冪等にテーブルとインデックスを作成します。初回実行のみ実行してください。
  - 監査ログは別関数で初期化できます（init_audit_schema / init_audit_db）。
- 環境 (KABUSYS_ENV) は "development"/"paper_trading"/"live" のいずれかのみ有効です。live 実行時は細心の注意が必要です。

---

## ディレクトリ構成

主要なファイル・モジュールの一覧（リポジトリ内の `src/kabusys` を想定）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得 + 保存）
    - news_collector.py     — RSS ニュース収集・保存
    - schema.py             — DuckDB スキーマ定義と init_schema
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - features.py           — 特徴量関連の公開インターフェース
    - stats.py              — 汎用統計（zscore_normalize）
    - calendar_management.py— market_calendar 管理・営業日判定
    - quality.py            — データ品質チェック
    - audit.py              — 監査ログスキーマ初期化
    - etl.py                — ETLResult 再エクスポート
  - research/
    - __init__.py
    - feature_exploration.py— 将来リターン / IC / factor_summary / rank
    - factor_research.py    — momentum/volatility/value 等の計算
  - strategy/                — 戦略層（雛形）
  - execution/               — 発注実行層（雛形）
  - monitoring/              — 監視用モジュール（雛形）

（上記の多くのモジュールは README 中に説明した役割の実装を含みます）

---

## 開発・拡張の指針

- ETL や API 呼び出しは冪等に保つ（ON CONFLICT / DO UPDATE を活用）。
- 研究コードは DuckDB 接続を受け取り、prices_daily / raw_financials のみを参照すること。発注 API にはアクセスしない。
- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を用いて環境を明示的に制御すると安全。
- DuckDB のタイムスタンプは監査等で UTC を想定しているため、監査 DB 初期化時に TimeZone を UTC に固定する実装が含まれています。

---

## サポート / 貢献

バグ報告や機能追加、PR はリポジトリの Issue / Pull Request を通してお願いします。README に載せきれない運用手順やデータディクショナリは別途ドキュメント（DataPlatform.md、StrategyModel.md など）を参照または追加してください。

---

以上がこのコードベースの概要・セットアップ・使い方・ディレクトリ構成のまとめです。具体的な利用方法や追加のサンプルが必要であれば、どのユースケース（ETL 実行、ニュース収集、研究用ファクター計算、監査スキーマ初期化等）を優先して示すか教えてください。