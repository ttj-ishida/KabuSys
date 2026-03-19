# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。ETL（J-Quants からの市場データ取得） → 特徴量作成 → シグナル生成 → 実行・監視、というワークフローを DuckDB を中心に実現するモジュール群を提供します。

このリポジトリはライブラリとして以下の目的に分割されています。
- データ取得・保存（J-Quants API クライアント、RSSニュース収集、DuckDB スキーマ定義）
- ETL パイプライン（差分取得、品質チェック）
- 研究（ファクター計算・解析ユーティリティ）
- 戦略（特徴量整備、シグナル生成）
- 実行・監視（実行レイヤのスキーマ・監査ログ）

---

## 主な機能一覧

- J-Quants API クライアント
  - rate limit に配慮したリクエスト
  - リトライ、トークン自動リフレッシュ
  - 日足・財務・マーケットカレンダー取得
  - DuckDB へ冪等的に保存する save_* 関数群

- DuckDB スキーマ管理
  - raw / processed / feature / execution 層のテーブル定義
  - init_schema() による初期化（冪等）

- ETL パイプライン
  - 差分更新（最終取得日からの差分）
  - market calendar の先読み・バックフィル
  - run_daily_etl による一括 ETL（品質チェック含む）

- 研究用ファクター計算
  - Momentum / Volatility / Value の計算（prices_daily, raw_financials 参照）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー

- 特徴量整備 & シグナル生成
  - features の Z スコア正規化・ユニバースフィルタ適用
  - ai_scores と統合して final_score を計算し BUY/SELL シグナル生成
  - シグナルは signals テーブルへ日付単位で置換（冪等）

- ニュース収集（RSS）
  - URL 正規化、トラッキングパラメータ除去、SSRF 対策、gzip/サイズ制限
  - raw_news / news_symbols への冪等保存

- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査用スキーマ

---

## セットアップ手順（開発環境向け）

1. Python（推奨 3.9+）を用意してください。

2. 必要パッケージをインストールします。主要依存は duckdb, defusedxml 等です。プロジェクトに pyproject.toml / requirements があればそちらを利用してください。最低限の例:

   ```bash
   python -m pip install "duckdb" "defusedxml"
   ```

3. このパッケージを開発インストール（任意）:

   ```bash
   python -m pip install -e .
   ```

4. 環境変数を設定します。ルートに `.env` / `.env.local` を置くと自動で読み込まれます（パッケージ読み込み時に自動ロード）。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（主要）環境変数例:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（既定: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development"|"paper_trading"|"live")（既定: development）
- LOG_LEVEL: ログレベル ("DEBUG"|"INFO"|...)

`.env` の例（ルートに `.env.example` を置くことを想定）:

```
JQUANTS_REFRESH_TOKEN=xxxxxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単なワークフロー例）

以下は Python スクリプト内での基本的な操作順です。

1. DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# 設定からデフォルトの DB パスを取得
db_path = settings.duckdb_path
conn = init_schema(db_path)  # テーブルを作成して DuckDB 接続を返す
```

2. 日次 ETL を実行（J-Quants からデータ取得して保存）

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3. 特徴量をビルド（features テーブルに保存）

```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date.today())
print(f"features: {n} rows")
```

4. シグナル生成（signals テーブルに保存）

```python
from kabusys.strategy import generate_signals

count = generate_signals(conn, target_date=date.today())
print(f"signals written: {count}")
```

5. ニュース収集ジョブ例

```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄コードセット（抽出に利用）
known_codes = {"7203", "6758", "6501"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

注:
- すべての主要APIは DuckDB コネクション（duckdb.DuckDBPyConnection）を引数にとるため、テスト時は ":memory:" での in-memory DB を使えます。
- generate_signals や build_features は target_date 時点のデータのみを参照する設計になっておりルックアヘッドを防止します。

---

## 主要 API / エントリポイント（要約）

- kabusys.config.settings: 環境変数経由の設定取得
- kabusys.data.schema.init_schema(db_path): DuckDB スキーマ初期化
- kabusys.data.pipeline.run_daily_etl(conn, target_date, ...): 日次 ETL
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes: データ取得・保存
- kabusys.data.news_collector.run_news_collection: RSS 収集・DB保存
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- kabusys.strategy.build_features(conn, target_date): features 作成
- kabusys.strategy.generate_signals(conn, target_date, threshold, weights): signals 作成

---

## ディレクトリ構成

（ルートがプロジェクトルートとして想定）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント（取得・保存）
    - news_collector.py       # RSS ニュース収集・保存
    - schema.py               # DuckDB スキーマ定義と init_schema
    - pipeline.py             # ETL パイプライン（run_daily_etl 等）
    - features.py             # zscore_normalize の再エクスポート
    - calendar_management.py  # market_calendar 関連ユーティリティ
    - audit.py                # 監査ログスキーマ
    - stats.py                # 統計ユーティリティ（zscore_normalize 等）
  - research/
    - __init__.py
    - factor_research.py      # momentum/volatility/value 計算
    - feature_exploration.py  # 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py  # features テーブル生成ロジック
    - signal_generator.py     # final_score 計算と signals 生成
  - execution/                # 発注実行レイヤ（パッケージ用意）
  - monitoring/               # 監視用コード（SQLite 連携など）

---

## 補足・設計上の注意点

- 環境変数の自動読み込み:
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml に基づく）から `.env` / `.env.local` を自動で読み込みます。
  - 優先順位: OS 環境 > .env.local > .env
  - 無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- 冪等性:
  - DuckDB への保存は ON CONFLICT を用いた冪等性を重視しています（重複更新防止）。

- セキュリティ考慮:
  - news_collector は SSRF 対策、XML パースの堅牢化（defusedxml）等の安全対策を実装しています。
  - jquants_client は rate limit とリトライ・トークン自動リフレッシュを実装。

- テスト:
  - 各関数は DuckDB の in-memory モード ":memory:" を使えば外部 API に依存しない単体テストが可能です（ただし jquants_client のネットワーク呼び出しはモック推奨）。

---

README に記載した以外の詳細ドキュメント（StrategyModel.md, DataPlatform.md, DataSchema.md 等）をプロジェクトルートに用意しておくと実運用時の理解が進みます。必要であれば README に追記する項目やサンプルを追加します。