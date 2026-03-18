# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けのライブラリ群です。  
データ収集（J-Quants / RSS）、DuckDB ベースのデータレイク、特徴量計算、リサーチユーティリティ、ETL パイプライン、監査ログ用スキーマ、品質チェックなどを提供します。

主な設計方針は「本番口座・発注 API への直接アクセスを最小化」「DuckDB を中心にした冪等（idempotent）設計」「Look‑ahead bias 回避のための取得時刻トレーシング」「軽量で外部依存を限定すること」です。

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック（Settings）
- データ取得（J-Quants API クライアント）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダー取得
  - レート制限、リトライ、トークン自動リフレッシュ、ページネーション対応
  - DuckDB への冪等保存機能（ON CONFLICT）
- ETL パイプライン
  - 差分更新、バックフィル、カレンダー先読み、品質チェックとの連携
  - 日次 ETL エントリポイント（run_daily_etl）
- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution / Audit 階層のテーブル定義
  - スキーマ初期化ユーティリティ（init_schema, init_audit_schema 等）
- ニュース収集
  - RSS フィード収集、前処理、記事ID生成（URL正規化＋SHA256）、SSRF 対策、gzip・サイズ制限
  - raw_news / news_symbols への冪等保存
- リサーチ / 特徴量
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - Z スコア正規化ユーティリティ
- データ品質チェック
  - 欠損、重複、日付不整合、スパイク検出
  - 問題を QualityIssue オブジェクトで返却
- 監査（Audit）ログ
  - signal → order_request → execution を追跡できる監査テーブル群

---

## 動作環境 / 前提

- Python 3.10 以上（typing の `X | Y` 構文を使用）
- 推奨ライブラリ（必須）
  - duckdb
  - defusedxml
- （その他）ネットワーク経由で J-Quants API / RSS にアクセスするため適切なネットワーク環境と API トークンが必要

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージを editable install する場合（プロジェクトルートに pyproject.toml がある想定）
pip install -e .
```

---

## 環境変数 / .env

Settings クラスは環境変数から設定を読みます。自動でプロジェクトルート（.git または pyproject.toml を探索）から `.env` → `.env.local` をロードします。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（必須は README 上で明示）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API 用パスワード
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — one of "development", "paper_trading", "live"（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG / INFO / WARNING / ERROR / CRITICAL

簡易 .env.example:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token_here

# kabu API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB paths (任意)
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. 仮想環境を作成して依存をインストール（上記参照）
3. `.env` を作成して必要な環境変数を設定
4. DuckDB スキーマ初期化:
   - data ディレクトリを自動で作成してくれます
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
5. （監査用に別 DB を用意する場合）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（代表的な例）

- 日次 ETL（市場カレンダー / 日足 / 財務 / 品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（初回のみ）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL 実行（対象日を指定する場合）
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は抽出に使う有効な銘柄コード集合（省略可）
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)  # {source_name: saved_count, ...}
```

- ファクター計算（モメンタム / ボラティリティ / バリュー）
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

mom = calc_momentum(conn, target_date=date(2024, 1, 31))
vol = calc_volatility(conn, target_date=date(2024, 1, 31))
val = calc_value(conn, target_date=date(2024, 1, 31))
```

- 将来リターン計算・IC 計算
```python
from kabusys.research import calc_forward_returns, calc_ic, zscore_normalize

fwd = calc_forward_returns(conn, target_date=date(2024, 1, 31), horizons=[1,5,21])
# factor_records は例えば calc_momentum の結果を使う
ic = calc_ic(factor_records=mom, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
```

- Z スコア正規化（クロスセクション）
```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "ma200_dev"])
```

- 品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)  # target_date を指定して部分チェックも可能
for i in issues:
    print(i)
```

---

## 自動ロード / 注意点

- config.py はプロジェクトルート（.git または pyproject.toml）を起点に `.env` / `.env.local` を自動で読み込みます。CI やユニットテストで自動ロードを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を環境変数に設定してください。
- Settings のプロパティ（必須変数）を利用する関数は、未設定時に `ValueError` を投げます。実行前に必須環境変数を設定してください。
- J-Quants API へのリクエストにはレート制限があるため、大量取得時はモジュールの RateLimiter と retry ロジックに従います。
- DuckDB の `:memory:` を指定するとインメモリ DB として動作します（テスト用に便利）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 + 保存）
    - news_collector.py     — RSS -> raw_news / news_symbols
    - schema.py             — DuckDB スキーマ、init_schema / get_connection
    - stats.py              — zscore_normalize 等の統計ユーティリティ
    - pipeline.py           — ETL パイプライン（run_daily_etl など）
    - features.py           — features 公開インターフェース
    - calendar_management.py — 市場カレンダー管理ユーティリティ
    - audit.py              — 監査ログスキーマ初期化
    - etl.py                — ETL 用の再エクスポート（ETLResult 等）
    - quality.py            — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py — 将来リターン / IC / summary / rank
    - factor_research.py     — momentum / volatility / value の計算
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

各モジュールはできるだけ小さく責務を分離しています（例: data/jquants_client は API 通信と DuckDB 保存、data/schema は DDL 定義と初期化のみ）。

---

## 開発・貢献

- テスト・CI の簡易化のため、config の自動 .env ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。
- 新しい機能はまずユニットテストを追加し、DuckDB の `:memory:` を使ったテストを推奨します。
- 他の貢献ポリシーやライセンス表記はリポジトリルートに追加してください（この README はコードベースに合わせた概要説明です）。

---

この README は現行のコードベース（data / research / news_collector / jquants_client / pipeline / schema / quality / audit 等）に基づいて作成しています。実運用では API トークンの管理、Slack 通知や発注周りの安全性（フロントランニング対策、注文検証など）、モニタリング・アラート設定を適切に行ってください。