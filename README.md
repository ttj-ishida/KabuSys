# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（モジュール群）。  
DuckDB をデータストアとして用い、J-Quants API からのデータ取得、ETL、品質チェック、特徴量計算、ニュース収集、監査ログ等のユーティリティを提供します。

---

## 主な目的（概要）

- J-Quants 等の外部データソースから日本株の市場データ・財務データを取得して DuckDB に蓄積する。
- 品質チェック・差分ETL・カレンダー管理・ニュース収集を含むデータパイプラインを提供する。
- 戦略研究用のファクター計算（モメンタム・バリュー・ボラティリティ等）および特徴量探索ツールを提供する。
- 発注・監査ログ・シグナル管理等の実行層のためのスキーマ・ユーティリティを備える（発注クライアント実装は別途）。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数の検査（`settings` オブジェクト）
- Data レイヤー（kabusys.data）
  - J-Quants クライアント（取得・リトライ・レート制御・トークン自動リフレッシュ）
  - DuckDB スキーマ初期化（raw / processed / feature / execution 層）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - 市場カレンダー管理（営業日判定・next/prev/get_trading_days）
  - ニュース収集（RSS パーシング、SSRF対策、トラッキングパラメータ除去、記事→銘柄紐付け）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
  - 統計ユーティリティ（Zスコア正規化等）
- Research（kabusys.research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー
- Strategy / Execution / Monitoring パッケージ用の骨組み（拡張可能）

---

## 前提 / 必要環境

- Python 3.10 以上（型注釈で `X | Y` 構文を使用）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）

インストール（例）
```bash
python -m pip install duckdb defusedxml
# パッケージとして利用する場合（setup があれば）
# python -m pip install -e .
```

---

## 環境変数（主なもの）

以下はこのライブラリが参照する主要な環境変数です。プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須（未設定時に例外が発生します）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack のチャンネル ID

オプション
- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト `development`）
- LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト `INFO`）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト `data/monitoring.db`）

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python 環境を用意（仮想環境推奨）
2. 依存パッケージをインストール
   - duckdb, defusedxml など
3. プロジェクトルートに `.env` を配置（上記の必要変数を設定）
4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで以下を実行：
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# 監査用スキーマを追加する場合
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

---

## 使い方（代表的な例）

- 日次 ETL（株価・財務・カレンダーの差分取得、品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を省略すると today を対象に実行
print(result.to_dict())
```

- 個別 ETL（価格のみ）
```python
from kabusys.data.pipeline import run_prices_etl, get_last_price_date
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched} saved={saved}")
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄コードの集合。DB から取得して渡すのが一般的。
known_codes = {"7203", "6758", "9433"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- J-Quants クライアントを直接利用して取得・保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
```

- ファクター計算 / 研究用関数
```python
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
target = date(2024, 1, 31)

momentum = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
# 例: モメンタム mom_1m と 翌日リターン fwd_1d の IC を計算
ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(momentum, ["mom_1m", "mom_3m", "ma200_dev"])
normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## よくある注意点 / トラブルシューティング

- 環境変数が未設定だと Settings のプロパティ呼び出し時に ValueError が出ます。`.env.example` を参照して `.env` を作成してください（プロジェクトルート）。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml のある場所）を基に行われます。テスト時に自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API はレート制限があります（120 req/min）。jquants_client は内部でスロットリングとリトライを行いますが、短時間に大量のリクエストを投げると API 側で制限される可能性があります。
- RSS フィード取得では SSRF や XML Bomb 対策が実装されています。社内プロキシや特殊な環境では適宜検討してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル／モジュール構成です（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境設定読み込み / settings
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得 / 保存）
    - news_collector.py       — RSS ニュース収集・前処理・DB保存
    - schema.py               — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - features.py             — 特徴量ユーティリティ（再エクスポート）
    - stats.py                — 統計ユーティリティ（zscore_normalize 等）
    - calendar_management.py  — マーケットカレンダー管理
    - audit.py                — 監査ログスキーマ（signal/order_request/execution）
    - etl.py                  — ETLResult 型の再エクスポート
    - quality.py              — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py  — 将来リターン計算 / IC / summary / rank
    - factor_research.py      — momentum / volatility / value 等のファクター計算
  - strategy/
    - __init__.py            — 戦略モジュール用のパッケージ化ポイント
  - execution/
    - __init__.py            — 発注・実行関連モジュール用のパッケージ化ポイント
  - monitoring/
    - __init__.py            — 監視関連のパッケージ化ポイント

（上記以外にも多くの補助関数・ユーティリティ関数が実装されています。詳細は各ファイルの docstring を参照してください。）

---

## 開発者向けメモ

- 型アノテーション・docstring を重視して設計されています。関数の入力に DuckDB の接続オブジェクトを受け取る設計が多く、テスト時はインメモリ DB (`":memory:"`) を用いたユニットテストが可能です。
- 外部依存（pandas 等）を避ける方針のため、内部実装は標準ライブラリと duckdb で完結するようになっています。
- ETL やニュース収集は外部 API・ネットワークを伴うため、ユニットテストではネットワーク呼び出しをモックすることを推奨します（各モジュールはテスト時に差し替え可能な設計がされている箇所があります）。

---

必要であれば、README にサンプル .env.example、より詳細な API リファレンス（関数一覧／引数説明）や CLI スクリプト（ラッパー）追加の雛形を作成します。どの部分を詳しく記載したいか教えてください。