# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計された Python ライブラリです。  
J-Quants からの市場データ取得、DuckDB でのデータ蓄積、特徴量（features）生成、シグナル計算、ニュース収集、監査ログなどをワンストップで提供します。  
本 README はコードベース（src/kabusys）に基づく概要・セットアップ・使い方・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

- 目的: 日本株のデータプラットフォーム（ETL）と戦略層（特徴量生成・シグナル生成）を提供し、自動売買システムの基盤を構成する。
- 特徴:
  - J-Quants API クライアント（認証・レート制御・リトライ・ページネーション対応）
  - DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution 層）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - 研究用ファクター計算（Momentum / Volatility / Value 等）
  - 特徴量正規化（Zスコア）、シグナル生成（最終スコアの重み付け）
  - RSS ベースのニュース収集と銘柄紐付け
  - 監査・トレーサビリティ用テーブル群

---

## 機能一覧（主要）

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存関数（save_daily_quotes 等） — 冪等（ON CONFLICT）対応
- data.schema
  - DuckDB スキーマ定義・初期化（init_schema）
- data.pipeline
  - 日次 ETL（run_daily_etl）
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
- data.news_collector
  - RSS 取得（fetch_rss）、記事保存（save_raw_news）、銘柄抽出と紐付け（save_news_symbols）
- data.calendar_management
  - 営業日判定・前後営業日の取得・カレンダー更新ジョブ
- research.factor_research / research.feature_exploration
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算・IC（情報係数）や統計サマリー
- strategy.feature_engineering
  - 生ファクターの統合・Z スコア正規化・ユニバースフィルタ、features テーブルへの保存（build_features）
- strategy.signal_generator
  - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを signals テーブルへ書き込む（generate_signals）
- 設定管理（config）
  - .env / 環境変数自動ロード、必須環境変数のチェック（Settings クラス）

---

## システム要件（推奨）

- Python >= 3.10（| 型注釈、match 等を使わない実装だが union 型記法を使用しているため）
- DuckDB
- defusedxml
- （標準ライブラリを多用するが、実行環境には上記パッケージをインストールしてください）

例:
```
pip install duckdb defusedxml
# または、パッケージ化されている場合は:
# pip install -e .
```

---

## 環境変数 / .env

Settings で参照される主な環境変数（必須）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

任意 / デフォルトあり:

- KABUSYS_ENV — 実行環境 (development | paper_trading | live)、デフォルト `development`
- LOG_LEVEL — ログレベル（DEBUG, INFO...）、デフォルト `INFO`
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視など）パス（デフォルト: data/monitoring.db）

自動 .env ロード:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を探索し、`.env` と `.env.local` を自動ロードします。
- テスト等で自動ロードを無効にする場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

サンプル .env:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順

1. レポジトリをクローン / 取得
2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   # その他、プロジェクトで必要なパッケージがあれば追加してください
   ```
4. 環境変数を設定（.env をプロジェクトルートに配置）
5. DuckDB スキーマ初期化（例: Python から）
   ```python
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")  # ファイル作成とテーブル初期化
   ```
   - `":memory:"` を渡すとインメモリ DB を使用します。

---

## 使い方（簡易例）

以下は典型的なワークフローの例です。

1) 日次 ETL を実行して市場データ・財務情報・カレンダーを取得・保存する:
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量を生成して features テーブルに保存する:
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

3) シグナルを計算して signals テーブルへ保存する:
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date.today())
print(f"signals generated: {total}")
```

4) ニュース収集ジョブを実行する（RSS → raw_news / news_symbols）:
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

5) J-Quants API から日足データを直接フェッチして保存する（テスト用途）:
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")

# id_token を明示的に取得して注入することも可能
token = jq.get_id_token()
records = jq.fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

注意点:
- run_daily_etl は複数のステップ（calendar → prices → financials → quality checks）を順に実行し、各ステップは失敗しても他を継続する振る舞いです。
- build_features / generate_signals は target_date 時点のデータのみを使用するように設計されており、ルックアヘッドバイアスを防止します。

---

## 主要 API（抜粋）

- kabusys.config.settings: 環境設定アクセサ（Settings インスタンス）
- kabusys.data.schema.init_schema(db_path) -> DuckDB connection
- kabusys.data.schema.get_connection(db_path) -> DuckDB connection
- kabusys.data.pipeline.run_daily_etl(conn, target_date=...)
- kabusys.strategy.build_features(conn, target_date=...)
- kabusys.strategy.generate_signals(conn, target_date=..., threshold=..., weights=...)
- kabusys.data.news_collector.run_news_collection(conn, sources=..., known_codes=...)

ログレベルや挙動の調整は環境変数（LOG_LEVEL / KABUSYS_ENV）で行えます。

---

## ディレクトリ構成（src/kabusys、主要ファイル）

- kabusys/
  - __init__.py
  - config.py — 環境変数管理 (.env 自動ロード、Settings)
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（認証・取得・保存）
    - news_collector.py — RSS ニュース取得・保存・銘柄抽出
    - schema.py — DuckDB スキーマ定義と init_schema
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - audit.py — 監査ログ / トレーサビリティの DDL（監査テーブル）
    - features.py — features 関連の公開インターフェース
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py — 生ファクター合成・正規化・features へ保存
    - signal_generator.py — final_score 計算・BUY/SELL 判定・signals 保存
  - execution/ (空パッケージ: 実際の発注関連は別実装想定)
  - monitoring/ (一部監視用 DB 連携を想定)

---

## 開発・運用上の注意

- 環境変数は機密情報（API トークン等）を含みます。`.env` をバージョン管理に入れないでください。
- DuckDB のファイルパスは環境変数で指定できます（DUCKDB_PATH）。同一 DB に複数プロセスが同時にライトする場合はロックや設計に注意してください。
- J-Quants の API レート制限（120 req/min）を守るため、jquants_client は内部でスロットリングを行います。大量リクエストの際は配慮してください。
- ニュース収集では外部 URL のパース・SSRF 対策・Gzip サイズチェック等の防御を実装していますが、運用時は追加の監視（異常なフィード等）を行ってください。
- generate_signals の重み（weights）を外部から与える際は正規化ルールに従ってください（負値・非数は無視されます）。

---

## 今後の拡張案（参考）

- execution 層: 実際の発注連携（kabu API / ブローカー SDK）とエラーハンドリング
- Web UI / ダッシュボード: signals / positions / performance の可視化
- モデル/AI スコアの学習パイプライン統合
- 単体テスト・CI ワークフローの整備

---

必要であれば、README に CLI コマンド例（Makefile / run scripts）や、より詳しいテーブル定義説明（DataSchema.md 相当の抜粋）、運用手順（バックアップ、メンテナンス）を追加します。どの部分を詳しく書くか指定してください。