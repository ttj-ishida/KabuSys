# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、DuckDBベースのスキーマ管理、ETLパイプライン、データ品質チェック、ニュース収集、ファクター（リサーチ）計算、監査ログなど、アルファ探索から実運用に必要な機能群を含みます。

バージョン: 0.1.0

---

## 主要機能

- データ取得
  - J-Quants API クライアント（ページネーション対応、レートリミット制御、トークン自動リフレッシュ、リトライ）
  - 株価日足 / 財務データ / 市場カレンダーの取得・保存
- データレイヤー（DuckDB）
  - Raw / Processed / Feature / Execution 層のスキーマ定義と初期化
  - 監査ログ用スキーマ（signal/order/execution トレース）
- ETLパイプライン
  - 差分更新、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次ETLの統合エントリポイント
- ニュース収集
  - RSS フィードの安全な取得（SSRF対策、XML脆弱性対策、gzip上限、トラッキングパラメータ除去）
  - raw_news 保存、銘柄コード抽出と news_symbols への紐付け
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を直接参照）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ
- その他
  - 環境変数設定読み込み（`.env` / `.env.local` 自動ロード、プロジェクトルート検出）
  - ロギングレベル・運用モード（development / paper_trading / live）管理

---

## 必要条件

- Python 3.10 以上（型ヒントや Union 型記法を利用）
- 必要な Python パッケージ（代表）:
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API / RSS フィード）

実際のプロジェクトでの要件は setup/pyproject 等で管理してください。

---

## 環境変数（主なもの）

このパッケージは環境変数から設定を読み込みます（`.env` / `.env.local` をプロジェクトルートに置くことを想定）。自動読み込みはデフォルトで有効です。無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション等の API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — `development` | `paper_trading` | `live`（デフォルト: development）
- LOG_LEVEL — `DEBUG` | `INFO` | `WARNING` | `ERROR` | `CRITICAL`（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

注意: 必須変数が欠けている場合、Settings プロパティアクセスで ValueError を送出します。

---

## セットアップ手順（開発向け）

1. リポジトリをクローン／配置
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （実際のパッケージ一覧があればそれを利用してください）
4. プロジェクトルートに `.env`（および必要なら `.env.local`）を作成し、環境変数を設定
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
5. DuckDB スキーマを初期化
   - Python REPL またはスクリプトから下記を実行:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")

---

## 使い方（例）

基本的なデータ初期化と日次ETL実行の例:

```python
from datetime import date
from kabusys.data import schema, pipeline

# DB 初期化（ファイルなければ作成）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次ETL を実行（target_date を省略すると今日）
result = pipeline.run_daily_etl(conn, target_date=date.today())

print(result.to_dict())  # ETL 実行結果のサマリ
```

J-Quants からデータを直接取得したい場合:

```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

# トークンは Settings 経由で自動取得（環境変数 JQUANTS_REFRESH_TOKEN 必須）
quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(quotes))
```

ニュース収集ジョブの例:

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄リスト（例: set(["7203","6758"])）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
print(res)
```

リサーチ / ファクター計算例:

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2024, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m","mom_3m","mom_6m"])
```

品質チェック（ETL後に呼ぶ）:

```python
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

監査スキーマ初期化（監査専用DBを使う場合）:

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 自動 .env 読み込みについて

- パッケージ起動時に `.env` / `.env.local` をプロジェクトルートから自動で読み込みます（プロジェクトルートは .git もしくは pyproject.toml を探索して決定）。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で便利です）。

---

## ディレクトリ構成（主要ファイルと説明）

（パッケージルート: src/kabusys）

- __init__.py
  - パッケージのバージョンと公開モジュール一覧
- config.py
  - 環境変数読み込みと Settings クラス（J-Quants / kabu API / Slack / DB パス / env 等）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py — RSS ニュース収集、前処理、DB 保存、銘柄抽出
  - schema.py — DuckDB スキーマ定義と init_schema / get_connection
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - pipeline.py — ETL パイプライン（差分更新、run_daily_etl 等）
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management.py — market_calendar 管理・営業日判定ロジック・calendar_update_job
  - etl.py — ETLResult エクスポート
  - audit.py — 監査ログ（signal/order/execution）スキーマの初期化ユーティリティ
- research/
  - __init__.py — 研究用関数のエクスポート（calc_momentum 等）
  - factor_research.py — Momentum/Volatility/Value 等のファクター計算
  - feature_exploration.py — 将来リターン計算、IC、factor_summary、rank
- strategy/ (空の __init__.py があり、戦略実装を追加する想定)
- execution/ (空の __init__.py があり、発注実装を追加する想定)
- monitoring/ (空の __init__.py)

README に記載のない内部関数やユーティリティも多数あり、上記は主要な公開インターフェースの抜粋です。

---

## 運用上の注意点

- J-Quants の API レート制限（120 req/min）を厳守するため、クライアント側で固定間隔のスロットリングを実装しています。
- API 呼び出しはリトライ・指数バックオフを行い、401 発生時には自動でトークンを更新して1回リトライします。
- DuckDB に対する INSERT/UPDATE は冪等性（ON CONFLICT）を意識した実装です。
- ニュース収集では SSRF や XML 攻撃対策（defusedxml）等の安全処理を行っています。
- 本ライブラリはデータ処理・研究用途を主眼としており、実際の発注ロジックやブローカー連携は strategy / execution 層で具体化する必要があります。live 運用時は必ず sandbox/paper_trading で十分な確認を行ってください。

---

## 貢献・拡張

- strategy / execution / monitoring の各モジュールは拡張ポイントです。独自の戦略やブローカー接続の実装を追加して利用してください。
- スキーマや ETL の振る舞いを変更する場合は DuckDB DDL を更新し、互換性を考慮してマイグレーションを用意してください。

---

質問や README の補足が必要であれば、利用シナリオ（例: 「ETL を毎朝 cron で回したい」「Slack に ETL 結果を通知したい」など）を教えてください。具体的な実行例や運用手順を追加で作成します。