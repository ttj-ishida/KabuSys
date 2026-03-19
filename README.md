# KabuSys

日本株自動売買プラットフォームの一部機能を提供する Python パッケージ（ライブラリ）です。  
主にデータ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査用スキーマなどを含み、戦略層・実行層と連携できる基盤を提供します。

---

## 主要機能

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務諸表、JPX マーケットカレンダーの取得（ページネーション対応）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- データ永続化（DuckDB）
  - Raw / Processed / Feature / Execution 層を想定したスキーマ定義と初期化
  - ON CONFLICT による冪等保存
- ETL パイプライン
  - 差分更新（バックフィル対応）、品質チェックフック
  - 日次 ETL 統合処理
- 研究・ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - 前方リターン計算、IC（Spearman）計算、統計サマリー
- 特徴量エンジニアリング
  - ファクターの正規化（Z スコア）・ユニバースフィルタ・features テーブルへの UPSERT
- シグナル生成
  - features と ai_scores を統合して final_score を計算、BUY / SELL シグナルを生成し signals テーブルへ日付単位で置換保存
  - Bear レジーム抑制、ストップロス等のエグジット判定
- ニュース収集
  - RSS 取得（SSRF対策、XML 脆弱性防止、gzip サイズ制限）
  - raw_news 保存、記事ID生成（URL 正規化→SHA256）、銘柄抽出と紐付け
- 監査ログ（Audit）
  - signal → order_request → broker_order → execution までトレース可能な監査テーブル群

---

## 要求環境

- Python >= 3.10（PEP 604 の型記法などを使用）
- 必須ライブラリ（一例）
  - duckdb
  - defusedxml
- その他: 標準ライブラリを中心に実装されていますが、実行環境に応じて追加パッケージが必要になる場合があります。

インストール例:
```bash
python -m pip install duckdb defusedxml
# またはプロジェクトの setup / poetry を用いる場合はそちらに従ってください
```

---

## 環境変数（設定）

Settings クラスは環境変数から設定を読み込みます。自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL (省略可) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (省略可) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (省略可) — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV (省略可) — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (省略可) — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

例（プロジェクトルートの `.env`）:
```env
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン／配置
2. Python と依存パッケージをインストール
   - 例: python -m pip install -r requirements.txt（requirements.txt があれば）
   - または最低限: python -m pip install duckdb defusedxml
3. 環境変数をセット（.env をプロジェクトルートに配置）
4. DuckDB スキーマを初期化

DuckDB スキーマ初期化（Python REPL / スクリプト例）:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb を作成してスキーマを作る
conn.close()
```

---

## 基本的な使い方（例）

### 日次 ETL 実行
日次 ETL を実行して市場カレンダー・株価・財務データを取得・保存し、品質チェックを行います。

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
conn.close()
```

### 特徴量構築（features テーブル）
research モジュールで計算した raw ファクターを正規化して features に保存します。

```python
from kabusys.config import settings
from kabusys.data.schema import get_connection, init_schema
from kabusys.strategy import build_features
from datetime import date

conn = init_schema(settings.duckdb_path)
n = build_features(conn, target_date=date.today())
print(f"{n} 銘柄の features を更新しました")
conn.close()
```

### シグナル生成
features / ai_scores / positions を参照して BUY/SELL シグナルを生成し signals テーブルへ保存します。

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals
from datetime import date

conn = init_schema(settings.duckdb_path)
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"{count} シグナルを生成しました")
conn.close()
```

### ニュース収集ジョブ
RSS からニュース記事を収集して raw_news に保存、既知銘柄との紐付けを行います。

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema(settings.duckdb_path)
# sources を渡してカスタム RSS を使うことも可能
results = run_news_collection(conn, known_codes={"7203", "6758"})
print(results)  # {source_name: saved_count, ...}
conn.close()
```

---

## 注意点・設計メモ

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。テストなどで無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレートリミット（120 req/min）に従うため、fetch 部分は内部でスロットリングしています。
- DuckDB のスキーマ初期化は idempotent（既存テーブルは再作成しません）。初回は init_schema() を使ってください。
- NewsCollector は SSRF 対策、XML 脆弱性対策（defusedxml）、レスポンスサイズ制限 等の安全策を組み込んでいます。
- 生成されるシグナルは signals テーブルに保存され、発注（execution）層は別モジュール / 外部プロセスで実装される想定です。
- ログレベルや環境（paper_trading / live）に応じた挙動切替が Settings で可能です。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数および Settings 管理（自動 .env ロード）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ）
    - schema.py
      - DuckDB スキーマ定義・初期化・接続ユーティリティ
    - pipeline.py
      - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - features.py
      - data.stats の再エクスポート
    - news_collector.py
      - RSS 収集・記事保存・銘柄抽出・紐付け
    - calendar_management.py
      - market_calendar の管理・営業日判定・更新ジョブ
    - audit.py
      - 発注〜約定の監査ログスキーマ（signal_events, order_requests, executions 等）
    - pipeline.py
      - ETL 実行ロジック（重複）
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_volatility / calc_value
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py
      - build_features（Z スコア正規化、ユニバースフィルタ、features への保存）
    - signal_generator.py
      - generate_signals（final_score 計算、BUY/SELL 生成）
  - execution/
    - __init__.py
      - （実行層用の骨組み）
  - monitoring/
    - （監視・メトリクス収集用のモジュール想定）

各モジュールには詳細な docstring と設計ポリシーが記載されているため、実装の拡張や運用ルールの理解に役立ちます。

---

もし README に追加したいセクション（例: CI / テストの実行方法、具体的な実運用のワークフロー、Docker 化手順など）があれば教えてください。必要に応じてサンプルスクリプトやコマンド例を追記します。