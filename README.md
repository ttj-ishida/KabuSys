# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ（KabuSys）。  
データ収集（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、DuckDB スキーマ／監査ログなどのユーティリティを提供します。

主な目的は「研究（research）で得た生ファクターを処理して戦略へ繋げる」「外部 API へのアクセスを安全かつ冪等に行う」「DuckDB ベースでローカルにデータを管理する」ことです。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数（.env）設定例
- 使い方（よく使う API 例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下のレイヤーを備えたツールキットです。

- Data Layer: J-Quants API から株価・財務・市場カレンダーを取得し、DuckDB に保存（冪等処理）。
- ETL / Pipeline: 差分取得、バックフィル、品質チェックを行う日次 ETL。
- Research: ファクター計算（モメンタム、ボラティリティ、バリュー等）・探索用ユーティリティ（IC / 統計量）。
- Strategy: 特徴量正規化（Z スコア）、最終スコア算出、BUY/SELL シグナル生成（冪等）。
- Data Processing: RSS からニュース収集しテキスト前処理・銘柄抽出して保存。
- Schema / Audit: DuckDB スキーマ定義・初期化、監査ログ用テーブル。

設計方針として、ルックアヘッドバイアス防止、冪等性、API レート制御、ローカル DB でのトレーサビリティを重視しています。

---

## 機能一覧

主な機能（モジュール別）:

- kabusys.config
  - .env ファイル / 環境変数の自動読み込み（.env.local が .env を上書き）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN 等）
- kabusys.data
  - jquants_client: J-Quants API への安全なリクエスト、ページネーション、トークン自動リフレッシュ、保存関数（raw_prices / raw_financials / market_calendar 等）
  - schema: DuckDB のテーブル定義と初期化（init_schema）
  - pipeline: 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 取得、記事正規化、raw_news への冪等保存、銘柄抽出
  - calendar_management: 営業日/翌営業日/期間の営業日リスト取得、夜間カレンダー更新
  - stats: zscore_normalize（クロスセクション Z スコア）
- kabusys.research
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.strategy
  - build_features: research の生ファクターを正規化して features テーブルに UPSERT
  - generate_signals: features + ai_scores から final_score を計算し signals テーブルへ書き込み
- その他: execution / monitoring プレースホルダ（将来的な発注・監視機能）

主要設計上の配慮:
- API レート制御、指数バックオフ、401 の自動リフレッシュ
- DuckDB への挿入は ON CONFLICT で冪等
- ファクター正規化は欠損・外れ値（±3 clip）処理
- ニュース収集で SSRF / XML Bomb 対策（SSRF チェック、defusedxml、サイズ制限）

---

## セットアップ手順

※ 以下は最小限のセットアップ例です。プロジェクトのパッケージ化・requirements.txt に応じて調整してください。

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境を作成して有効化（推奨）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要なパッケージをインストール
   - 最低依存:
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - （パッケージ化されている場合）
     ```
     pip install -e .
     ```

4. 環境変数ファイル（.env）の作成（下節参照）

5. DuckDB スキーマの初期化:
   - Python REPL / スクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
     ```

---

## 環境変数（.env）設定例

config.Settings で使用される主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — モニタリング用デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — {development, paper_trading, live}（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意) — 1 を設定すると自動 .env 読み込みを無効化

サンプル `.env`:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

実装メモ:
- パッケージはプロジェクトルートを .git または pyproject.toml を基準に自動検出し、`.env` / `.env.local` を順に読み込みます。
- `.env.local` が存在すれば `.env` の値を上書きします（ただし OS 環境変数は保護されます）。
- テスト時や明示的に自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方

以下はよく使う操作の Python サンプルです。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
# ファイルパスは settings.duckdb_path などに合わせて指定
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants から差分取得して保存）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
# init_schema で得た conn を渡す
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 研究モジュールでファクター計算 → 特徴量作成
```python
from datetime import date
from kabusys.strategy import build_features

# conn: DuckDB 接続
n_upserted = build_features(conn, target_date=date(2024, 1, 4))
print(f"features upserted: {n_upserted}")
```

4) シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals

# threshold / weights をカスタマイズ可能
count = generate_signals(conn, target_date=date(2024, 1, 4), threshold=0.6)
print(f"signals generated: {count}")
```

5) ニュース収集ジョブ（RSS を取得して raw_news / news_symbols に保存）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は銘柄抽出に使用する有効銘柄コードセット（例: {'7203', '6758', ...}）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203', '6758'})
print(res)
```

6) J-Quants から生データを直接取得（テストや backfill 用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
print(saved)
```

エラーハンドリング:
- 各 ETL / 保存関数は内部でログ出力・例外を発生します。run_daily_etl は可能な限りステップごとにエラーを捕捉して処理を継続する設計です（結果 ETLResult.errors にエラー情報を格納）。

---

## ディレクトリ構成（主なファイル）

以下はパッケージ内の主要なファイル・モジュール構成（抜粋）です。

src/kabusys/
- __init__.py
- config.py                         — 環境変数・設定管理
- data/
  - __init__.py
  - jquants_client.py                — J-Quants API クライアント（取得・保存）
  - news_collector.py                — RSS ニュース収集・保存
  - schema.py                        — DuckDB スキーマ定義と init_schema
  - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py           — 市場カレンダー管理（is_trading_day 等）
  - features.py                       — zscore_normalize エクスポート
  - stats.py                          — 統計ユーティリティ（zscore_normalize）
  - audit.py                          — 監査ログ DDL
- research/
  - __init__.py
  - factor_research.py               — モメンタム／ボラティリティ／バリュー算出
  - feature_exploration.py           — IC / forward returns / summary
- strategy/
  - __init__.py
  - feature_engineering.py           — features テーブル作成（build_features）
  - signal_generator.py              — final_score 算出・signals 作成（generate_signals）
- execution/ (プレースホルダ)
- monitoring/ (プレースホルダ)

（上記は抜粋。schema.py は多数のテーブル DDL を定義しています。実際のファイル一覧はリポジトリを参照してください。）

---

## 注意点・実装メモ

- DuckDB をデータストアに採用しているため、パフォーマンス上は大量データの読み書きやトランザクションを意識してください。init_schema は一括で DDL を実行します。
- J-Quants API 呼び出しはレート制御（120 req/min）とリトライロジックを実装しています。大量のページネーション呼び出しを行う際は注意してください。
- ニュース収集では SSRF / XML バックドア / 大容量レスポンス等の防御を入れています（_SSRFBlockRedirectHandler、defusedxml、最大サイズチェック）。
- 設定は環境変数ベースです。CI / 本番では OS 環境変数で秘匿情報を与えることを推奨します。
- Strategy の各種閾値や重みは generate_signals の引数でオーバーライドできます。既定値は StrategyModel.md に基づいています（コード中の _DEFAULT_WEIGHTS, _DEFAULT_THRESHOLD 等）。

---

もし README に追加したいサンプルスクリプト、CI 設定、あるいは実際の運用手順（cron / Airflow 例など）があれば指定してください。README をそれに合わせて拡張します。