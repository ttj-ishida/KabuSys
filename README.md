# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ収集（J-Quants）、データ品質チェック、DuckDB スキーマ管理、特徴量計算、リサーチユーティリティなどを備え、戦略・発注層と連携できるよう設計されています。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的は「日本株のデータパイプラインとリサーチ機能を備えた基盤ライブラリ」を提供することです。  
設計方針として以下を重視しています。

- DuckDB を用いたローカルデータベース（Raw / Processed / Feature / Execution 層）の提供
- J-Quants API からの差分取得・レート制御・リトライ・トークン自動更新
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策・トラッキング除去）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用に外部依存を抑えたファクター計算（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ

---

## 機能一覧（主なモジュール）

- kabusys.config
  - .env 自動ロード（プロジェクトルート基準、無効化可）
  - 必須環境変数の取得ラッパー（settings）
  - 環境: development / paper_trading / live、ログレベル検証
- kabusys.data
  - jquants_client: J-Quants API クライアント（ページネーション、レート制御、リトライ、id_token の自動リフレッシュ）
  - news_collector: RSS フィード収集、正規化、DuckDB への冪等保存、銘柄抽出
  - schema: DuckDB のスキーマ定義と初期化（raw / processed / feature / execution 層）
  - pipeline / etl: 差分 ETL（市場カレンダー・株価・財務）と run_daily_etl の実装
  - quality: データ品質チェック（欠損、スパイク、重複、日付整合性）
  - calendar_management: JPX カレンダー管理 / 営業日判定ユーティリティ
  - audit: 監査ログテーブルと初期化ユーティリティ（order_request の冪等性等）
  - stats: zscore_normalize などの統計ユーティリティ
- kabusys.research
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー
- kabusys.strategy / kabusys.execution / kabusys.monitoring
  - プレースホルダ（将来的な戦略・発注・監視ロジック用）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の `|` や標準ライブラリの型注釈を利用）
- Git（プロジェクトルートの検出に使用）

推奨パッケージ（必須/主要）:
- duckdb
- defusedxml

例: 仮想環境作成とインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 開発中はプロジェクトを editable install する場合:
pip install -e .
```

環境変数（最低限設定が必要なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- SLACK_BOT_TOKEN        : Slack 通知を使う場合（必須）
- SLACK_CHANNEL_ID       : Slack チャンネル ID（必須）
- KABU_API_PASSWORD      : kabuステーション API を使用する場合（必須）
- (オプション) DUCKDB_PATH: デフォルトは data/kabusys.duckdb
- (オプション) SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- (オプション) KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- (オプション) LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

.env の自動読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml）を探して `.env` と `.env.local` を自動で読み込みます。
- テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

例: 最小 .env（実際は .env.example を参照して設定してください）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

以下は代表的な操作のサンプルコードです。実行は Python スクリプトやコンソールで行います。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数から取得される
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL 実行（J-Quants から差分取得して保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes: 抽出対象の有効な銘柄コードセット（例: 全上場コード）
known_codes = {"7203", "6758", "9984", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

4) ファクター計算（研究用）
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
t = date(2024, 1, 31)
mom = calc_momentum(conn, t)
vol = calc_volatility(conn, t)
val = calc_value(conn, t)
fwd = calc_forward_returns(conn, t, horizons=[1,5,21])

# IC の例（mom_1m と fwd_1d の相関）
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

5) 監査スキーマ初期化（監査ログ専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

注意点
- jquants_client の API 呼び出しはレート制限（120 req/min）を守るために内部でスロットリングされます。
- get_id_token は settings.jquants_refresh_token を使用します。環境変数を正しく設定してください。
- ETL やニュース収集はトランザクションやエラーハンドリングを組み込んでいますが、運用時はログや監視を適切に構成してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント（fetch/save）
  - news_collector.py             — RSS ニュース収集 / 保存 / 銘柄抽出
  - schema.py                     — DuckDB スキーマ定義 & init_schema / get_connection
  - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
  - etl.py                        — ETLResult 再エクスポート
  - quality.py                    — データ品質チェック
  - calendar_management.py        — JPX カレンダー管理 / 営業日ユーティリティ
  - audit.py                      — 監査ログスキーマ初期化
  - stats.py                      — zscore_normalize 等の統計ユーティリティ
  - features.py                   — 特徴量ユーティリティの公開インターフェース
- research/
  - __init__.py
  - factor_research.py            — momentum/volatility/value 等の算出
  - feature_exploration.py        — 将来リターン計算 / IC / summary / rank
- strategy/                        — 戦略層プレースホルダ
- execution/                       — 発注層プレースホルダ
- monitoring/                      — 監視関連プレースホルダ

その他:
- pyproject.toml (想定)
- .env / .env.local (環境変数設定)

---

## 運用上の注意 / ベストプラクティス

- 本番 (live) 環境では KABUSYS_ENV=live を設定し、発注ロジックは十分な検証を行ってから運用してください（現コードベースでは発注モジュールはプレースホルダです）。
- .env ファイルに秘匿情報（トークン・パスワード）を平文で置く場合はアクセス制限に注意してください。CI ではシークレットストアを利用することを推奨します。
- テスト時に自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB は単一ファイル DB なのでバックアップ・管理を運用ルールとして定めてください。
- news_collector の HTTP フェッチは SSRF 防止やレスポンスサイズ制限を行っていますが、公開 RSS のみを対象にするなど運用時にソースを管理してください。

---

## 貢献 / 開発

- コードは src/ 配下で構成されています。ローカルで開発する場合は pip install -e . を推奨します。
- 新しい ETL ジョブやチェックを追加する場合は、既存の duckdb スキーマとの互換性（主キー・制約）とトランザクションの扱いに注意してください。
- ロギングは各モジュールで行っています。デバッグ時は LOG_LEVEL=DEBUG を設定してください。

---

必要であれば、README に次の情報も追記できます:
- 詳細な .env.example のテンプレート
- 実運用の ETL スケジューリング例（cron / Airflow）
- DuckDB スキーマの ER 図やテーブル一覧の詳細説明
- テストの実行方法（ユニットテスト / CI 設定）

追記希望があれば教えてください。