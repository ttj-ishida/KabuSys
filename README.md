# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得・ETL、特徴量計算、リサーチユーティリティ、監査用スキーマなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は J-Quants 等のデータソースから株価・財務・カレンダー・ニュースを取得して DuckDB に保存し、戦略用の特徴量計算や品質チェック、監査ログのためのスキーマを備えた日本株自動売買システム向けの基盤モジュール群です。  
設計方針として、本番の発注APIへの直接アクセスを避け、DuckDB を中心に冪等性・トレーサビリティ・Look-ahead-bias 回避を重視しています。

主な提供機能は以下です。

---

## 機能一覧

- 環境設定読み込み・管理（.env 自動読み込み、必須環境変数チェック）
- J-Quants API クライアント
  - トークン取得（自動リフレッシュ）
  - 日足・財務・マーケットカレンダーのページネーション対応取得
  - レート制限・リトライ・指数バックオフ対応
  - DuckDB へ冪等保存（ON CONFLICT / DO UPDATE）
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン
  - 差分更新（最終取得日に基づく差分取得とバックフィル）
  - 市場カレンダー先読み
  - 品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS）
  - URL 正規化・トラッキングパラメータ除去、SSRF 対策、gzip 制限、XML 安全パース
  - raw_news 保存と銘柄コードの抽出・紐付け
- リサーチ用ファクター計算
  - モメンタム（1/3/6ヶ月、MA200 乖離）
  - ボラティリティ（20日 ATR、出来高比率等）
  - バリュー（PER / ROE）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（signal / order_request / execution）用スキーマと初期化ユーティリティ
- マーケットカレンダー管理（営業日判定、next/prev_trading_day、calendar 更新ジョブ）

---

## 必要条件（推奨）

- Python 3.9+（typing での型ヒントを多数利用）
- DuckDB
- defusedxml

（プロジェクトの pyproject.toml / requirements.txt があればそちらを参照してインストールしてください）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# またはプロジェクトに requirements.txt があれば:
# pip install -r requirements.txt
```

---

## 環境変数 / .env

KabuSys は起動時にプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索し、`.env` と `.env.local` を自動で読み込みます（OS 環境変数を優先）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に必要な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）

例 `.env`（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

コード内での取得例:
```py
from kabusys.config import settings
token = settings.jquants_refresh_token
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成・依存ライブラリインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   # もし pyproject.toml / requirements.txt があるならそちらでインストール
   ```

3. 環境変数設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数を設定

4. DuckDB スキーマ初期化
   Python から:
   ```py
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # ファイルパスまたは ":memory:"
   ```

5. （任意）監査DB初期化:
   ```py
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表的な例）

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
```py
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブの実行
```py
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コードセット（抽出精度向上）
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)
```

- J-Quants から日足を取得して保存（低レベル）
```py
from kabusys.data import jquants_client as jq
import duckdb
from kabusys.config import settings
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
```

- リサーチ / ファクター計算例
```py
from kabusys.data.schema import get_connection
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

conn = get_connection("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2024,1,31))
vol = calc_volatility(conn, target_date=date(2024,1,31))
value = calc_value(conn, target_date=date(2024,1,31))
forwards = calc_forward_returns(conn, target_date=date(2024,1,31))
# IC 計算の例（factor_records と forward_records を code でジョインして評価）
ic = calc_ic(factor_records=momentum, forward_records=forwards, factor_col="mom_1m", return_col="fwd_1d")
```

- スキーマ初期化の注意
  - init_schema() はテーブルを冪等に作成します。既存 DB を上書きしません。
  - ":memory:" を渡すとインメモリ DuckDB を使用します（テスト等に便利）。

---

## 注意事項 / 実装上のポイント

- .env の自動読み込みはプロジェクトルート（.git もしくは pyproject.toml）を基準に行います。CWD に依存しないため、パッケージ配布後でも安定して動作します。
- J-Quants クライアントはレート制限（120 req/min）・リトライ・401 自動リフレッシュを実装しています。アプリ側で追加のスロットリングを行う必要は基本的にありません。
- NewsCollector は SSRF・XML Bomb・gzip 解凍後のサイズ検査などセキュリティを考慮した実装になっています。
- DuckDB に対する保存は基本的に ON CONFLICT / DO UPDATE（冪等）を用いています。
- カレンダー情報がない場合は曜日ベース（単純に土日を非営業日）でのフォールバックを行います。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイル一覧（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - features.py
      - stats.py
      - calendar_management.py
      - etl.py
      - quality.py
      - audit.py
      - audit.py
    - research/
      - __init__.py
      - feature_exploration.py
      - factor_research.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

（各ファイルにはモジュールの詳細な docstring と設計上の注釈が含まれています）

---

## 貢献・開発

- バグ報告や機能提案は Issue にて受け付けてください。
- 開発時は仮想環境を利用し、DuckDB はインメモリ ":memory:" で単体テストを行うと便利です。
- 自動ロードする .env を使いたくないテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

以上が本リポジトリの README です。さらに詳細な使い方（戦略実装例、発注フロー連携、CI/CD 設定等）が必要であれば追記します。