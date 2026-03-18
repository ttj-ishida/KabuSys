# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB をデータレイクに用い、J-Quants API からのデータ取得、ETL、品質チェック、特徴量計算、ニュース収集、監査ログなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の層を想定したモジュール群を含みます。

- データ収集 (J-Quants API クライアント、RSS ニュース収集)
- データ格納 (DuckDB スキーマ、監査ログスキーマ)
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化）
- 発注／実行／監視のための骨組み（Execution / Strategy / Monitoring：実装は拡張前提）

設計方針のポイント：
- DuckDB を中心に「Raw / Processed / Feature / Execution」の多層スキーマを用意
- J-Quants のレート制限厳守、再試行、トークン自動リフレッシュに対応
- ニュース収集では SSRF 対策・XML 脆弱性対策・トラッキングパラメータ除去などを実装
- ETL は差分更新・バックフィル・品質チェックを行い、冪等に保存

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API から株価日足 / 財務データ / 市場カレンダーを取得
  - ページネーション対応、レート制限 (120 req/min)、リトライ、トークン自動リフレッシュ
  - DuckDB へ冪等的に保存する save_* 関数

- data.news_collector
  - RSS フィード取得 → テキスト前処理 → raw_news への冪等保存
  - SSRF・XML攻撃・レスポンスサイズ制限・トラッキングパラメータ除去等の安全対策
  - 記事と銘柄コードの紐付け機能

- data.schema / data.audit
  - DuckDB のスキーマ定義（raw / processed / feature / execution / audit）
  - init_schema / init_audit_db による初期化

- data.pipeline
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得・backfill のサポート
  - ETLResult による処理結果の集約

- data.quality
  - 欠損・スパイク・重複・日付不整合チェック（QualityIssue を返す）

- research
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（data.stats）

---

## 動作環境と依存

- Python 3.10 以上（型ヒントに PEP 604 の `|` を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 推奨: ロギング設定、.env による機密情報管理

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# もしパッケージ化されていれば:
# pip install -e .
```

---

## 環境変数 / 設定

KabuSys は環境変数から設定を読み込みます。プロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）にある `.env` / `.env.local` を自動的に読み込みます（OS 環境変数が優先、.env.local は .env を上書き）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API パスワード
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       : Slack 通知先チャンネル ID

任意 / デフォルト:
- KABU_API_BASE_URL      : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV            : 開発モード（development / paper_trading / live。デフォルト development）
- LOG_LEVEL              : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定は `from kabusys.config import settings` でアクセスできます（例: settings.jquants_refresh_token）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（duckdb, defusedxml 等）
4. プロジェクトルートに `.env` を作成して上記必須変数を設定
5. DuckDB スキーマを初期化

DuckDB スキーマ初期化例:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

監査ログ専用 DB 初期化例:
```python
from kabusys.data import audit
conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（代表的なワークフロー）

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data import schema, pipeline
conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- 株価データを差分取得のみ行う（run_prices_etl）:
```python
from kabusys.data import pipeline, schema
from datetime import date
conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
```

- RSS ニュース収集（raw_news 保存と銘柄紐付け）
```python
from kabusys.data import news_collector, schema
conn = schema.get_connection("data/kabusys.duckdb")
# known_codes は銘柄コード (例: {"7203","6758", ...}) を渡すと抽出を行う
res = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
print(res)  # {source_name: saved_count}
```

- 研究用: モメンタム・ボラティリティ等の特徴量計算
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
fwd = calc_forward_returns(conn, target)
```

- Z スコア正規化（クロスセクション）
```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m", "mom_3m"])
```

---

## セキュリティ／運用上の注意

- J-Quants の rate limit（120 req/min）を守るために内部でスロットリングとリトライが実装されています。大量取得は制限に注意してください。
- ニュース収集は外部 URL を開くため、SSRF 対策や XML パースの安全ライブラリ（defusedxml）を利用していますが、運用時はアクセス先リスト等の運用ルールを設けてください。
- 本番口座（live）での発注機能を実装する場合は、安全なブローカー連携・二重発注防止・監査ログの完全性を必ず確認してください。
- 環境変数やトークンは安全に管理してください（.env は gitignore へ追加推奨）。

---

## ディレクトリ構成（主要ファイル）

（このライブラリの src/kabusys 配下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数読み込み・設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント + 保存ロジック
    - news_collector.py      # RSS ニュース収集・前処理・保存
    - schema.py              # DuckDB スキーマ定義・init_schema
    - stats.py               # 統計ユーティリティ（zscore_normalize）
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py # 市場カレンダー管理ユーティリティ
    - audit.py               # 監査ログスキーマ（signal/order/execution）
    - etl.py                 # ETL 公開インターフェース
    - quality.py             # データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py # 将来リターン / IC / summary 等
    - factor_research.py     # momentum/value/volatility 計算
  - strategy/                 # 戦略関連（拡張用）
  - execution/                # 発注実装（拡張用）
  - monitoring/               # 監視関連（拡張用）

---

## 開発ノート / 拡張ポイント

- Strategy / Execution / Monitoring は骨組みとして用意されています。実際の発注ロジックやブローカー連携はプロジェクト固有の要件に合わせて実装してください。
- DuckDB スキーマは冪等（IF NOT EXISTS / ON CONFLICT）で作られているため、本番運用でも安全にスキーマ初期化できます。ただし、外部キー制約や ON DELETE の扱いに制限（DuckDB バージョン依存）がある点に注意してください。
- quality モジュールは Fail-Fast ではなく問題を収集して返す設計です。ETL の停止基準は呼び出し側で判断してください。

---

必要であれば、README に含めるサンプル .env.example や CI / デプロイ手順、より詳細な関数リファレンスの追加も作成します。どの範囲を詳しく書くか指定してください。