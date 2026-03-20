# KabuSys

日本株向けの自動売買システム用ライブラリ（モジュール群）です。データ取得（J‑Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査テーブル等の基盤機能を提供します。

主な用途は、DuckDB を用いた市場データ基盤の構築と、それを元にした戦略用特徴量の作成・シグナル生成です。発注層（ブローカー接続）は execution 層に想定されていますが、本リポジトリ内の戦略・データ処理は発注 API に直接依存しない設計になっています。

---

## 機能一覧

- データ取得・保存
  - J‑Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - レート制限制御・再試行・トークン自動更新
  - DuckDB への冪等保存（ON CONFLICT / トランザクション）
- ETL / パイプライン
  - 差分更新（最終取得日からの差分・バックフィル対応）
  - 日次 ETL 実行（カレンダー → 株価 → 財務 → 品質チェック）
- スキーマ管理
  - DuckDB の全テーブル（Raw / Processed / Feature / Execution / Audit）を定義・初期化
- 研究・特徴量
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - クロスセクション Z スコア正規化ユーティリティ
  - 研究向けの IC / 将来リターン・統計解析ユーティリティ
- 戦略
  - build_features: 各ファクターを正規化・合成して features テーブルへ保存
  - generate_signals: features + ai_scores を統合して BUY / SELL シグナルを生成し signals テーブルへ保存
- ニュース収集
  - RSS フィードからの記事取得・正規化・重複排除・銘柄抽出・保存
  - SSRF 対策・Gzip 上限・XML 攻撃対策（defusedxml）
- カレンダー管理
  - JPX カレンダーの差分取得・営業日判定ユーティリティ（next/prev/get_trading_days 等）
- 監査（Audit）
  - signal → order_request → execution のトレーサビリティ用テーブル群

---

## 必要条件

- Python 3.10 以上（コードは型ヒントに | を使用）
- 必須ライブラリ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリのみで実装されている部分も多いですが、上記は明示的に使用しています）

実際のプロジェクトでは pyproject.toml / requirements.txt を用意して依存管理してください。

---

## セットアップ手順

1. リポジトリをクローン／配置
   - 例: git clone <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトで配布している場合は pip install -e . または requirements.txt を使ってください）

4. 環境変数の設定
   - .env または OS の環境変数で設定します。自動読み込み機構があり（プロジェクトルートの .env / .env.local を優先的に読み込み）、テスト等で無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（config.Settings で参照される）:
- JQUANTS_REFRESH_TOKEN：J‑Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD：kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN：Slack 通知に使う Bot トークン（必須）
- SLACK_CHANNEL_ID：Slack のチャンネル ID（必須）

任意（デフォルトあり）:
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

例 .env（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 初期化（DuckDB スキーマ作成）

DuckDB のスキーマを初期化して接続を取得するには `kabusys.data.schema.init_schema` を使います。

簡単な例:
```python
from kabusys.data.schema import init_schema

# デフォルト: data/kabusys.duckdb を使用
conn = init_schema("data/kabusys.duckdb")
```

":memory:" を渡すことでインメモリ DB にもできます:
```python
conn = init_schema(":memory:")
```

---

## 使い方（代表的なワークフロー）

1) 日次 ETL を実行してデータを取得・保存する
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量（features）を構築する
```python
from kabusys.strategy import build_features
from datetime import date

count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

3) シグナルを生成する
```python
from kabusys.strategy import generate_signals

n_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {n_signals}")
```

4) ニュース収集ジョブを実行する
```python
from kabusys.data.news_collector import run_news_collection

# known_codes: 銘柄抽出に使う有効コードセット（例: {'7203','6758',...}）
res = run_news_collection(conn, known_codes=set(), timeout=30)
print(res)
```

5) カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"market_calendar saved: {saved}")
```

---

## 開発時の注意点

- 環境自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を読み込みます。テストや CI で自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB への挿入は多くの箇所でトランザクションを使用し、冪等性（ON CONFLICT）を保っています。初期化・ETL・保存処理は冪等を前提に設計されています。
- ネットワークや API リトライ処理、レート制限は jquants_client に実装されています。テスト時は id_token 等を注入して外部 API 呼び出しをモックしてください（_request / _urlopen の差し替えが想定されています）。
- news_collector では SSRF 対策・XML 安全対策（defusedxml）を行っています。外部ネットワークアクセスのテストはモック推奨です。

---

## 主要モジュール・エントリ（抜粋）

- kabusys.config
  - settings: 環境変数アクセスラッパー
- kabusys.data
  - schema.init_schema / get_connection
  - jquants_client: fetch/save系 API
  - pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - news_collector.run_news_collection / fetch_rss / save_raw_news
  - calendar_management: is_trading_day / next_trading_day / calendar_update_job
  - stats.zscore_normalize
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- kabusys.strategy
  - build_features (features テーブル生成)
  - generate_signals (signals テーブル生成)
- kabusys.execution (placeholder / execution 層向けインターフェース)

---

## ディレクトリ構成

リポジトリ内の主要ファイルと階層（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/  （監視・モニタリング関連は monitoring パッケージ想定）
- pyproject.toml / setup.cfg / requirements.txt（プロジェクト配布用に存在する想定）
- .env.example（環境変数例、存在すれば参照）

（上記は抜粋です。詳細は各モジュールの docstring を参照してください。）

---

## よくある操作例 / サンプルワンライナー

- スキーマ初期化（コマンドラインから Python 実行）
  - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

- 日次 ETL 実行（スクリプト化推奨）
  - python -c "from kabusys.data.schema import init_schema; from kabusys.data.pipeline import run_daily_etl; conn=init_schema('data/kabusys.duckdb'); print(run_daily_etl(conn).to_dict())"

---

## 最後に / 今後の拡張点

- execution 層のブローカー接続（kabuステーションや他ブローカー）と実運用向けの安全機構（資金管理・レート制限・遅延処理）
- AI スコア生成パイプライン（ai_scores の算出）
- モニタリング・アラート（Slack 通知・監視 DB への集計）
- テストスイート・CI 設定（単体テスト・インテグレーションテスト）

ご不明点や README に追加したい項目があれば教えてください。README をプロジェクトの実際の配布形態（pyproject / requirements）や CI に合わせて調整できます。