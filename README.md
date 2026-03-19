# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータ収集・ETL・特徴量生成・研究・監査ログを備えた自動売買プラットフォームのコアライブラリです。J-Quants API を用いた市場データ取得、DuckDB を用いたローカルデータベース管理、ニュース収集、データ品質チェック、研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）を提供します。

目次
- プロジェクト概要
- 主な機能
- 動作要件 / 依存関係
- セットアップ手順
- 環境変数（設定項目）
- 使い方（主要な例）
- ディレクトリ構成
- トラブルシューティング / 注意点

---

## プロジェクト概要

このパッケージは、データプラットフォーム（raw → processed → feature）と研究 / 戦略レイヤー、監査ログを備えた日本株自動売買システムの基盤コンポーネントを実装します。主に以下を目的とします。

- J-Quants からの株価・財務・カレンダー取得（レート制御・リトライ・トークンリフレッシュ対応）
- DuckDB による冪等的なデータ永続化（schema 定義・初期化）
- RSS ベースのニュース収集と記事→銘柄紐付け
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ）、IC 計算、Z スコア正規化
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログテーブル（シグナル→発注→約定のトレーサビリティ）

---

## 主な機能（機能一覧）

- data/jquants_client.py
  - J-Quants API クライアント（ページネーション、レート制御、リトライ、トークン自動更新）
  - fetch/save: daily quotes, financial statements, market calendar
- data/schema.py
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution / Audit 層）
  - init_schema(db_path) で初期化（冪等）
- data/pipeline.py
  - 日次 ETL（run_daily_etl）: カレンダー取得 → 株価差分取得 → 財務取得 → 品質チェック
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- data/news_collector.py
  - RSS 取得（安全性対策: SSRF 防止、gzip 制限、XML サニタイズ）
  - 記事正規化・ID 生成（URL 正規化 → SHA-256）、DuckDB 保存（冪等）
  - 銘柄コード抽出・紐付け
- data/quality.py
  - 欠損・スパイク（前日比）・重複・日付不整合チェック
  - run_all_checks でまとめて実行
- data/calendar_management.py
  - 営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - カレンダー更新ジョブ
- data/audit.py
  - 監査ログ（signal_events, order_requests, executions）定義と初期化
- research/
  - factor_research.py: calc_momentum, calc_volatility, calc_value（DuckDB ベース）
  - feature_exploration.py: calc_forward_returns, calc_ic, factor_summary, rank
  - data.stats.zscore_normalize の再利用（クロスセクション Z スコア）

---

## 動作要件 / 依存関係

- Python 3.10 以上（型ヒントで | 演算子を使用）
- 必要パッケージ（代表例）
  - duckdb
  - defusedxml
- ここで示した以外の依存は最小限に抑えられています（標準ライブラリ中心に実装）。

インストール例（開発環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 開発インストール（パッケージ化されていれば）
# pip install -e .
```

プロダクションでは requirements.txt / pyproject.toml に基づくインストールを推奨します。

---

## セットアップ手順

1. リポジトリを取得
   - git clone ...（省略）

2. Python 仮想環境を作成して依存をインストール
   - 上記参照

3. 環境変数（.env）を準備
   - ルートに `.env` または `.env.local` を配置すると、自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. DuckDB スキーマ初期化
   - デフォルト DB パスは環境変数 `DUCKDB_PATH`（デフォルト: `data/kabusys.duckdb`）。
   - 例:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```

---

## 環境変数（主な設定項目）

必須（実行時に ValueError を投げるものがあります）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン（必要に応じて）
- SLACK_CHANNEL_ID: Slack チャネル ID（必要に応じて）
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注連携を行う場合）

任意 / デフォルト付き:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読込を無効化するには "1" を設定
- KABUSYS_*（その他）: DUCKDB_PATH / SQLITE_PATH 等
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 sqlite path（デフォルト data/monitoring.db）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）

設定例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（主要な例）

基本的な流れ: スキーマを初期化 → ETL を実行 → 研究・特徴量生成 → 戦略/発注

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（J-Quants から差分取得して DuckDB に保存）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # settings.jquants_refresh_token が使用される
print(result.to_dict())
```

3) ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection

# known_codes: 銘柄抽出に使う有効な銘柄コード集合（省略可）
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)  # {source_name: 新規挿入件数}
```

4) 研究用ファクター計算例
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

d = date(2024, 1, 4)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

# Z スコア正規化（例: mom_1m と ma200_dev を正規化）
normed = zscore_normalize(mom, ["mom_1m", "ma200_dev"])
```

5) IC / 将来リターンの計算（研究用）
```python
from kabusys.research import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, date(2024,1,4), horizons=[1,5,21])
# factor_records はファクター計算結果（一例: mom）
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

6) 品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=date(2024,1,4))
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## ディレクトリ構成（主要ファイル）

（ルート: src/kabusys 以下）

- __init__.py
- config.py — 環境変数・設定読み込み（.env 自動ロードロジック）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - news_collector.py — RSS 収集・前処理・DB 保存
  - schema.py — DuckDB スキーマ定義・init_schema / get_connection
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - quality.py — データ品質チェック
  - calendar_management.py — 市場カレンダー管理（営業日ロジック）
  - audit.py — 監査ログスキーマ（signal/order/execution）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - features.py — features API リエクスポート
  - etl.py — ETLResult の再エクスポート
- research/
  - __init__.py — 研究 API の再エクスポート
  - feature_exploration.py — 将来リターン・IC・統計要約
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
- strategy/ (空パッケージのエントリポイント)
- execution/ (発注関連のパッケージ入り口)
- monitoring/ (監視関連のパッケージ入り口)

---

## トラブルシューティング / 注意点

- 環境変数の未設定:
  - settings.jquants_refresh_token 等の必須変数がないと ValueError が発生します。`.env` を用意するか OS 環境で定義してください。
- .env 自動読み込み:
  - パッケージはプロジェクトルートを .git または pyproject.toml を基準に探索し、.env/.env.local を読み込みます（CWD に依存しない）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB ファイルのディレクトリ:
  - init_schema は DB ファイルの親ディレクトリを自動作成しますが、パスに書き込み権限が必要です。
- J-Quants API 制限:
  - 本実装は 1 分あたりのリクエスト数制限（120 req/min）に合わせたレート制御とリトライを実装しています。API キー・トークンは厳重に管理してください。
- ネットワーク・セキュリティ:
  - news_collector は SSRF 対策（リダイレクト検査・プライベート IP 拒否）を実装していますが、実行環境のネットワークポリシーにも注意してください。
- DuckDB バージョン依存:
  - 一部の制約（ON DELETE CASCADE 等）は DuckDB のバージョン差分により挙動が異なるため、使用する DuckDB バージョンの互換性に注意してください。

---

必要があれば、この README をベースに「インストール手順（pip / Docker）」「運用手順（cron / CI）」や「開発ガイド（テスト、型チェック）」などの章を追加できます。どの情報を優先して拡張したいか教えてください。