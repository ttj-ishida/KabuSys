# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
DuckDB をデータ層に用い、J-Quants API と RSS ニュースを取り込み、ファクター計算 → 特徴量作成 → シグナル生成までを一貫して扱うことを目的としたモジュール群です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の層を備えた設計になっています。

- Data Layer（DuckDB）
  - J-Quants から取得した生データ（株価・財務・カレンダー）を raw 層へ保存
  - 生データの整形（prices_daily 等）およびニュース収集（RSS）
  - スキーマ定義・初期化、ETL パイプライン
- Research / Feature 層
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - クロスセクション Z スコア正規化などの統計ユーティリティ
  - 研究用の IC / フォワードリターン解析ツール
- Strategy 層
  - 正規化済みファクターと AI スコアを統合して最終スコアを計算
  - BUY / SELL シグナルを生成し signals テーブルに書き込む
- Execution / Monitoring 層（インターフェース置き場）
  - 発注・約定・ポジション監査などのスキーマを含む（実際のブローカ接続は分離）
- 設定管理
  - .env ファイルや環境変数から設定を読み込むユーティリティ（自動ロード機構あり）

設計の方向性として、ルックアヘッドバイアス回避、冪等性（ON CONFLICT / トランザクション）、外部依存を最小に（標準ライブラリ優先）することを重視しています。

---

## 主な機能一覧

- 環境設定管理（自動 .env 読み込み、必須チェック）
- DuckDB スキーマの定義と初期化（多数の Raw / Processed / Feature / Execution テーブル）
- J-Quants API クライアント（認証リフレッシュ、レート制御、リトライロジック、ページネーション）
- 株価・財務・カレンダーの差分 ETL（差分取得 / バックフィル / 品質チェック統合）
- ファクター計算（モメンタム / ボラティリティ / バリュー）
- 特徴量作成（Zスコア正規化、ユニバースフィルタ、features テーブルへの UPSERT）
- シグナル生成（final_score の計算、Bear レジーム抑制、BUY/SELL 判定、signals テーブルへの書き込み）
- ニュース収集（RSS からの記事取得、前処理、raw_news 保存、銘柄抽出）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等のユーティリティ）
- 監査ログ用スキーマ（signal → order_request → execution の追跡を想定）

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の `X | None` 構文を使用）
- システムに pip と仮想環境ツールがあること

1. リポジトリをクローン／取得する
2. 仮想環境を作成して有効化
   - Unix/macOS:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
3. 必要パッケージをインストール（最低限）
   - 必須: duckdb, defusedxml
   - 例: requirements.txt を整備している場合:
     ```bash
     pip install -r requirements.txt
     ```
   - 単発:
     ```bash
     pip install duckdb defusedxml
     ```
   - （プロジェクトを editable インストールする場合）
     ```bash
     pip install -e .
     ```
   - 補足: Slack 通知や外部ライブラリを使う場合は追加でそれらをインストールしてください。

4. 環境変数 / .env を用意する
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動的に読み込まれます（自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須環境変数（少なくとも以下を設定してください）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（execution 層利用時）
     - SLACK_BOT_TOKEN: Slack 通知を行う場合
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / ...（デフォルト INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env 読み込みを無効化
     - DUCKDB_PATH: DuckDB ファイルの保存先（デフォルト `data/kabusys.duckdb`）
     - SQLITE_PATH: 監視用 SQLite（デフォルト `data/monitoring.db`）

例 .env（簡易）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要なサンプル）

以下は Python REPL / スクリプト内での利用例です。適宜ログ設定やエラーハンドリングを追加してください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL 実行（J-Quants からの差分取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ今日
print(result.to_dict())
```

3) 特徴量（features）作成
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date(2025, 1, 20))
print(f"features upserted: {n}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date(2025, 1, 20))
print(f"signals written: {count}")
```

5) ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出時のホワイトリスト。None の場合は抽出をスキップ。
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
print(res)
```

6) マーケットカレンダー更新（夜間バッチ想定）
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar rows saved: {saved}")
```

7) J-Quants からの生データ取得を直接行って保存する
```python
from kabusys.data import jquants_client as jq
from datetime import date

records = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,20))
saved = jq.save_daily_quotes(conn, records)
```

---

## 主要モジュールとディレクトリ構成

（リポジトリの `src/kabusys` 以下を想定）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 読み込み、Settings オブジェクト（settings）を提供
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証・レート制御・保存ユーティリティ）
    - news_collector.py
      - RSS 取得、前処理、raw_news / news_symbols 保存
    - schema.py
      - DuckDB スキーマ定義、init_schema / get_connection
    - pipeline.py
      - 差分 ETL（run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - features.py
      - data.stats の公開インターフェース
    - calendar_management.py
      - 営業日判定、calendar_update_job 等
    - audit.py
      - 監査ログ向けの DDL（signal_events / order_requests / executions 等）
    - ...（その他モジュール）
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py
      - build_features（raw ファクターを正規化して features テーブルへ）
    - signal_generator.py
      - generate_signals（features / ai_scores → signals）
  - execution/
    - __init__.py
    - （発注・監視の実装を置く想定）
  - monitoring/
    - （監視・アラートの実装を置く想定）

---

## 環境変数（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API 用パスワード（execution 利用時）
  - SLACK_BOT_TOKEN — Slack 通知を使う場合
  - SLACK_CHANNEL_ID — Slack 通知先チャンネル
- 任意 / デフォルトあり
  - KABUSYS_ENV — development / paper_trading / live（default: development）
  - LOG_LEVEL — ログレベル（default: INFO）
  - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH — (監視用) SQLite ファイルパス（default: data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

config.Settings によって必須チェックが入り、未設定の場合はエラーになります。

---

## 運用上の注意・設計ポイント

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト等で無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のスキーマは冪等（IF NOT EXISTS / ON CONFLICT）を前提に設計されています。初回は `init_schema()` を呼んでください。
- J-Quants API にはレート制限（120 req/min）があるため、jquants_client で固定間隔スロットリングを実装しています。並列実行時は注意してください。
- 各 ETL / バッチ処理は部分的な失敗を許容する設計です（他のステップは継続）。重要なエラーは ETLResult.errors / quality チェックで検出できます。
- ルックアヘッドバイアス防止のため、各処理は target_date 時点の利用可能データのみを参照することを意識しています。
- 実際のブローカー発注実装（execution 層）と監査ログ連携は別途実装して使用してください。

---

## 今後の拡張案（例）

- execution 層の具体的なブローカ API 統合（kabuステーション、他ブローカー）
- Slack / メトリクス連携による監視・アラート
- AI スコア算出パイプラインの統合（ai_scores の投入）
- 単体テストと CI 用の pytest テスト群・Fixtures の整備

---

ライセンスやコントリビューション規約が別途あればその情報を追記してください。README の補足やサンプルスクリプトの追加を希望される場合は、どのワークフロー（ETL / シグナル生成 / 発注など）を優先するか教えてください。