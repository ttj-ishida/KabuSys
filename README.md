# KabuSys

KabuSys は日本株向けの自動売買システムのコアライブラリです。  
データ取得（J‑Quants）、ETL、特徴量計算、戦略シグナル生成、ニュース収集、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

このパッケージは次の責務を持ちます。

- J‑Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新対応）
- DuckDB を用いたデータスキーマ定義・初期化・保存（冪等）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- ニュース（RSS）収集と銘柄紐付け（SSRF対策、トラッキングパラメータ除去、メモリDoS対策）
- リサーチ向けファクター計算・特徴量探索ユーティリティ
- 戦略向け特徴量構築とシグナル生成ロジック（Zスコア正規化、コンポーネントスコアの統合、Bear フィルタ、売買シグナルの冪等書き込み）
- 発注/実行/監査のスキーマ（実行層）、および監査トレーサビリティの設計

設計上のポイント:
- ルックアヘッドバイアス回避（target_date 時点のデータのみを参照）
- 冪等性（ON CONFLICT / トランザクションによる置換）
- 外部ライブラリへの依存は必要最小限（例: duckdb, defusedxml）
- テストしやすさ（id_token の注入、環境変数自動ロードの無効化オプション等）

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local からの自動読み込み（優先度: OS 環境変数 > .env.local > .env）
  - 必須設定の取得（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL 制御

- データ層（kabusys.data）
  - J-Quants クライアント（jquants_client）
    - レート制御、リトライ、401 時のトークン自動リフレッシュ
    - fetch / save ユーティリティ（daily_quotes, financials, market_calendar）
  - ニュース収集（news_collector）
    - RSS 取得・XML パース（defusedxml）、URL 正規化、記事保存、銘柄抽出
    - SSRF/サイズ/圧縮/トラッキングパラメータ対策
  - データスキーマ初期化（schema）
    - DuckDB のテーブル定義（Raw / Processed / Feature / Execution / Audit）
    - init_schema / get_connection
  - ETL パイプライン（pipeline）
    - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
    - 差分取得・バックフィル・品質チェック連携
  - カレンダー管理（calendar_management）
    - 営業日判定・次/前営業日の検索・カレンダー更新ジョブ
  - 統計ユーティリティ（stats）
    - zscore_normalize（クロスセクションの Z スコア正規化）

- リサーチ（kabusys.research）
  - ファクター計算（factor_research: momentum / volatility / value）
  - 将来リターン計算・IC / ランク関数・統計サマリー（feature_exploration）

- 戦略（kabusys.strategy）
  - 特徴量構築（feature_engineering.build_features）
    - research の raw ファクターを正規化し features テーブルへ UPSERT
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合し final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ書き込む

- 監視・監査（kabusys.data.audit）
  - signal_events / order_requests / executions などの監査用スキーマ（トレーサビリティ）

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（PEP 604 の型記法などを使用）
- DuckDB を利用するためネイティブ拡張のビルドは不要（pip でインストール可）

1. リポジトリをチェックアウトしてパッケージをインストール（開発モード）
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install -e .
   ```
   依存パッケージ（例）:
   - duckdb
   - defusedxml

   上記が requirements.txt に含まれていない場合は個別にインストールしてください:
   ```
   pip install duckdb defusedxml
   ```

2. 環境変数の設定
   - 必須（本番/テスト条件による）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV (default: development) — 値: development / paper_trading / live
     - LOG_LEVEL (default: INFO)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化できます（テスト用）

   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（.env.local が優先）。

3. DuckDB スキーマ初期化
   Python REPL またはスクリプトから:
   ```python
   import duckdb
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   # init_schema はテーブルをすべて作成して DuckDB 接続を返します
   conn.close()
   ```

---

## 使い方（よく使う例）

- 日次 ETL を実行してデータを更新する
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.data.pipeline import run_daily_etl

  # 初回は init_schema を使う (ファイル作成・テーブル作成)
  conn = init_schema(settings.duckdb_path)

  # 日次 ETL（today を指定しない場合は今日）
  result = run_daily_etl(conn)
  print(result.to_dict())
  conn.close()
  ```

- 特徴量を構築して戦略シグナルを生成する
  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features, generate_signals

  conn = get_connection(settings.duckdb_path)
  target = date(2025, 3, 1)

  # features を構築
  n = build_features(conn, target)
  print("features upserted:", n)

  # シグナルを生成（デフォルト閾値 0.60）
  s = generate_signals(conn, target)
  print("signals written:", s)
  conn.close()
  ```

- ニュース収集ジョブを実行する
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  # known_codes は銘柄抽出に使う有効な銘柄コード集合
  known_codes = {"7203", "6758", "9984", ...}
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  conn.close()
  ```

- J‑Quants のデータを直接取得して保存する（テスト・開発用）
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import get_connection
  from kabusys.config import settings
  from datetime import date

  conn = get_connection(settings.duckdb_path)
  recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, recs)
  print("saved:", saved)
  ```

注意:
- generate_signals / build_features は DuckDB の特定テーブル（features, ai_scores, positions, prices_daily, raw_financials など）を参照します。事前に該当データを ETL で投入してください。
- run_daily_etl は内部で品質チェックを呼び出します（quality モジュール）。品質エラーは ETLResult に格納されます。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

.env の例:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## ディレクトリ構成

以下はパッケージ内部の主要なファイル/モジュール構成（src/kabusys 以下）です。

- src/kabusys/
  - __init__.py
  - config.py                            — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py                  — J‑Quants API クライアント + 保存関数
    - news_collector.py                  — RSS ニュース収集・保存・銘柄抽出
    - schema.py                          — DuckDB スキーマ定義・初期化
    - pipeline.py                        — ETL パイプライン（run_daily_etl 等）
    - stats.py                           — zscore_normalize 等統計ユーティリティ
    - features.py                        — データ層の特徴量インターフェース
    - calendar_management.py             — 市場カレンダー管理
    - audit.py                           — 監査ログ用スキーマ
    - (その他: quality モジュール等想定)
  - research/
    - __init__.py
    - factor_research.py                 — momentum / volatility / value 計算
    - feature_exploration.py             — IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py             — features テーブル構築
    - signal_generator.py                — final_score 計算 & signals 書き込み
  - execution/
    - __init__.py                         — 実行層（発注・オーダー処理）はここに拡張
  - monitoring/                           — 監視・メトリクス（存在する場合）
  - その他の補助モジュール

---

## 開発・テストに関するメモ

- 環境変数の自動ロードは .env / .env.local をプロジェクトルートから探して行います。テストで明示的に環境を制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化してください。
- J‑Quants クライアントはレート制御とリトライを実装していますが、テストでは外部 API 呼び出しをモックしてください。get_id_token や _urlopen などは差し替え可能な箇所です。
- DuckDB の接続は軽量なのでユニットテストでは ":memory:" を使うと高速にテストできます。
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")
  ```
- 外部依存（ネットワークや実API）を使う統合テストは別途環境変数やテスト用トークンを使って実行してください。

---

## 参考・注意事項

- この README はソースコード（docstrings）に基づく概要です。詳細仕様（StrategyModel.md, DataPlatform.md 等）はソースリポジトリ内の設計文書を参照してください。
- 本パッケージは金融系ロジックを含みます。実運用時は十分なバックテスト・リスク管理・監査が必須です。

---

もし README に追加したい「運用手順」「CI の設定」「サンプルデータロード手順」などがあれば教えてください。README をそれに合わせて追記します。