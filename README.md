# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（ライブラリ/バッチ処理向けモジュール群）。

このリポジトリは、データ収集（J‑Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、DuckDB スキーマおよび監査ログを扱うユーティリティを提供します。発注実行やブローカー連携は別層（execution）で扱う設計になっています。

バージョン: 0.1.0

---

## 主要機能

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得 API（settings オブジェクト）
- データ取得・永続化
  - J‑Quants API クライアント（認証・ページネーション・レート制御・リトライ）
  - 日次株価（OHLCV）・財務データ・マーケットカレンダーの取得と DuckDB への冪等保存
- ETL パイプライン
  - 差分取得・バックフィル対応の日次 ETL（run_daily_etl）
  - 品質チェックを統合（quality モジュールとの連携想定）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（init_schema）
- 特徴量エンジニアリング
  - research で計算した raw ファクターを正規化・フィルタして features テーブルへ保存（build_features）
  - zscore 正規化ユーティリティ
- シグナル生成
  - features と ai_scores を統合して final_score を算出、BUY/SELL シグナル生成（generate_signals）
  - Bear レジーム判定、エグジット（ストップロス等）判定
- ニュース収集
  - RSS フィード取得・前処理・raw_news への冪等保存、記事と銘柄コードの紐付け（run_news_collection）
  - SSRF / XML BOM / gzip / サイズ制限等を考慮した堅牢な実装
- 監査ログ（audit）
  - signal_events / order_requests / executions などの監査テーブル定義（トレーサビリティ確保）

---

## 必要条件

- Python 3.10 以上
  - （Union types の `Path | None` 等の構文、および型ヒントの使用に合わせ）
- 主要依存パッケージ（最低限）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# または requirements.txt があれば: pip install -r requirements.txt
```

---

## 環境変数（.env）

config モジュールはプロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動で読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J‑Quants の refresh token
- KABU_API_PASSWORD (必須) — kabu ステーション API 用パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

.env の書式はシェルの export 形式やコメント行に対応しています。`.env.local` は `.env` の上書きに使えます（OS 環境変数は上書きされません）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. 仮想環境作成・依存インストール
   - python >=3.10 を用意
   - pip install duckdb defusedxml
3. 環境変数を設定
   - プロジェクトルートに `.env` を作成（.env.example を参考に）
4. DuckDB スキーマ初期化
   - Python REPL やスクリプトから init_schema を実行して DB を作成

例:
```python
from kabusys.data.schema import init_schema, get_connection, settings
from datetime import date

# init schema (ファイルは settings.duckdb_path を参照するか明示的に指定)
conn = init_schema(settings.duckdb_path)
# またはメモリ DB:
# conn = init_schema(":memory:")
```

---

## 基本的な使い方（例）

以下は主要ワークフローの簡易例です。

1) 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量の生成（features テーブルへ）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025, 3, 1))
print(f"features upserted: {n}")
```

3) シグナル生成（signals テーブルへ）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2025, 3, 1))
print(f"signals written: {count}")
```

4) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 既知銘柄コードセット（抽出に使用）
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

5) J‑Quants から直接データを取得して保存する例
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema, get_connection

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"saved: {saved}")
```

---

## API（主な公開関数 / オブジェクト）

- kabusys.config.settings
  - 設定はプロパティ経由（例: settings.jquants_refresh_token, settings.duckdb_path, settings.env）
- kabusys.data.schema
  - init_schema(db_path) -> DuckDB 接続（スキーマ作成）
  - get_connection(db_path) -> 接続（スキーマ初期化はしない）
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token(refresh_token=None)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=..., weights=...)
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=...)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/設定読み込み
  - data/
    - __init__.py
    - jquants_client.py — J‑Quants API クライアント（取得/保存）
    - news_collector.py — RSS 収集・前処理・DB保存
    - schema.py — DuckDB スキーマ定義 / init_schema
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - calendar_management.py — マーケットカレンダー操作（営業日判定等）
    - audit.py — 監査ログ用テーブル定義
    - features.py — data.stats の公開ラッパー
    - (その他: quality 等、品質チェック用モジュール想定)
  - research/
    - __init__.py
    - factor_research.py — mom/vol/value 等のファクター計算（prices_daily/raw_financials を参照）
    - feature_exploration.py — forward returns / IC / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features（ユニバースフィルタ、正規化、UPSERT）
    - signal_generator.py — generate_signals（final_score、BUY/SELL 判定）
  - execution/ — 発注/約定/ブローカー連携層（未実装のエントリポイント）
  - monitoring/ — 監視・アラート用モジュール（SQLite 等を使う想定）

（README を含め、プロジェクトルートには pyproject.toml や .git 等があることを前提に .env 自動読み込みが動作します）

---

## 動作設計上の注意点 / ポリシー

- ルックアヘッドバイアス回避:
  - 特徴量・シグナル生成は target_date 時点で入手可能なデータのみを使用する設計。
  - J‑Quants データ取得では fetched_at を UTC で記録し、いつデータが得られたかトレース可能にする。
- 冪等性:
  - DB への INSERT は ON CONFLICT/UPSERT を活用し、再実行可能に設計。
- レート制御・リトライ:
  - J‑Quants クライアントは秒間間隔で固定スロットリング（120 req/min 相当）と指数バックオフを実装。
- セキュリティ:
  - RSS 取得は SSRF/プライベートアドレスアクセス防止、XML パーサの安全な実装（defusedxml）を採用。
- エラーハンドリング:
  - ETL 処理はステップごとに独立してエラーハンドリングし、可能な限り他処理を継続する（Fail‑Fast ではない）。

---

## テスト・デバッグ

- 環境変数の自動ロードを無効化することでテスト時の副作用を避けられます:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- DuckDB のインメモリモード (":memory:") を使えば一時的に DB を構築してユニットテストが容易になります。
- 一部のネットワーク呼び出し（jquants_client._request や news_collector._urlopen）はモックしやすい設計です。

---

## 今後の追加想定

- execution 層（ブローカー連携、注文送信、注文状態管理）の実装補完
- quality モジュールの具体実装（ETL pipeline と統合済み）
- CI / テストケース、requirements.txt の整備
- ドキュメント（DataPlatform.md / StrategyModel.md 等）のリポジトリ内添付

---

問題報告・貢献:
- バグや改善提案は Issue を作成してください。プルリク歓迎です。

以上。必要であれば README に含めるサンプル .env.example、実行スクリプト（cron / systemd 例）、より詳細な API リファレンスを追加します。どの情報を優先して追記しましょうか？