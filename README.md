# KabuSys

KabuSys は日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants や kabuステーション 等からデータを取得して DuckDB に蓄積し、戦略用の特徴量計算、品質チェック、監査ログ、ニュース収集などを提供します。

バージョン: 0.1.0

## 概要

主な目的は以下です。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する（差分取得／冪等保存）。
- RSS を用いたニュース収集とテキスト前処理、銘柄紐付け。
- データ品質チェック（欠損・重複・スパイク・日付矛盾など）。
- 戦略用のファクター計算（モメンタム、ボラティリティ、バリュー等）と研究（IC 計算等）。
- 発注 / 監査ログ用のスキーマ（監査トレースを UUID 連鎖で保持）。

設計方針は「実運用を想定した堅牢性／可観測性の確保」です（レート制御・再試行、トークン自動更新、SQL パラメータバインド、SSRF 対策、Gzip/サイズ制限 等）。

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（fetch / save）: prices, financials, market calendar
  - 差分 ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - DuckDB スキーマ初期化（init_schema / get_connection）
- データ品質管理
  - 欠損データ / 重複 / スパイク / 日付不整合 検出（quality モジュール）
  - ETL 実行結果の集約（ETLResult）
- ニュース収集
  - RSS 取得・前処理（URL 正規化、トラッキングパラメータ除去、SSRF 対策）
  - raw_news / news_symbols への冪等保存
  - 記事 -> 銘柄コード抽出（4 桁コード）
- 研究・特徴量
  - calc_momentum, calc_volatility, calc_value（research.factor_research）
  - 将来リターン計算 / IC（Information Coefficient）計算 / 統計サマリー（research.feature_exploration）
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）
- 監査ログ
  - signal_events / order_requests / executions 等の監査テーブル初期化（init_audit_schema / init_audit_db）
- 設定管理
  - 環境変数/.env 自動ロード（config.Settings からアクセス）

## セットアップ手順

前提: Python 3.9+（typing の Union 表記等を利用するため 3.9 以上を推奨）

1. リポジトリをクローン、もしくはパッケージを配置
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール

推奨パッケージ（主要依存のみ）:
- duckdb
- defusedxml

例:
```
pip install duckdb defusedxml
# またはプロジェクトに requirements.txt があれば:
# pip install -r requirements.txt
```

4. 環境変数を設定する（.env をプロジェクトルートに置くことが可能）。必須となる主な変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルトは development
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）。デフォルト INFO
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）

.env 自動ロードについて:
- パッケージインポート時にプロジェクトルート（.git または pyproject.toml を探索）から `.env` と `.env.local` を自動で読み込みます。
- 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. データベーススキーマ初期化例:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

## 使い方（主要な例）

- DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # ファイルが存在しなければ作成
```

- 日次 ETL の実行（市場カレンダー・株価・財務 and 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # 戻り値は ETLResult
print(result.to_dict())
```

- 個別 ETL（差分取得）
```python
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
from datetime import date

fetched, saved = run_prices_etl(conn, date.today())
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes: 銘柄抽出に使用する有効コードの集合（例: set(["7203","6758"])）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
print(results)  # {source_name: new_count, ...}
```

- ファクター計算（研究 / 戦略用）
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
from datetime import date

mom = calc_momentum(conn, date(2025, 1, 31))
vol = calc_volatility(conn, date(2025, 1, 31))
val = calc_value(conn, date(2025, 1, 31))

fwd = calc_forward_returns(conn, date(2025, 1, 31))
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

- Z スコア正規化
```python
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m", "mom_3m"])
```

- 監査ログスキーマ初期化（監査専用 DB を使う場合）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

注意点:
- J-Quants API はレート制限（120 req/min）や一部 HTTP ステータスでのリトライロジックを内蔵しています。ID トークンが 401 のときは自動リフレッシュします。
- ニュース取得は SSRF 対策・サイズチェック・gzip 解凍上限等の安全対策を実装しています。
- DuckDB への保存は基本的に ON CONFLICT（冪等）です。

## ディレクトリ構成

ソースは `src/kabusys` 以下に配置されています。主要ファイル・モジュールと役割を示します。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定の読み込み・管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント、取得・保存ロジック、レート制御、リトライ、トークン管理
    - news_collector.py — RSS 取得・前処理・保存・銘柄抽出
    - schema.py — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - pipeline.py — ETL パイプライン（差分取得・品質チェックの統合）
    - features.py — features 用の公開インターフェース（zscore の再エクスポート）
    - calendar_management.py — market_calendar の管理、営業日計算ユーティリティ
    - audit.py — 監査ログスキーマ（signal_events / order_requests / executions）と初期化
    - etl.py — ETLResult の公開（pipeline から再エクスポート）
    - quality.py — データ品質チェックの実装（欠損・重複・スパイク・日付不整合）
  - research/
    - __init__.py — 研究用関数の再エクスポート
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー、rank
    - factor_research.py — モメンタム・ボラティリティ・バリューなどファクター計算
  - strategy/ — 戦略関連（将来的な拡張ポイント）
  - execution/ — 発注 / ブローカ連携（将来的な拡張ポイント）
  - monitoring/ — 監視・メトリクス（未実装/拡張ポイント）

（上記は本リポジトリに含まれる主要モジュールの抜粋です）

## 環境変数一覧（まとめ）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（例 data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（例 data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化

## 開発 / テストに関するヒント

- 自動 .env 読み込みを無効にしてテスト時に独自環境を設定したい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - その後テストコード内で適切に os.environ を設定してください。
- DuckDB のインメモリ DB を使いたい場合は db_path に ":memory:" を渡せます（init_schema(":memory:")）。
- 外部 API 呼び出し（J-Quants / RSS）をテストする際は jquants_client._request や news_collector._urlopen をモックする設計を想定しています。

---

必要ならば README に追加したいサンプルコードや運用フロー（cron / Airflow / GitHub Actions での ETL スケジューリング例、Slack 通知例）を作成します。どの情報を優先して追加しますか？