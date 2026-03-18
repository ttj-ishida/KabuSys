# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータ取得、ETL、特徴量生成、リサーチ、発注・監査までを想定したモジュール群を提供する自動売買基盤のプロトタイプです。モジュールは責務ごとに分離されており、データ収集（J‑Quants）、ニュース収集、DuckDB によるデータ保管・スキーマ、品質チェック、特徴量・ファクター計算、監査ログ等の機能を含みます。

主な設計方針:
- DuckDB を中心としたローカルデータプラットフォーム
- API レート制御・リトライ・トークン自動更新（J‑Quants）
- ETL は差分取得／冪等保存（ON CONFLICT）を前提
- リサーチ機能は本番発注 API にアクセスしない（安全）
- セキュリティ考慮（RSS の SSRF 対策等）

---

## 機能一覧

- 環境変数／.env 管理（自動読み込み、.env.local 上書き）
- J‑Quants API クライアント（株価・財務・カレンダー取得）
  - 固定間隔レートリミッタ、リトライ、401 時のトークンリフレッシュ対応
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得 → 保存 → 品質チェック）
- ニュース収集（RSS）と前処理・記事ID生成・銘柄抽出
  - SSRF 対策、gzip 対応、トラッキングパラメータ除去
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- リサーチ用ファクター計算（Momentum / Volatility / Value 等）
- 特徴量正規化ユーティリティ（Zスコア）
- 監査ログ（signal / order_request / executions）スキーマ
- マーケットカレンダー管理（営業日判定、next/prev 取得）
- 監視・実行用モジュール（骨組み）

---

## 必要条件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

（プロジェクトの packaging / requirements ファイルがある場合はそちらを参照してください）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# その他、実行時に必要なライブラリを追加してください
```

---

## 環境変数

必須（実行する機能に応じて必要）:
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注機能使用時）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID

任意 / デフォルト:
- KABUSYS_ENV — 実行環境 ("development" / "paper_trading" / "live")、デフォルト "development"
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)、デフォルト "INFO"
- DUCKDB_PATH — DuckDB のデータベースパス（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト "data/monitoring.db"）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動ロードを無効化（テスト用）

読み込み順:
- OS 環境変数 > .env.local > .env
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して .env を読み込みます。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（簡易）

1. リポジトリをチェックアウト
2. 仮想環境作成 & 依存パッケージをインストール
3. 環境変数を設定（もしくはプロジェクトルートに .env/.env.local を配置）
4. DuckDB スキーマを初期化

例:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# .env に DUCKDB_PATH を設定している想定
conn = init_schema(settings.duckdb_path)
```

---

## 使い方（主要ユースケース）

以下は典型的なスクリプト例です。各関数は duckdb 接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。

1) DuckDB の初期化と日次 ETL の実行
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)   # ファイルがなければ作成・スキーマ初期化
result = run_daily_etl(conn)               # 今日を対象に ETL を実行
print(result.to_dict())
```

2) ニュース収集ジョブの実行（既知銘柄リストで銘柄抽出）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203","6758","9984"}  # 例: 有効な銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

3) J‑Quants からの日足取得（クライアント直接利用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を利用して id_token を取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(records))
```

4) ファクター計算・IC 計算（研究用）
```python
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
target = date(2024,1,31)
factors = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
# Zスコア正規化
normed = zscore_normalize(factors, ["mom_1m","mom_3m","mom_6m"])
```

注意:
- research モジュールは DuckDB の prices_daily / raw_financials 等のテーブルを前提とします。
- ETL や保存処理は冪等（ON CONFLICT）を意識して設計されています。

---

## よく使う API（概要）

- kabusys.config.settings — アプリケーション設定（環境変数アクセス）
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ初期化
- kabusys.data.jquants_client.* — J‑Quants API の fetch_*/save_* 関数
- kabusys.data.pipeline.run_daily_etl — 日次 ETL のエントリポイント
- kabusys.data.news_collector.run_news_collection — RSS からニュースを収集して保存
- kabusys.data.quality.run_all_checks — データ品質チェック一括実行
- kabusys.research.* — ファクター計算・探索（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank）
- kabusys.data.stats.zscore_normalize — クロスセクション Z スコア正規化
- kabusys.data.calendar_management.* — 営業日判定 / カレンダー更新ジョブ
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査ログ初期化

---

## 開発 / テスト時のヒント

- 自動 .env ロードを無効にする:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定
- settings から値を取得する際、必須環境変数が未設定だと ValueError が発生します（例: JQUANTS_REFRESH_TOKEN）。
- DuckDB はインメモリ ":memory:" を使用して単体テストが可能です。
- RSS 処理など外部通信はモックして単体テストを行ってください（news_collector._urlopen を差し替え可能）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py (パッケージ定義, __version__ = "0.1.0")
- config.py (環境変数・設定管理)
- data/
  - __init__.py
  - jquants_client.py (J‑Quants API クライアント & DuckDB 保存)
  - news_collector.py (RSS 収集・前処理・DB 保存)
  - schema.py (DuckDB スキーマ定義 & init_schema)
  - pipeline.py (ETL パイプライン / run_daily_etl 等)
  - etl.py (ETL 用公開インターフェース)
  - features.py (特徴量ユーティリティの再エクスポート)
  - calendar_management.py (マーケットカレンダー管理)
  - quality.py (データ品質チェック)
  - stats.py (zscore_normalize 等)
  - audit.py (監査ログスキーマ初期化)
- research/
  - __init__.py (研究用ユーティリティのエクスポート)
  - feature_exploration.py (forward returns, IC, summary, rank)
  - factor_research.py (momentum/volatility/value 等)
- strategy/
  - __init__.py
  (戦略実装用プレースホルダ)
- execution/
  - __init__.py
  (発注 / 実行周りのプレースホルダ)
- monitoring/
  - __init__.py
  (監視・メトリクス周りのプレースホルダ)

---

## 補足・注意事項

- 本リポジトリは基盤ライブラリの骨組みを提供するもので、実際の発注（本番環境）に用いる場合は十分な検証と安全対策（レート制御、障害時のリカバリ、資金管理、リスク制御等）が必要です。
- J‑Quants / 証券会社 API の利用には各サービスの利用規約を遵守してください。
- 一部の機能（発注連携、Slack 通知等）はこのコードベースに骨組みしか含まれていない場合があります。運用に合わせて具体的な実装を追加してください。

---

必要であれば README を英語版に翻訳したり、各機能ごとの詳細ドキュメント（API リファレンス、設計ドキュメント）を追加します。どの部分を詳しく書くか指定してください。