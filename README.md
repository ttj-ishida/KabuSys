# KabuSys

KabuSys は日本株向けの自動売買 / データ基盤ライブラリです。  
DuckDB をデータストアとして用い、J-Quants API からのデータ取得、ETL パイプライン、データ品質チェック、ファクター計算（リサーチ用）、ニュース収集、監査ログ等を提供します。

バージョン: 0.1.0

---

## 概要

- J-Quants API（株価・財務・市場カレンダー）を安全に取得し、DuckDB に冪等的に保存するクライアント/保存ロジックを提供します。
- 日次 ETL パイプライン（差分取得 + 品質チェック）を実装しています。
- マーケットカレンダー管理、RSS によるニュース収集（SSRF 対策・トラッキング除去・重複排除）を備えます。
- リサーチ用にファクター計算（モメンタム、バリュー、ボラティリティ等）や IC（Information Coefficient）計算、Zスコア正規化などのユーティリティを提供します。
- 発注・監査用のスキーマ（監査ログ、order_requests、executions 等）を用意しています（発注ロジックは別実装を想定）。

設計方針の抜粋:
- DuckDB 上のテーブルのみ参照する（実運用 API に影響を与えない）。
- 冪等性（ON CONFLICT .. DO UPDATE / DO NOTHING）を重視。
- ネットワーク・XML パース・SSRF 等に対する安全策を実装。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント、ページネーション・リトライ・トークン自動再取得、DuckDB 保存ユーティリティ
  - pipeline: 日次 ETL（prices / financials / calendar）と差分取得ロジック
  - schema: DuckDB スキーマ定義と初期化
  - news_collector: RSS 取得・前処理・DB 保存・銘柄抽出
  - calendar_management: 営業日判定、カレンダー更新ジョブ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ用スキーマ（signal_events, order_requests, executions）
  - stats / features: 汎用統計ユーティリティ（zscore_normalize など）
- research/
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー
- config:
  - Settings クラスによる環境変数管理（.env 自動ロード機構を含む）
- monitoring, execution, strategy:
  - 各パッケージのエントリポイント（実装を追加するためのプレースホルダ）

---

## 必要要件

- Python 3.9+（型ヒントにより 3.9 以上を想定）
- 主要依存パッケージ（少なくとも以下が必要）
  - duckdb
  - defusedxml
- （ネットワークアクセスが必要）J-Quants API の利用にはリフレッシュトークンが必要

※ requirements.txt がプロジェクトにある場合はそちらを参照してください。開発環境では `pip install -e .` の前に必要パッケージをインストールしてください。

---

## インストール（開発時）

1. リポジトリをチェックアウト
2. 仮想環境を作成して有効化（任意）
3. 必要パッケージをインストール

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージを開発インストール（プロジェクトルートに pyproject.toml または setup.py があること）
pip install -e .
```

---

## 環境変数と .env の扱い

`kabusys.config.Settings` が環境変数を参照します。自動で `.env` / `.env.local` をプロジェクトルート（.git または pyproject.toml を基準）から読み込みます（ただし OS 環境変数が優先されます）。

自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

重要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注連携等で利用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

その他（任意／デフォルトあり）
- KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL） デフォルト: INFO
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 用パス（モニタリングDB 等。デフォルト: data/monitoring.db）

例 (.env):
```env
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（データベース初期化）

DuckDB スキーマを初期化します。Python REPL またはスクリプト内で実行できます。

例（最も簡単な初期化）:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は .env またはデフォルトを参照します
conn = init_schema(settings.duckdb_path)
# conn を使って ETL 等を実行できます
```

監査ログ専用 DB を初期化する場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主要ユースケース）

1) 日次 ETL の実行（J-Quants から取得して DuckDB に保存 → 品質チェック）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)
print(result.to_dict())  # ETLResult の内容を確認
```

- 引数で `target_date`、`id_token`、`run_quality_checks` などを調整可能です。
- `run_daily_etl` はカレンダー取得 → 価格取得 → 財務取得 → 品質チェックの順で実行します。

2) 市場カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

3) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes: 銘柄抽出に使う有効コードのセット。None の場合は抽出をスキップ。
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
print(results)  # {source_name: saved_count}
```

4) ファクター計算 / リサーチ
```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, zscore_normalize

conn = duckdb.connect(str(settings.duckdb_path))
target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# 将来リターンと IC 計算の例
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
# factor_records は各ファクターの出力リスト。factor_col と return_col を指定して calc_ic を呼ぶ
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)

# Zスコア正規化
normed = zscore_normalize(mom, ["mom_1m", "ma200_dev"])
```

5) J-Quants の生データ取得と保存を個別に実行する
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

---

## ロギングと実行環境

- ログレベルは `LOG_LEVEL` で制御できます（Settings.log_level）。
- `KABUSYS_ENV` により実行環境フラグ（is_dev / is_paper / is_live）が `settings` オブジェクトから参照可能です。
- 自動環境変数読み込みはプロジェクトルート（.git または pyproject.toml）を基準とします。テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。

---

## ディレクトリ構成

（主要ファイルを抜粋）

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
      - quality.py
      - etl.py
      - audit.py
      - pipeline.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

説明:
- data/: データ取得・ETL・品質チェック・スキーマ定義を含む。
- research/: リサーチ / ファクター計算用ユーティリティ。
- config.py: 環境変数管理（.env 自動読み込み等）。
- strategy / execution / monitoring: 戦略・発注・監視のための名前空間（将来拡張用）。

---

## 注意点 / 実運用向けメモ

- J-Quants API レート制限 (120 req/min) に合わせた内部 RateLimiter を用いていますが、実行パターンに応じて追加のレート調整が必要になる場合があります。
- jquants_client のトークンリフレッシュは 401 発生時に自動で行いますが、環境変数のトークンが有効かを事前に確認してください。
- DuckDB に格納する TIMESTAMP の扱いや timezone に注意してください（audit.init_audit_schema は TimeZone を UTC にセットします）。
- news_collector は RSS をパースするため defusedxml を利用しています。外部 RSS の不正データや大容量レスポンスに対する安全策を実装していますが、運用時は信頼できるソースのみを収集対象にすることを推奨します。
- run_daily_etl は各ステップで独立した例外処理を行い、可能な限り途中で止まらない設計です。結果の ETLResult を参照して問題の有無を判断してください。

---

## 最後に

この README はコードベースから読み取れる公開 API と設計方針を基に作成しています。実際の運用ではプロジェクトルートにあるドキュメント（DataPlatform.md / StrategyModel.md 等）が存在する場合、それらも参照してください。機能追加や外部連携（発注インターフェース、Slack 通知等）は適宜 strategy / execution パッケージに実装してください。