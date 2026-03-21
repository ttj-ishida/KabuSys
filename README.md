# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群です。データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなど、戦略開発〜実行に必要な主要コンポーネントを含みます。

主な設計方針は次の通りです。
- ルックアヘッドバイアスを防ぐ（target_date 時点のデータのみ使用）
- DuckDB をコアの永続化層として使用（冪等保存を重視）
- API 呼び出しはレート制御・リトライ・トークンリフレッシュ対応
- DB 操作はトランザクション・バルク挿入で原子性を確保
- ライブラリは research（研究）と production（運用）両方のユースケースを想定

---

## 機能一覧

- 環境設定管理（.env 自動読み込み / 強制無効化オプション）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、マーケットカレンダー取得
  - レート制限・リトライ・トークンリフレッシュ実装
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
- 特徴量計算（momentum / value / volatility / liquidity 等）
- 特徴量正規化（Zスコア）
- シグナル生成（最終スコア計算、BUY/SELL 判定、Bear レジーム抑制、エグジットルール）
- ニュース収集（RSS フィード取得、前処理、銘柄抽出、冪等保存）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ / 発注トレーサビリティ用スキーマ
- 各種ユーティリティ（統計関数、URL 正規化、SSRF 対策 など）

---

## 必須・推奨依存パッケージ

最低限必要な Python パッケージ（例）
- duckdb
- defusedxml

（pip でインストールしてください）
例:
```
pip install duckdb defusedxml
```

プロジェクト配布形式によっては `pip install -e .` 等でインストール可能です。

---

## 環境変数（必須）

以下はこのライブラリが参照する主要な環境変数です。`.env` と `.env.local` をプロジェクトルートに置くことで自動ロードされます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 実行モード（development / paper_trading / live）。デフォルト `development`
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト `INFO`
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト `data/monitoring.db`）

注意:
- Settings クラスは環境変数の検証を行います。必要な値が無いと ValueError を投げます。

---

## セットアップ手順（簡易）

1. リポジトリをチェックアウト
2. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトに requirements.txt がある場合はそれを使用）
3. プロジェクトルートに `.env`（と必要なら `.env.local`）を作成して環境変数を設定
4. DuckDB スキーマを初期化
   - Python REPL やスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - またはインメモリ DB:
     ```python
     conn = init_schema(":memory:")
     ```

---

## 使い方（クイックスタート）

以下は代表的なワークフローの例です。

1. DuckDB 初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2. 日次 ETL を実行（J-Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しないと今日が対象
print(result.to_dict())
```

3. 特徴量の構築（features テーブルへ保存）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date(2024, 1, 4))
print(f"features built: {count}")
```

4. シグナル生成（signals テーブルへ保存）
```python
from kabusys.strategy import generate_signals
from datetime import date

n = generate_signals(conn, target_date=date(2024, 1, 4))
print(f"signals generated: {n}")
```

5. ニュース収集（RSS）と保存
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出に使う有効コードのセット（例: データベースから取得）
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

6. マーケットカレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

補足:
- generate_signals は weights や threshold を引数でカスタマイズ可能です。
- run_daily_etl は品質チェック（quality モジュール呼び出し）を行い、検出された問題を ETLResult.quality_issues に格納します。

---

## 注意点・運用メモ

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）で行われます。テスト時に自動ロードを防ぐには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API に対しては 120 req/min の制限を厳守するため固定間隔スロットリングを実装しています。
- API リトライは 408/429/5xx を対象に指数バックオフで行います。401 はトークンリフレッシュして 1 回リトライします。
- DuckDB への挿入は ON CONFLICT/DO UPDATE / DO NOTHING による冪等保存を基本としています。
- ニュース収集では SSRF 対策、XML の脆弱性対策（defusedxml）、レスポンスサイズチェックなどが組み込まれています。
- production（live）運用時は KABUSYS_ENV を `live` に設定し、ログレベルや通知設定を適切にしてください。

---

## 主要モジュールと API（抜粋）

- kabusys.config.Settings
  - settings.jquants_refresh_token / kabu_api_password / slack_bot_token / slack_channel_id
  - settings.duckdb_path / sqlite_path / env / log_level / is_live / is_paper / is_dev

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None)

- kabusys.research
  - calc_momentum(conn, date), calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=0.60, weights=None)

---

## ディレクトリ構成（主要ファイル）

以下はコードベースの主なファイル配置（抜粋）です。

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
      - calendar_management.py
      - audit.py
      - stats.py
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
    - monitoring/  (README に記載はあるが実装は省略されている場合あり)

（上記はリポジトリの一部を抜粋したものです。詳細はプロジェクトツリーを参照してください。）

---

## 開発・デバッグ時のヒント

- 環境変数が足りないと Settings プロパティから ValueError が出ます。テスト実行時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うか、テスト用の環境変数をセットしてください。
- DuckDB を用いた単体テストでは `init_schema(":memory:")` を使うと便利です。
- ネットワーク呼び出しのテストは jquants_client._request や news_collector._urlopen 等をモックして外部依存を切り離してください。
- ロギングは各モジュールで logger = logging.getLogger(__name__) を使っているため、ルート logger の設定で出力レベルやフォーマットを統一してください。

---

README の内容はプロジェクト内のドキュメント（StrategyModel.md / DataPlatform.md / DataSchema.md 等）と合わせて参照してください。必要であれば各モジュールの詳細な使用例（例: ETL スケジューラ設定、発注フローサンプル、監査ログの利用方法）を追加します。どの部分の詳細が欲しいか教えてください。