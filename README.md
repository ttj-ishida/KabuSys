# KabuSys

日本株向け自動売買基盤のライブラリ群（データ収集・ETL・特徴量計算・監査ログ・研究用ユーティリティ等）

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するためのコンポーネント群です。主な目的は以下です。

- J-Quants API からのマーケットデータ・財務データ・市場カレンダーの取得と DuckDB への保存（冪等化）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）と記事 → 銘柄紐付け
- 研究（リサーチ）用のファクター計算・将来リターン・IC 計算・統計サマリ
- 監査（signal → order → execution のトレーサビリティ）用スキーマと初期化
- 各種ユーティリティ（マーケットカレンダー管理、統計正規化 など）

設計方針として、DuckDB を中心にデータレイヤを分離し、API 呼び出しはレート制御・リトライ・トークンリフレッシュを含む堅牢な実装になっています。研究モジュールは本番発注 API にアクセスしないよう設計されています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークンリフレッシュ）
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: 日次 ETL（差分取得・バックフィル・品質チェック）
  - news_collector: RSS 収集、テキスト前処理、記事保存、銘柄抽出・紐付け
  - calendar_management: 市場カレンダーの管理・営業日判定
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ（signal, order_requests, executions）スキーマと初期化
  - stats / features: 汎用統計・正規化ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、統計サマリー
- config: 環境変数 / .env 読み込みのユーティリティ（自動ロードを無効化可能）
- execution / strategy / monitoring: 各レイヤのプレースホルダ／拡張ポイント

---

## 必要要件（依存）

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml

インストール環境に合わせて pip / poetry 等でインストールしてください。

例（pip）:
```
pip install duckdb defusedxml
```

プロジェクトを editable インストールする場合:
```
pip install -e .
```
（pyproject.toml がある想定です）

---

## セットアップ手順

1. リポジトリをチェックアウト
2. 仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. 環境変数を準備（.env ファイルをプロジェクトルートに置くと自動読み込みされます）
   - 自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

推奨する .env の項目（例）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack 通知
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO
```

環境変数は .env / .env.local の順でプロジェクトルートから自動読み込みされます（config モジュール）。テスト等で自動ロードを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## 使い方（代表的な利用例）

基本的に DuckDB 接続を初期化して ETL や解析関数を呼び出します。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイルを指定（":memory:" でインメモリ DB）
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants から差分取得・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を渡せば任意の日を対象に実行
print(result.to_dict())
```

3) J-Quants から直接データ取得（テストや個別取得）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

# トークンは config.settings.jquants_refresh_token を参照（必要に応じて引数で注入可）
quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

4) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection

# known_codes: 銘柄抽出に利用する有効銘柄コードの集合
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存数}
```

5) 研究（ファクター計算・IC 計算）
```python
from kabusys.research import (
    calc_momentum, calc_volatility, calc_value,
    calc_forward_returns, calc_ic, factor_summary, zscore_normalize
)
from datetime import date

d = date(2024, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

# 将来リターン算出（翌日・翌週・翌月）
fwd = calc_forward_returns(conn, d, horizons=[1,5,21])

# 例: mom_1m と fwd_1d の IC
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")

# ファクター統計サマリー
summary = factor_summary(mom, ["mom_1m", "ma200_dev"])

# Zスコア正規化（クロスセクション）
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

6) 監査ログ（audit）スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema

conn = init_schema("data/kabusys.duckdb")
# 既存接続に監査用テーブルを追加
init_audit_schema(conn, transactional=True)
```

---

## よく使う設定 / 注意点

- 環境（KABUSYS_ENV）は development / paper_trading / live のいずれかを指定してください。live 実行時は発注系の慎重な取り扱いが必要です。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行われます。テストで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API はレート制限（120 req/min）や 401 リフレッシュが組み込まれています。大量データ取得時は pipeline の差分ロジックを利用してください。
- news_collector は外部 RSS を扱うため SSRF・XML Bomb・大容量レスポンス等の保護を実装していますが、運用時はソースの信頼性に留意してください。

---

## ディレクトリ構成

以下は主要なファイル／モジュールの一覧（抜粋）です:

- src/
  - kabusys/
    - __init__.py
    - config.py                     # 環境変数 / .env ロード・設定
    - data/
      - __init__.py
      - jquants_client.py           # J-Quants API クライアント（取得・保存）
      - news_collector.py           # RSS 収集・保存・銘柄抽出
      - schema.py                   # DuckDB スキーマ定義・初期化
      - pipeline.py                 # ETL パイプライン（run_daily_etl など）
      - quality.py                  # データ品質チェック
      - calendar_management.py      # マーケットカレンダー管理
      - audit.py                    # 監査用スキーマ（signal/order/execution）
      - stats.py                    # 統計ユーティリティ（zscore_normalize）
      - features.py                 # features 用公開インターフェース
      - etl.py                      # ETLResult の再エクスポート
    - research/
      - __init__.py
      - factor_research.py          # Momentum/Value/Volatility 等
      - feature_exploration.py      # 将来リターン・IC・summary 等
    - strategy/                      # 戦略レイヤ（雛形）
      - __init__.py
    - execution/                     # 発注 / ブローカー連携（雛形）
      - __init__.py
    - monitoring/                    # 監視用モジュール（雛形）
      - __init__.py

各モジュールには docstring と詳細な実装上の設計注釈が含まれており、API の使用方法は docstring を参照することで理解できます。

---

## 開発・拡張のポイント

- DuckDB のスキーマは schema.py に集約されています。テーブル追加やカラム変更時はこのファイルを修正してください。
- ETL の差分ロジックは pipeline.py にあり、backfill の日数や品質チェック閾値は引数で調整可能です。
- research モジュールは外部ライブラリ非依存で実装されているため、そのままテスト実行できます。大規模データ処理の最適化は SQL 側（DuckDB）で行うのが推奨です。
- 発注周り（kabuAPI 等）を実装する場合は execution パッケージに実装し、audit テーブルへの書き込みを忘れずに行ってください（トレーサビリティ要件）。

---

必要であれば README の追加セクション（例: API リファレンス抜粋、より詳細な環境変数説明、運用チェックリスト、CI 手順）を作成します。どの情報を優先して追加しますか？