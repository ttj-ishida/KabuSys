# KabuSys

日本株のデータ取得・特徴量生成・シグナル生成を行う自動売買システムのコアライブラリ（勉強用／実運用向けの基盤コード）。  
モジュールは主に Data / Research / Strategy / Execution 層で構成され、DuckDB を使ったローカルデータベースを中心に動作します。

---

## 主な目的（概要）
- J-Quants API から市場データ（株価・財務・カレンダー）を取得して DuckDB に保存する ETL 基盤
- 取得データを加工して特徴量（features）を作成する特徴量エンジニアリング
- 正規化済みファクターと AI スコアを統合して売買シグナルを生成
- ニュース収集（RSS）とテキスト前処理、銘柄紐付け
- マーケットカレンダー管理、監査ログ（発注〜約定のトレーサビリティ）などの補助機能

設計上の重点：
- レートリミット遵守、リトライ、トークン自動リフレッシュ（J-Quants クライアント）
- DB 保存は冪等（ON CONFLICT で更新）で再実行可能
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみ利用）
- セキュリティ対策（RSS 取得時の SSRF 対策、XML パースの安全化 など）

---

## 機能一覧
- データ取得 / ETL
  - J-Quants API クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - rate limiting、リトライ、401 時のトークンリフレッシュ対応
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
- データベース
  - DuckDB スキーマ定義と初期化（init_schema）
  - raw / processed / feature / execution レイヤーのテーブル
- 特徴量・研究
  - ファクター計算（momentum / volatility / value）
  - Z スコア正規化ユーティリティ
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- 戦略
  - 特徴量の構築（build_features）
  - final_score によるシグナル生成（generate_signals）、BUY/SELL 判定、SELL の優先処理
- ニュース
  - RSS 収集（fetch_rss）、記事正規化、raw_news 保存、銘柄コード抽出と紐付け
  - SSRF 対策、gzip サイズ制限、XML の defusedxml での安全パース
- カレンダー管理
  - 営業日判定・次/前営業日取得・期間内営業日リスト
  - カレンダーの差分更新ジョブ（calendar_update_job）
- 監査 / 発注系（スキーマ）
  - signal_events / order_requests / executions などの監査テーブル定義

---

## 必要条件 / 依存
- Python 3.10+
- 必須パッケージ（代表例）:
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, datetime, logging, etc.）を多用

（プロジェクト配布時は requirements.txt を用意してください。）

---

## 環境変数（主なもの）
このモジュールは .env を自動読み込みします（プロジェクトルートに .git または pyproject.toml がある場合）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（Settings._require で検証されるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（execution 層利用時）
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabuapi の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development", "paper_trading", "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

例（.env の最小サンプル）:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカルでの基本）
1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（例）
   - pip install duckdb defusedxml
   - （必要に応じて他の依存を追加）
4. プロジェクトルートに .env を作成して必要な環境変数を設定
5. DuckDB スキーマを初期化
   - 簡単なスクリプト例:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     init_schema(settings.duckdb_path)
     ```
   - または: python -c "from kabusys.data.schema import init_schema; from kabusys.config import settings; init_schema(settings.duckdb_path)"
6. ETL を実行（後述の使い方を参照）

---

## 使い方（サンプル）
以下はライブラリ関数を直接呼ぶ簡単な例です。実際は logger 設定やエラー処理、ジョブのスケジューリング（cron 等）を行ってください。

1) DuckDB 初期化（1回だけ）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL の実行（市場カレンダー取得 → 株価 / 財務 差分取得 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量構築（features テーブルへ書き込み）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, date(2024, 1, 10))
print(f"features upserted: {n}")
```

4) シグナル生成（signals テーブルへ書き込み）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, date(2024, 1, 10), threshold=0.6)
print(f"signals generated: {total}")
```

5) ニュース収集ジョブ（RSS 収集 + raw_news 保存 + 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes を渡すと記事から銘柄抽出して news_symbols に紐付ける
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)
```

6) カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## 注意事項 / 運用上のポイント
- Python のバージョンは 3.10 以上（PEP 604 の型 | を利用）。
- J-Quants の API レート制限（120 req/min）に従うため、fetch は内部でレート制御されます。
- ETL は idempotent に設計されているため再実行可能ですが、外部 API のレスポンスや DB の状態に応じて差分取得されます。
- features/signal のロジックはルックアヘッドバイアスを避けるよう target_date 時点のデータのみを参照します。
- RSS 収集は SSRF 対策や受信バイト数制限を実装していますが、運用環境での追加検証を推奨します。
- 自動 .env ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。

---

## ディレクトリ構成（主要ファイル）
（リポジトリを src 配下にパッケージ化している想定）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存）
    - news_collector.py        — RSS 収集・前処理・保存・銘柄抽出
    - schema.py                — DuckDB スキーマ定義と init_schema/get_connection
    - stats.py                 — zscore_normalize 等の統計ユーティリティ
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   — 市場カレンダー管理 / ジョブ
    - features.py              — data 側の特徴量ユーティリティ公開
    - audit.py                 — 監査ログ用スキーマ（signal_events 等）
    - (その他: quality モジュール等を想定)
  - research/
    - __init__.py
    - factor_research.py       — momentum/volatility/value の計算
    - feature_exploration.py   — 将来リターン / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py   — build_features（正規化・ユニバースフィルタ）
    - signal_generator.py      — generate_signals（final_score 計算、BUY/SELL）
  - execution/                 — 発注関連（パッケージ構造のみ。実装は別）
  - monitoring/                — 監視/アラート（パッケージ構造のみ）

（実際のツリーはリポジトリの内容に合わせてください）

---

## 開発者向けメモ
- テスト時に .env の自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB を :memory: で起動すれば一時的にメモリ DB を利用可能（init_schema(":memory:")）
- 大量データの挿入は executemany / チャンク化しているのでメモリ負荷は抑えられています
- ロギングを適切に設定してジョブの進捗と警告を収集してください

---

もし README に追加したい情報（例: 実行スケジュール例、システム図、requirements.txt の正確な中身、CI 設定、Docker 化手順など）があれば教えてください。必要に応じて追記します。