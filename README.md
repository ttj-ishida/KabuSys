# KabuSys

日本株向けの自動売買システム用ライブラリ群。データ取得（J-Quants）、ETL、特徴量生成、戦略シグナル生成、ニュース収集、監査ログ／スキーマ管理までの主要なコンポーネントを含みます。

本リポジトリはライブラリ形式で提供され、内部モジュールを組み合わせてバッチ／オンデマンド処理を構成できます。

---

## 概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新対応）
- DuckDB によるデータスキーマ定義と冪等保存
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量の正規化・合成（features テーブルへの保存）
- 戦略による最終スコア算出と BUY/SELL シグナル生成（signals テーブルへ保存）
- RSS ベースのニュース収集と銘柄抽出（SSRF 対策・サイズ制限・重複排除）
- 監査ログ（signal → order → execution のトレース）および実行層向けテーブル

設計上の注意点：
- ルックアヘッドバイアス対策のため、すべての計算は target_date 時点の利用可能データのみを参照します。
- DuckDB を中心に SQL と純粋な Python 標準ライブラリで実装されています（外部依存は最小限）。
- 冪等性（ON CONFLICT / INSERT DO NOTHING）・トランザクションによる原子性に配慮しています。

---

## 機能一覧

- 環境/設定管理（kabusys.config）
  - .env / .env.local を自動ロード（プロジェクトルート検出）
  - 必須設定の取得ヘルパ
- データ取得（kabusys.data.jquants_client）
  - daily_quotes / financials / market_calendar のページネーション対応フェッチ
  - レート制御（120 req/min）、指数バックオフ、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ
- スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブルおよびインデックス定義
  - init_schema() / get_connection()
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）: カレンダー → 価格 → 財務 → 品質チェック
  - 差分取得・バックフィル処理
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、記事ID生成、raw_news 保存、銘柄抽出
  - SSRF 対策・gzip/サイズガード
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev_trading_day、calendar_update_job
- 研究・ファクター計算（kabusys.research）
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic 等
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - 生ファクターの合成、Zスコア正規化、ユニバースフィルタ、features への UPSERT
- シグナル生成（kabusys.strategy.signal_generator）
  - コンポーネントスコア計算、AI スコア統合、Bear レジーム判定、BUY/SELL 作成、signals への日付単位置換
- 監査ログ / 実行層 DDL（kabusys.data.audit / schema）

---

## セットアップ手順

想定環境
- Python 3.9 以上（3.10/3.11 推奨）
- DuckDB（Python パッケージ）
- defusedxml（RSS パースの安全性向上のため）

1. リポジトリをクローン（既にある場合はスキップ）
   - git clone <repo_url>

2. 依存パッケージをインストール（例）
   - pip install duckdb defusedxml

   補足: 実際のプロジェクトでは requirements.txt / pyproject.toml を用意し、pip install -r requirements.txt または pip install . を使ってください。

3. 環境変数の設定
   - 必須:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — 通知先 Slack チャネル ID
   - 任意（デフォルトあり）:
     - KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視 DB 等（デフォルト: data/monitoring.db）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/…）
   - .env/.env.local をプロジェクトルートに置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。

4. データベース初期化
   - Python コンソールやスクリプトで DuckDB スキーマを作成します（例を次節に記載）。

---

## 使い方（主要なワークフロー例）

下記は最小限のサンプルコード例です。適宜 logging の設定や例外処理を追加してください。

1) DuckDB スキーマ初期化
```
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# 以降 conn を再利用して ETL / 計算を実行
```

2) 日次 ETL を実行（J-Quants から差分取得して保存）
```
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しなければ今日（営業日に調整される）
print(result.to_dict())
```

3) 特徴量（features）を構築
```
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date(2025, 1, 31))
print(f"features upserted: {n}")
```

4) シグナル生成
```
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date(2025, 1, 31))
print(f"signals written: {count}")
```

5) ニュース収集（RSS）
```
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄コードセット（銘柄抽出に使用）
known_codes = {"7203", "6758", ...}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) カレンダー先読みジョブ
```
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意点:
- J-Quants API 呼び出しにはレート制限やリトライポリシーが組み込まれています。大量同時実行は避けてください。
- get_id_token は内部でキャッシュされ、401 を受けると自動でリフレッシュして再試行します（一回のみ）。

---

## 環境変数（要点）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルト値あり）:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live / default: development)
- LOG_LEVEL (DEBUG / INFO / … / default: INFO)

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）を探索して .env と .env.local を読み込みます。
- 読み込み順: OS 環境 > .env.local > .env
- 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）

（省略可能な空 __init__ などは除く、実装上重要なモジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（フェッチ・保存）
    - schema.py                 — DuckDB スキーマ定義・init_schema / get_connection
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - news_collector.py         — RSS 収集・raw_news 保存・銘柄抽出
    - calendar_management.py    — market_calendar 管理、営業日ユーティリティ
    - features.py               — zscore_normalize の再エクスポート
    - stats.py                  — zscore_normalize 等統計ユーティリティ
    - audit.py                  — 監査ログ用 DDL（signal / order / execution ログ）
  - research/
    - __init__.py
    - factor_research.py        — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py    — forward returns / IC / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py    — features テーブル構築処理
    - signal_generator.py       — final_score 計算・signals 書き込み
  - execution/
    - __init__.py               — 発注/ブローカー連携層（将来的に実装）
  - monitoring/                 — 監視・外部通知など（将来的に追加）

---

## 追加の実装ノート / 注意事項

- 冪等性: DB への保存は可能な限り ON CONFLICT を利用して重複を避け、トランザクションで原子性を確保します。
- J-Quants クライアント:
  - レート制御（_RateLimiter）で 120 req/min を固定間隔で守ります。
  - リトライは 408/429/5xx を対象とした指数バックオフ、最大 3 回。
  - 401 発生時はリフレッシュトークンを用いて id_token を再発行して1回だけリトライします。
- News Collector:
  - SSRF 防止（リダイレクト先／ホストのプライベートアドレス検査）、レスポンスサイズ上限、gzip 解凍後の再チェックを実装しています。
  - 記事ID は正規化 URL の SHA-256 先頭 32 文字で生成して冪等性を保証します。
- 設計原則:
  - 本番の発注・execution 層へは strategy 層は直接依存しません。signal テーブルと signal_queue を介して分離します。
  - すべてのタイムスタンプは UTC を想定しています（監査ログ等）。

---

必要に応じて README に実行例のスクリプトや docker-compose、CI 設定、requirements.txt を追加すると導入がさらに容易になります。README の補足や利用例（cron / Airflow での日次ジョブ、Slack 通知の例など）が必要なら追加で作成します。