# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
DuckDB をデータレイヤに使い、J-Quants API や RSS を取り込んで特徴量生成・品質チェック・監査ログまで整備することを目的としたモジュール群です。

主な設計方針
- DuckDB をコアな永続化層として利用（冪等な INSERT、スキーマ初期化機能あり）
- J-Quants API からの差分取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- ニュース（RSS）収集時に SSRF 対策、サイズ上限、XML 脆弱性対策を実装
- 研究（research）用に外部依存を可能な限り排し、純粋な Python + DuckDB SQL でファクター計算を提供

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得とバリデーション

- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
    - レートリミット（120 req/min）に準拠した RateLimiter
    - リトライ / 指数バックオフ / 401 時のトークン自動リフレッシュ
  - 差分 ETL パイプライン（prices, financials, market calendar）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE / DO NOTHING）

- データ品質チェック
  - 欠損データ検出、スパイク検出、重複チェック、日付不整合チェック
  - QualityIssue データ構造で問題を返却

- ニュース収集
  - RSS フィード取得、前処理（URL 除去・空白正規化）
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等保存
  - SSRF 対策、gzip サイズ検査、XML の defusedxml パース

- ファクター計算 / 研究補助
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - Zスコア正規化ユーティリティ

- スキーマ管理 / 監査ログ
  - DuckDB 向けスキーマ初期化（Raw / Processed / Feature / Execution / Audit）
  - 監査用テーブル群（signal_events / order_requests / executions 等）とインデックス

---

## 必要環境 / 依存ライブラリ

- Python 3.10+
  - （コードは型注釈に `X | None` 等の構文を使用しています）
- pip パッケージ
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install duckdb defusedxml
# 開発ではパッケージルートに pyproject.toml/setup があれば pip install -e . を推奨
```

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを配置）
2. Python 環境を用意（仮想環境推奨）
3. 依存ライブラリをインストール（上記参照）
4. プロジェクトルートに `.env`（必要な環境変数）を作成

自動環境読み込み
- パッケージ import 時に、パッケージ内からプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索して `.env` / `.env.local` を自動で読み込みします。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

### 重要な環境変数（一覧）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABU_API_BASE_URL (任意): kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用トークン
- SLACK_CHANNEL_ID (必須): 通知先チャネル ID
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意): SQLite path（monitoring 用、デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意): 環境 ("development", "paper_trading", "live")（デフォルト: development）
- LOG_LEVEL (任意): ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

例 `.env`（簡易）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=./data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

以下は主要なユースケースの簡単なコード例です。Python スクリプトや REPL で実行できます。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化（親ディレクトリがなければ自動作成）
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants から差分収集）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブ実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
out = run_news_collection(conn, known_codes=known_codes)
print(out)  # {source_name: 新規保存件数}
```

4) 研究系関数（ファクター計算）
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2024, 1, 31)

mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
# ある factor カラムと将来リターン列で IC を計算
# 例: factor_records は calc_momentum の戻り値に類似したリスト
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

5) J-Quants の生データ直接取得
```python
from kabusys.data.jquants_client import fetch_daily_quotes
# settings.jquants_refresh_token を .env 等で設定しておくと id_token を自動管理します
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
print(len(records), "records")
```

---

## よく使う API の説明（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token 等のプロパティで環境変数を取得します。未設定時は ValueError を送出。

- kabusys.data.schema.init_schema(db_path)
  - DuckDB スキーマを作成し、接続を返します（冪等）。

- kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)
  - 日次 ETL を実行して ETLResult を返します。品質チェックも実行可能。

- kabusys.data.news_collector.fetch_rss(url, source)
  - RSS を取得して前処理した記事リストを返します（NewsArticle 型）。

- kabusys.research.calc_momentum / calc_volatility / calc_value
  - 各種ファクターを prices_daily / raw_financials を参照して算出します。

- kabusys.data.stats.zscore_normalize(records, columns)
  - クロスセクションの Z スコア正規化を行います。

---

## ディレクトリ構成

パッケージ内の主要ファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境設定 / .env ロード
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント / 保存ロジック
    - news_collector.py         — RSS 収集 / 前処理 / DB 保存
    - schema.py                 — DuckDB スキーマ定義と init_schema
    - pipeline.py               — ETL パイプライン（差分取得・品質チェック）
    - features.py               — 特徴量ユーティリティ公開
    - stats.py                  — 統計ユーティリティ（zscore 等）
    - calendar_management.py    — マーケットカレンダー管理ユーティリティ
    - audit.py                  — 監査ログスキーマ初期化
    - quality.py                — データ品質チェック
    - etl.py                    — ETLResult 再エクスポート
  - research/
    - __init__.py
    - feature_exploration.py    — 将来リターン / IC / summary 等
    - factor_research.py        — momentum/volatility/value ファクター計算
  - strategy/                    — 戦略層（エントリーポイント等）
  - execution/                   — 発注・実行関連（空の __init__）
  - monitoring/                  — 監視・メトリクス（空の __init__）

---

## 開発 / 貢献

- コードスタイル、テスト、CI を整備していない場合は、まずは軽いユニットテストと linters を追加してください。
- 大きな設計変更や API 変更は README などのドキュメントに注記してください。
- .env やシークレットはリポジトリに含めないでください。

---

## 注意事項 / セキュリティ

- J-Quants トークンや kabu のパスワード等は安全に保管してください（.env を使う場合でもリポジトリに含めないこと）。
- news_collector は SSRF・XML bomb 対策や受信サイズ制限を実装していますが、外部 URL 取得を許可する環境ではさらなる監査を行ってください。
- DuckDB への INSERT は冪等性を意識した実装になっていますが、他のクライアントや直接の DB 操作と組み合わせる場合は注意してください。

---

必要なら README に追記するサンプル（より詳細なセットアップ手順、運用手順、CI/CD やデプロイのガイド、実際の schedule（cron）例、Slack 通知統合例など）を作成できます。どの部分を拡張しますか？