# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ群です。データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、DuckDB スキーマ・監査モデルなどを提供します。

> 注意: 本リポジトリはライブラリ/モジュールの集まりであり、実際の発注（ブローカー連携）や運用ジョブは別途実装することを想定しています。

---

## 概要

KabuSys は次の役割を持つコンポーネント群を含んでいます。

- J-Quants API クライアント（データ取得、トークン管理、レート制御、リトライ）
- DuckDB ベースのデータレイヤ（スキーマ定義と初期化）
- ETL パイプライン（差分取得、保存、品質チェック呼び出し）
- ニュース収集（RSS -> raw_news、銘柄抽出）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ）
- シグナル生成ロジック（ファクター + AI スコア統合、BUY/SELL の生成）
- カレンダー管理、監査ログ（注文から約定までのトレース用テーブル）

設計方針としては「ルックアヘッドバイアス防止」「冪等性」「API レート制御」「ロギングとトレーサビリティ」を重視しています。

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API から株価・財務・市場カレンダーをページネーション対応で取得
  - トークン自動リフレッシュ、指数バックオフによるリトライ、固定間隔レートリミッタ
  - DuckDB へ冪等的に保存する save_* 関数

- data/schema
  - DuckDB 用のテーブル定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema(db_path) による一括初期化

- data/pipeline
  - 日次 ETL 実行（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）

- data/news_collector
  - RSS フィード取得・XML パース（defusedxml 利用）・URL 正規化・記事保存
  - 記事から銘柄コード抽出して news_symbols に紐付け

- research
  - calc_momentum / calc_volatility / calc_value：prices_daily/raw_financials を用いたファクター計算
  - calc_forward_returns / calc_ic / factor_summary：ファクター評価・探索ツール
  - zscore_normalize：クロスセクションの Z スコア正規化

- strategy
  - build_features：research の生ファクターを統合・正規化して features へ保存
  - generate_signals：features と ai_scores を統合して BUY/SELL シグナルを signals に保存

- data/calendar_management
  - market_calendar の取得・営業日判定・next/prev_trading_day 等のユーティリティ

- data/audit
  - シグナル／発注要求／約定の監査テーブル定義（トレーサビリティ設計）

---

## 要件

- Python 3.10 以上（型アノテーションで PEP 604 等を使用しているため）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml

（プロジェクトの実際の requirements.txt に合わせて調整してください）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（例）

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要ライブラリをインストール

   例（最低限）:

   ```bash
   pip install duckdb defusedxml
   ```

   実運用では logging ライブラリ設定や Slack 連携（slack_sdk など）を追加してください。

3. 環境変数を設定

   .env または OS 環境変数で以下を設定します。リポジトリルートの `.env` / `.env.local` が自動読み込みされます（自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   必須（Settings._require により未設定で例外）:

   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
   - KABU_API_PASSWORD: kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   任意（デフォルト有り）:

   - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live) — default: development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO

   例 `.env`（テンプレート）:

   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化

   Python REPL またはスクリプトで:

   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)   # ファイルを作成してテーブルを作る
   conn.close()
   ```

---

## 使い方（代表的な操作例）

- 日次 ETL 実行（J-Quants から差分取得して保存・品質チェック）

  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- 特徴量の構築（features テーブルに書き込む）

  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.strategy import build_features

  conn = init_schema(settings.duckdb_path)
  n = build_features(conn, target_date=date.today())
  print(f"features upserted: {n}")
  conn.close()
  ```

- シグナル生成（features / ai_scores / positions を参照して signals に書き込む）

  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals

  conn = init_schema(settings.duckdb_path)
  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals written: {total}")
  conn.close()
  ```

- ニュース収集ジョブ

  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = init_schema(settings.duckdb_path)
  # known_codes: 銘柄抽出に使う有効コードの集合（例: prices_daily の code 列から取得）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
  print(results)
  conn.close()
  ```

---

## 環境変数／設定一覧

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意、development|paper_trading|live、デフォルト: development)
- LOG_LEVEL (任意、デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動的な .env ロードを無効化します。

---

## ディレクトリ構成

以下は主要ファイル／モジュールの概観（src/kabusys 以下）です。

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数/設定の読み込み・検証
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（fetch/save）
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - schema.py            — DuckDB スキーマ定義と init_schema/get_connection
    - news_collector.py    — RSS 収集・記事保存・銘柄抽出
    - calendar_management.py — カレンダー更新 / 営業日ユーティリティ
    - features.py          — zscore_normalize 再エクスポート
    - stats.py             — zscore_normalize 等の統計ユーティリティ
    - audit.py             — 監査ログテーブル定義
    - execution/           — 発注関連モジュール（骨組み）
  - research/
    - __init__.py
    - factor_research.py   — momentum/volatility/value の計算
    - feature_exploration.py — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py — features の生成・正規化
    - signal_generator.py    — final_score 計算・BUY/SELL シグナル生成
  - execution/              — 発注実装（ブローカー接続は別実装）
  - monitoring/             — 監視・アラート用（骨組み）

（上記は現状の主要モジュールであり、将来的に拡張される想定です）

---

## 運用上の注意点

- DuckDB ファイルはデフォルトで data/kabusys.duckdb に作成されます。運用環境では永続ボリュームに置いてください。
- J-Quants のレート制限（120 req/min）をコード内で守る設計になっていますが、並列リクエスト等は注意してください。
- features / signals などは日付単位で置換（DELETE してから INSERT）を行い冪等性を保っていますが、複数プロセスから同時更新する場合は運用上のロック設計が必要です。
- news_collector は外部 RSS を取得するため SSRF や XML 攻撃対策（defusedxml、ホストチェック、サイズ制限）を実装していますが、運用環境ではさらに監視を強化してください。
- KABUSYS_ENV により挙動（paper_trading/live）を切り替えられます。live の場合は認証情報・監査を特に厳密に扱ってください。

---

## 貢献・拡張案

- ブローカー API（kabuステーション）の発注ロジック実装（execution 層）
- AI スコア生成パイプライン（ai_scores の作成）
- 品質チェックモジュール（data/quality）が参照されているが未掲示の部分の実装とテスト
- CI / 自動デプロイ・監視ジョブ（ETL スケジューラ）
- 単体テスト・型チェック（mypy）・静的解析の追加

---

疑問点や README の追加情報（例: 実運用での cron / systemd 設定例、より詳しい .env.example）を希望であれば教えてください。必要に応じてサンプルスクリプトや運用手順を追加します。