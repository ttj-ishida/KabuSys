# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）。  
データ取得・ETL、ファクター計算、特徴量エンジニアリング、シグナル生成、ニュース収集、監査ログ・スキーマ管理などを含むモジュール群を提供します。

現在のバージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API から市場データ・財務データ・カレンダーを安全に取得（レート制限・リトライ・トークンリフレッシュ対応）
- DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）の管理（冪等保存、DDL 初期化）
- 研究（research）で作成した生ファクターを正規化・合成して戦略用特徴量を作成
- 正規化済み特徴量と AI スコアを統合して売買シグナルを生成
- RSS 等からニュース記事を収集して DB に保存し、銘柄抽出まで行う
- ETL パイプライン・品質チェック・マーケットカレンダー管理・監査ログ機能を提供

設計上のポイント：
- ルックアヘッドバイアスの防止（target_date 時点のデータのみ使用）
- 冪等性（ON CONFLICT / トランザクションで置換）を重視
- 外部依存を最小化（標準ライブラリ中心、DuckDB / defusedxml 等の必要最小限のライブラリ）

---

## 主な機能一覧

- 環境設定の自動ロード（.env / .env.local / 環境変数）
- J-Quants API クライアント（fetch / save / retry / rate limiting / token refresh）
- DuckDB スキーマ初期化（init_schema）
- ETL パイプライン（run_daily_etl、差分取得・バックフィル・品質チェック）
- ファクター計算（momentum / volatility / value 等）
- 特徴量作成（build_features） — Z スコア正規化、ユニバースフィルタ適用
- シグナル生成（generate_signals） — コンポーネントスコア合成、BUY/SELL 判定、Bear レジーム抑制
- ニュース収集（RSS fetch / preprocess / 保存 / 銘柄抽出）
- マーケットカレンダー管理（営業日判定 / next/prev_trading_day / calendar update job）
- 監査ログ・発注／約定トレーサビリティ用テーブル群
- 汎用統計ユーティリティ（zscore_normalize 等）

---

## セットアップ手順

前提
- Python 3.10 以上（コード内で型の `|` を使用しているため）
- pip が使えること

1. リポジトリをクローン / 展開

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール  
   必須依存（最低限）:
   - duckdb
   - defusedxml

   例:
   ```bash
   pip install duckdb defusedxml
   ```

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用）

4. パッケージのインストール（開発モード）
   ```bash
   pip install -e .
   ```

5. 環境変数設定  
   プロジェクトルートの .env または .env.local に設定できます。主な環境変数:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - KABU_API_BASE_URL: kabuステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 開発環境（development / paper_trading / live）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するとパッケージ読み込み時の .env 自動ロードを無効化

   簡単な .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 初期化（DB スキーマ作成）

Python REPL またはスクリプトで DuckDB のスキーマを初期化します。

例:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

- db_path に ":memory:" を渡すとインメモリ DB を使用します。
- init_schema はテーブル・インデックスを冪等に作成します。

---

## 使い方（主要な操作例）

以下は代表的な利用フローのサンプルです。プロダクションではログ設定・例外処理・スケジューラを組み合わせます。

1) 日次 ETL（市場カレンダー / 株価 / 財務 の差分取得・保存）
```python
from datetime import date
from kabusys.data import schema, pipeline

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB 接続（初回は init_schema を事前実行）
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量作成（build_features）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

3) シグナル生成（generate_signals）
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date.today(), threshold=0.60)
print(f"signals created: {n}")
```

4) ニュース収集ジョブ（RSS 取得 → DB 保存 → 銘柄紐付け）
```python
import duckdb
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = duckdb.connect("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

5) J-Quants 生データ取得（直接呼び出す場合）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使って自動取得
records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
```

---

## よくあるトラブルシューティング

- 環境変数不足による例外:
  - settings のプロパティ（例: settings.jquants_refresh_token）は未設定時に ValueError を投げます。必須変数を .env に設定してください。
- DuckDB 関連:
  - init_schema を事前に呼ばずにテーブル参照するとテーブル未作成で失敗する処理があります。初回は必ず init_schema を実行してください。
- ネットワーク / API:
  - J-Quants の呼び出しはリトライやレートリミット対策を備えていますが、認証トークンの期限切れやネットワーク障害時はログを確認してください。
- RSS / ニュース収集:
  - RSS のパースに失敗した場合は警告ログが出ます。defusedxml を使用して安全にパースしています。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要モジュール構成（src/kabusys）:

- __init__.py
  - パッケージ初期化。公開モジュール一覧。

- config.py
  - 環境変数の自動読み込み（.env / .env.local）と Settings クラス。
  - 必須変数チェック（JQUANTS_REFRESH_TOKEN など）と環境切替（KABUSYS_ENV）。

- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（fetch/save、リトライ、rate limit、token refresh）
  - schema.py
    - DuckDB のスキーマ定義と init_schema、get_connection
  - pipeline.py
    - ETL パイプライン（run_daily_etl、個別 ETL ジョブ）
  - stats.py
    - 統計ユーティリティ（zscore_normalize）
  - features.py
    - データ層の特徴量ユーティリティ（再エクスポート）
  - news_collector.py
    - RSS 収集・前処理・DB 保存・銘柄抽出
  - calendar_management.py
    - マーケットカレンダー管理、営業日判定、カレンダー更新ジョブ
  - audit.py
    - 発注/約定の監査ログ用 DDL（signal_events, order_requests, executions など）

- research/
  - __init__.py
  - factor_research.py
    - momentum / volatility / value のファクター計算（prices_daily, raw_financials を参照）
  - feature_exploration.py
    - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー

- strategy/
  - __init__.py
  - feature_engineering.py
    - 生ファクターを正規化・合成し features テーブルへ保存
  - signal_generator.py
    - features と ai_scores を統合して BUY/SELL シグナルを生成

- execution/
  - （発注実行層のプレースホルダ。発注ロジック・ブローカー連携を実装）

---

## 開発者向け補足

- 型注釈とロギングを多用しており、ユニットテスト・モックが行いやすい設計です（例: news_collector._urlopen の差し替え）。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テストなどで自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の SQL は SQL インジェクションに配慮してパラメータバインディングを多用していますが、DDL のような静的 SQL では埋め込み文字列があります（信頼済みの DDL のみ）。

---

もし README に追記したい点（CLI コマンド例、運用スケジュール、監視/アラート設定、より詳細な .env.example など）があれば教えてください。必要に応じてテンプレートや手順を追加で作成します。