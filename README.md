# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
DuckDB をデータレイクとして使用し、J-Quants からデータを取得して ETL → 特徴量生成 → シグナル生成 → 発注／監視へとつなぐことを想定したモジュール群を含みます。

---

## 特徴（概要）

- J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
- DuckDB ベースのデータスキーマ（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック向けフロー）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ）
- シグナル生成（複数コンポーネントの重み付け合成・Bear 判定・エグジットロジック）
- ニュース収集（RSS 取得・前処理・記事→銘柄紐付け・SSRF対策）
- マーケットカレンダー管理（営業日判定／next/prev 取得）
- 監査ログ（signal → order → execution のトレース保存設計）

---

## 主な機能一覧

- data/jquants_client.py
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - レートリミット、再試行、トークン自動リフレッシュ
- data/schema.py
  - DuckDB スキーマ定義と init_schema(db_path)
- data/pipeline.py
  - run_daily_etl: 日次 ETL（カレンダー、株価、財務、品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl
- data/news_collector.py
  - fetch_rss / save_raw_news / run_news_collection（SSRF 対策・前処理・チャンク挿入）
- data/calendar_management.py
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- research/factor_research.py
  - calc_momentum / calc_volatility / calc_value
- strategy/feature_engineering.py
  - build_features（Z スコア正規化・ユニバースフィルタ・features テーブルへ UPSERT）
- strategy/signal_generator.py
  - generate_signals（features と ai_scores を統合して BUY/SELL シグナル生成）
- data/stats.py
  - zscore_normalize（クロスセクション正規化ユーティリティ）
- config.py
  - 環境変数読み込み（.env, .env.local 自動ロード）と settings オブジェクト

---

## セットアップ手順

前提:
- Python 3.9+（typing 記法や一部型ヒントのため推奨）
- DuckDB がインストールされていること（pip 経由で duckdb を入手します）

1. クローン / パッケージ化
   - ローカルで編集する場合:
     - git clone ... を行い、プロジェクトルートで作業してください

2. 依存パッケージをインストール
   - 例（pip）:
     - pip install duckdb defusedxml
   - 開発環境なら:
     - pip install -e . など（setup 配置がある場合）

3. 環境変数設定
   - プロジェクトルートに `.env`（および必要で `.env.local`）を作成します。主なキー:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN (必須) — Slack Bot トークン
     - SLACK_CHANNEL_ID (必須) — Slack 投稿先チャンネル ID
     - DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH (任意) — 監視用 SQLite のパス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - 自動 .env ロードを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数にセットしてください（テスト用途など）

4. データベース初期化（DuckDB）
   - Python から schema.init_schema を呼び出して初期化します（例を下に記載）

---

## 使い方（代表的な例）

以下は最小限の使用例です。実運用ではログ設定やエラーハンドリング、ジョブスケジューラ（cron、Airflow 等）と組み合わせてください。

1) DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) J-Quants の ID トークンを取得（必要に応じて）

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

3) 日次 ETL を実行（カレンダー、株価、財務、品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しないと today を使用
print(result.to_dict())
```

4) 特徴量の構築（feature テーブルへ保存）

```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date(2025, 3, 20))
print(f"features upserted: {n}")
```

5) シグナル生成（signals テーブルへ保存）

```python
from kabusys.strategy import generate_signals
from datetime import date

total = generate_signals(conn, target_date=date(2025, 3, 20))
print(f"signals written: {total}")
```

6) ニュース収集ジョブ（RSS 収集→raw_news 保存→news_symbols 紐付け）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
new_counts = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(new_counts)
```

7) カレンダー更新ジョブ（夜間バッチ）

```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効にする（1）

注意: config.Settings は必須の環境変数が未設定だと ValueError を投げます。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数管理・自動 .env ロード
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント
    - news_collector.py      — RSS 収集・前処理・保存
    - schema.py              — DuckDB スキーマ定義・初期化
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - pipeline.py            — ETL パイプライン / run_daily_etl 等
    - calendar_management.py — 市場カレンダー管理
    - features.py            — data.stats の再エクスポート
    - audit.py               — 監査ログテーブル定義（signal/order/execution）
    - execution/             — 発注実行層（空 __init__ が存在）
  - research/
    - __init__.py
    - factor_research.py     — momentum/value/volatility の計算
    - feature_exploration.py — IC / forward returns / summary 等
  - strategy/
    - __init__.py  — build_features, generate_signals を公開
    - feature_engineering.py — features テーブル生成ロジック
    - signal_generator.py    — signals テーブル生成ロジック
  - monitoring/ （監視関連 DB / ロジックを置く想定フォルダ）

---

## 設計上の注意点・運用へのヒント

- DuckDB のスキーマは init_schema() で冪等に作成されます。初回起動時に呼び出してください。
- ETL は差分更新（最後の取得日ベース）かつ小さなバックフィルを行う設計です。ジョブスケジューラに日次実行させる想定です。
- J-Quants API はレート制限（120 req/min）を守るため内部でスロットリングします。大量取得や並列化は注意してください。
- ニュース取得は SSRF 対策や Gzip/サイズ上限チェックを実装していますが、社内ポリシーに合わせたネットワーク制御も推奨します。
- strategy 層は発注 API（execution 層）に直接アクセスしない設計です。signals テーブルを通じて発注層が行動するパターンを推奨します。
- 本 README はコードコメントと実装を要約したもので、詳細な仕様（StrategyModel.md / DataPlatform.md / DataSchema.md など）が別途ある前提です。

---

もし README に追加したい情報（例: 実行スクリプト・CI/CD 例・テストの書き方・外部設定テンプレート等）があれば教えてください。必要に応じて .env.example のテンプレートや運用手順書も作成します。