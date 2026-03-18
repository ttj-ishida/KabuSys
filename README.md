# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）の README。  
本リポジトリはデータ取得（J-Quants）、ETL、品質チェック、特徴量生成、研究用ユーティリティ、監査ログ／実行レイヤーのスキーマなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引向けの内部ツール群です。主な目的は以下です：

- J-Quants API からのデータ取得（株価日足・財務・マーケットカレンダー）
- DuckDB を用いたデータレイク（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース（RSS）収集と銘柄紐付け
- 研究（ファクター計算、将来リターン・IC 計算、Zスコア正規化）
- 監査ログ（シグナル→注文→約定のトレースを可能にするスキーマ）

パッケージはモジュール化されており、データ層（kabusys.data）、研究層（kabusys.research）、戦略/実行/監視のための枠組みを含みます。

---

## 主な機能一覧

- データ取得 & 保存
  - J-Quants API クライアント（ページネーション、リトライ、トークン自動リフレッシュ）
  - raw_prices / raw_financials / market_calendar などの冪等保存（ON CONFLICT）
- ETL パイプライン
  - 差分更新、バックフィル、カレンダー先読み、品質チェックの統合実行（run_daily_etl）
- データ品質チェック
  - 欠損、重複、スパイク（前日比急変）、将来日付／非営業日データ検出
- ニュース収集
  - RSS フィード取得、前処理、記事ID生成（URL正規化＋SHA256）、DuckDB 保存、銘柄抽出
  - SSRF 対策、gzip/サイズ制限、XML 脆弱性対策（defusedxml）
- 研究用ユーティリティ
  - momentum / volatility / value 等のファクター計算
  - 将来リターン計算、Spearman rank（IC）計算、basic 統計サマリー
  - Zスコア正規化ユーティリティ
- スキーマ管理
  - DuckDB のスキーマ定義と初期化（init_schema）
  - 監査ログスキーマ（init_audit_schema / init_audit_db）

---

## 要件（推奨）

- Python 3.8+
- パッケージ依存（例）
  - duckdb
  - defusedxml
- 標準ライブラリの urllib / datetime / logging 等を使用

（実行環境に応じて適切なバージョンを選んでください）

---

## セットアップ手順

1. リポジトリをチェックアウト／クローン

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じて）pip install -e . で開発インストール

4. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（デフォルト）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DuckDB スキーマ初期化（例は後述）

---

## 環境変数（必須・任意）

kabusys.config.Settings で参照される主な環境変数：

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注系利用時）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID（通知先）

任意（デフォルト値あり／設定推奨）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live。デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL。デフォルト: INFO）

例（.env）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 初期化（DuckDB スキーマ）

DuckDB のスキーマを初期化する最小手順例（Python REPL / スクリプト）：

```python
from kabusys.data.schema import init_schema
# デフォルトパスを使う場合は settings.duckdb_path を参照しても良い
conn = init_schema("data/kabusys.duckdb")
```

監査ログ専用 DB を初期化する場合：

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
```

既存接続に監査スキーマを追加する場合：

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

---

## 使い方（代表的な例）

- ETL（日次パイプライン）実行例：

```python
from datetime import date
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（既に初期化済みなら get_connection でも可）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2024, 1, 1))
print(result.to_dict())
```

- 市場カレンダー更新ジョブ：

```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

- RSS ニュース収集（既知銘柄 set を渡して銘柄紐付け）：

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
known_codes = {"7203", "6758", "9984"}  # 例
result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(result)
```

- 研究用ファクター計算（例: momentum）：

```python
from datetime import date
from kabusys.research import calc_momentum

recs = calc_momentum(conn, target_date=date(2024, 1, 1))
# recs は [{"date":..., "code":..., "mom_1m":..., "ma200_dev":...}, ...]
```

- 将来リターン・IC 計算の流れ：

```python
from kabusys.research import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, target_date=date(2024,1,1), horizons=[1,5,21])
# factor_records は calc_momentum などの出力
ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

- Zスコア正規化：

```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, columns=["mom_1m", "mom_3m"])
```

---

## ロギング / 実行環境

- 環境変数 `LOG_LEVEL` と `KABUSYS_ENV` を用いてログ・実行モードを制御します。
  - KABUSYS_ENV の有効値: `development`, `paper_trading`, `live`
- 自動で `.env` / `.env.local` を読み込む仕組みがあります（プロジェクトルートを .git か pyproject.toml を基準に探索）。
  - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内のおおまかな構成（src/kabusys 以下）です。主要モジュールと簡単な説明を併記します。

- src/kabusys/
  - __init__.py  — パッケージ初期化（公開モジュールの定義）
  - config.py    — 環境変数 / 設定管理（Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py  — RSS フィード収集・前処理・保存
    - schema.py          — DuckDB スキーマ定義・初期化（init_schema）
    - stats.py           — 統計ユーティリティ（zscore_normalize）
    - pipeline.py        — ETL パイプライン（run_daily_etl 他）
    - features.py        — 特徴量ユーティリティ（再エクスポート）
    - calendar_management.py — マーケットカレンダー管理 / 更新ジョブ
    - audit.py           — 監査ログスキーマ・初期化
    - etl.py             — ETL インターフェース（ETLResult 再エクスポート）
    - quality.py         — データ品質チェック
  - research/
    - __init__.py        — 研究ユーティリティ再エクスポート
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
    - factor_research.py — ファクター計算（momentum / volatility / value）
  - strategy/            — 戦略実装（ボイラープレート）
  - execution/           — 発注 / 実行管理（枠組み）
  - monitoring/          — 監視関連（空の __init__ など）

（上記はコードベースから抜粋した主要ファイルです。詳細はソースツリーを参照してください。）

---

## 開発・拡張に関する注意点

- DuckDB への保存は多くの箇所で冪等性（ON CONFLICT）を担保していますが、スキーマ変更時は既存データとの整合性を確認してください。
- ネットワーク呼び出し（J-Quants / RSS 等）はリトライやサイズ制限、SSRF 対策など防御的な実装が含まれます。外部アクセス時の権限管理には注意してください。
- 実取引（live）モードで発注を行う場合は、KABU_API の設定や認証情報、運用ルールを十分に検証してください。

---

## サポート / 貢献

不具合報告や改善提案は Issue を作成してください。Pull Request を歓迎します。コードスタイルやテストはリポジトリの CONTRIBUTING ガイドラインに従ってください（存在する場合）。

---

以上。必要であれば README にサンプル .env.example を付ける、CI 実行方法、さらに具体的なコードスニペット（発注フロー等）を追加します。どの部分を詳しく追加したいか教えてください。