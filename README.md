# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
DuckDB をデータ層に用い、J-Quants API からマーケットデータや財務データを取得して ETL → 特徴量生成 → シグナル生成 → 発注（execution 層）へつなぐ設計になっています。研究用の factor 計算や特徴量探索機能も含まれます。

## 主要な特徴
- データ収集（J-Quants API）と差分 ETL（差分取得・バックフィル対応）
- DuckDB ベースのスキーマ定義と冪等な保存（ON CONFLICT / トランザクション対応）
- ファクター（Momentum / Volatility / Value 等）計算モジュール
- クロスセクション Z スコア正規化ユーティリティ
- 戦略特徴量作成（feature engineering）とシグナル生成（BUY/SELL）ロジック
- ニュース（RSS）収集と記事→銘柄紐付け機能（SSRF 対策・サイズ制限・XML 安全パース）
- 市場カレンダー管理（JPX）と営業日判定ユーティリティ
- 発注・約定・ポジション・監査ログ向けのスキーマ（execution / audit）

## 動作要件
- Python 3.10 以上（ソースで | (union) 型注釈等を使用）
- 必要な外部ライブラリ（主に）
  - duckdb
  - defusedxml
（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）

例（最低限のインストール）:
```bash
python -m pip install "duckdb" "defusedxml"
# パッケージを開発モードでインストールする場合（リポジトリルートで）
python -m pip install -e .
```

## セットアップ手順

1. リポジトリを取得する（例）:
   ```bash
   git clone <this-repo>
   cd <this-repo>
   ```

2. Python 環境の準備（仮想環境推奨）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install duckdb defusedxml
   pip install -e .
   ```

3. 環境変数の設定  
   自動で .env（プロジェクトルート）や .env.local を読み込みます（無ければ手動で設定）。必要な主な環境変数:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
   - LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化する場合に `1` を設定

   .env の例（環境に合わせて作成）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

## 初期化（DB スキーマ作成）
DuckDB のスキーマを初期化するには `kabusys.data.schema.init_schema` を使用します。

例:
```python
from datetime import date
from kabusys.data.schema import init_schema, get_connection

# ファイル DB を作成してスキーマを初期化
conn = init_schema("data/kabusys.duckdb")

# メモリ DB を使う場合
# conn = init_schema(":memory:")
```

init_schema は必要なテーブル・インデックスをすべて作成して DuckDB 接続を返します。既に存在する場合はスキップされるため冪等です。

## 基本的な使い方（サンプル）
以下は日次処理の一例です。J-Quants からデータを取得して保存 → 特徴量を作成 → シグナル生成までの流れを示します。

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.strategy import build_features, generate_signals

# DB 初期化（既存ファイルを使用している場合は init_schema を書かず get_connection を使っても可）
conn = init_schema("data/kabusys.duckdb")

# ETL 実行（今日分を対象）
etl_result = run_daily_etl(conn, target_date=date.today())
print(etl_result.to_dict())

# 特徴量作成
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")

# シグナル生成（閾値や重みをカスタム渡し可能）
signals_count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {signals_count}")
```

- run_daily_etl は市場カレンダー・株価・財務データの差分取得と品質チェックを行い、ETLResult を返します。
- build_features は research モジュールのファクターを取り込み Z スコア正規化・ユニバースフィルタを適用し features テーブルへ保存します（冪等）。
- generate_signals は features / ai_scores / positions を参照して BUY/SELL シグナルを signals テーブルに書き込みます（冪等）。

### ニュース収集ジョブの実行例
RSS 取得 → raw_news 保存 → 銘柄紐付けの流れ:

```python
from kabusys.data.news_collector import run_news_collection

# conn は init_schema で得た DuckDB 接続
# known_codes: 銘柄抽出に使う有効な銘柄コードの集合（例: prices_daily から取得）
results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
print(results)  # {source_name: saved_count, ...}
```

### カレンダー更新ジョブ
夜間バッチ等で JPX カレンダーを更新する:

```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn, lookahead_days=90)
print(f"calendar saved: {saved}")
```

## 主要 API（モジュールと関数）
- kabusys.config.settings: 環境変数をラップした設定オブジェクト
- kabusys.data.schema.init_schema(db_path) / get_connection(db_path)
- kabusys.data.pipeline.run_daily_etl(...) / run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / save_* 系
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
- kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- kabusys.research.*: calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary 等
- kabusys.strategy.build_features / generate_signals

## ディレクトリ構成（主要ファイル）
（リポジトリの src/kabusys 以下の主なファイル/パッケージ）

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
    - (その他 ETL/quality/monitoring 関連モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
    - (研究用ユーティリティ)
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/ (エクスポートされているがコードベースによる実装の有無に差異がある可能性があります)

（上記は本 README を作成した時点での主要ファイル群です。実際のリポジトリでは追加ファイルやサブモジュールが存在することがあります。）

## 開発・運用上の注意
- 環境変数は .env/.env.local をプロジェクトルートに置くことで自動読み込みされます。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレート制限（120 req/min）に配慮した実装になっていますが、運用時は API 利用規約を遵守してください。
- DuckDB の DDL は冪等実行するよう書かれているため、init_schema は何度呼んでも安全です。ただし schema の変更やマイグレーションは注意して行ってください。
- ニュース収集は SSRF 対策や受信サイズ制限、XML の堅牢パーサ（defusedxml）を用いていますが、運用環境でのネットワーク・セキュリティ方針に合わせて更なる制限を検討してください。
- KABUSYS_ENV により本番（live）・ペーパー取引（paper_trading）・開発（development）で挙動を切り替えられます。実運用では設定ミスに注意してください。

## 参考・拡張ポイント
- strategy や execution 層は明確に分離されています。発注ロジックを組み合わせてブローカーとの接続を実装すると運用環境で自動発注が可能です（paper_trading モードで十分にテスト推奨）。
- research パッケージは外部依存を最小限にした設計です。追加の統計・可視化には pandas/plotly 等をラップして研究ノートを作成すると便利です。

---

README の内容やサンプルはコードベースに合わせた簡易的な案内です。実際の運用にあたっては secrets の管理、ログ設定、ジョブスケジューラ（cron / Airflow 等）との連携、バックアップや監査要件に応じた運用設計を行ってください。必要であればセットアップ手順の詳細（systemd ユニット / Docker コンテナ化 / CI 設定など）も作成します。必要があれば教えてください。