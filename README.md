# KabuSys

日本株向けの自動売買システム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、DuckDB スキーマ管理などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下のレイヤーを念頭に置いて設計されたモジュール群の集合です。

- Data Layer: J-Quants API 経由で株価 / 財務 / カレンダー / ニュースを取得し、DuckDB に保存する（冪等保存／差分更新／品質チェック）。
- Feature Layer: Research 用のファクター計算、クロスセクション正規化（Z スコア）を行い features テーブルを作成。
- Strategy Layer: 正規化済みファクターと AI スコアを統合して final_score を計算し BUY/SELL シグナルを生成。
- Execution / Audit: 発注・約定・ポジションのスキーマ定義および監査ログ（テーブル設計）を含む。

設計上のポイント:
- ルックアヘッドバイアス回避のため、常に target_date 時点までのデータのみを使用。
- DuckDB を単一の分析 DB として利用（ファイルまたはインメモリ）。
- API 呼び出しはレート制限・リトライ・トークン自動更新を考慮。
- ETL / DB 書き込みは冪等（ON CONFLICT）で実装。

---

## 主な機能一覧

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local の自動ロード（無効化可）
  - 必須設定の検証、環境判定（development/paper_trading/live）等

- データ取得・保存（kabusys.data）
  - J-Quants API クライアント（レートリミット、リトライ、トークンリフレッシュ）
  - デイリープライス / 財務 / カレンダーの取得・DuckDB への冪等保存
  - ニュース収集（RSS）と前処理、raw_news・news_symbols への保存（SSRF 対策・gzip/サイズ制限）
  - DuckDB スキーマ定義と初期化（init_schema）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）

- 研究（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - zscore_normalize（クロスセクション Z スコア正規化）

- 戦略（kabusys.strategy）
  - 特徴量構築（build_features）: research の生ファクターを統合・正規化して features テーブルへ保存
  - シグナル生成（generate_signals）: features と ai_scores を統合して BUY/SELL シグナルを signals テーブルへ保存

- その他
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - 監査ログ（signal_events / order_requests / executions など）用スキーマ定義

---

## セットアップ手順

前提:
- Python 3.10+（typing の Union 型短縮や型ヒントを利用）
- DuckDB をネイティブに使用可能な環境

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージ例（本リポジトリに requirements.txt が無い場合、最低限以下をインストールしてください）
   - duckdb
   - defusedxml

   例:
   ```
   pip install duckdb defusedxml
   ```

   （他にログ出力・テスト用ライブラリを追加することがあります）

3. パッケージとしてインストール（開発時）
   - プロジェクトルートに pyproject.toml があれば:
     ```
     pip install -e .
     ```
   - ない場合は、開発フォルダ直下から Python の import path を通す形で利用してください。

4. 環境変数の準備
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成します。
   - 例（.env.example）:
     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here

     # kabu API
     KABU_API_PASSWORD=your_kabu_station_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi

     # Slack (通知用)
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

     # DB パス
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

     # 動作モード: development | paper_trading | live
     KABUSYS_ENV=development

     # ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL
     LOG_LEVEL=INFO
     ```

   - 自動 .env 読み込みはデフォルトで有効。無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方（主要ユースケース）

以下は代表的な操作の例（Python スクリプトや REPL で実行）。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   # conn は duckdb.DuckDBPyConnection
   ```

2. 日次 ETL 実行（J-Quants からデータを差分取得して保存）
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

3. 特徴量構築（features テーブルの作成／更新）
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   n = build_features(conn, target_date=date(2025, 1, 31))
   print(f"features upserted: {n}")
   ```

4. シグナル生成（signals テーブルへ書き込み）
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date(2025, 1, 31))
   print(f"signals generated: {total}")
   ```

5. ニュース収集ジョブ（RSS から raw_news 保存）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9984"}  # 既知の銘柄セット（抽出用）
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

6. J-Quants API の直接利用例
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes
   # id_token を省略すると内部で refresh token を使って取得・キャッシュする
   quotes = fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
   ```

---

## 主要設定（環境変数）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知（必要に応じて）
- SLACK_CHANNEL_ID — Slack チャネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — 有効値: development, paper_trading, live （デフォルト: development）
- LOG_LEVEL — INFO 等（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env 自動ロードを無効化

注意: Settings クラスは未設定の必須環境変数に対して ValueError を投げます。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下）

- __init__.py
- config.py
  - 環境変数ロード / Settings
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py — RSS フィード取得・前処理・保存
  - schema.py — DuckDB スキーマ定義・init_schema/get_connection
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - stats.py — zscore_normalize 等統計ユーティリティ
  - features.py — zscore_normalize を再エクスポート
  - calendar_management.py — market_calendar 管理・営業日判定
  - audit.py — 監査ログ用テーブル DDL
  - quality.py — （参照されるがここでは抜粋されていない品質チェック用モジュール想定）
  - その他（raw テーブル関連など）
- research/
  - __init__.py
  - factor_research.py — calc_momentum / calc_volatility / calc_value
  - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
- strategy/
  - __init__.py
  - feature_engineering.py — build_features
  - signal_generator.py — generate_signals
- execution/
  - __init__.py
  - （発注・約定・ブローカー連携ロジック等を実装する想定）
- monitoring/ (エクスポート対象に含まれているが実体がない場合あり)

README に含まれるモジュール群は主にデータ処理・研究・戦略生成に関するもので、発注（execution）や監視（monitoring）は別途実装する想定です。

---

## 開発・運用上の注意点

- DuckDB ファイルはバックアップを取ること。分析・運用でファイル破損があると大きな影響が出ます。
- API レート制限（J-Quants: 120 req/min）に注意。jquants_client は内部でスロットリングを行っていますが、大規模並列化時は注意が必要です。
- 自動ロードされる .env の解析は独自実装（export 付き形式、クォート・コメント処理に対応）です。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化して外部ツールで読み込んでください。
- 本コードベースは「研究」→「戦略評価」→「信号生成」までを対象にしており、本番の板寄せ・発注ロジックやブローカー固有のエラーハンドリングは execution 層で別途実装してください。
- ニュース RSS 処理では SSRF 対策・XML パースの安全化（defusedxml）・レスポンスサイズ制限が実装されていますが、運用で新しい RSS ソースを追加する際は注意して検証してください。

---

必要であれば次の内容を追加できます:
- サンプルスクリプト（cron 用の daily_job.py など）
- テスト実行手順（ユニットテスト / CI 用）
- 詳細な DB スキーマ図（DataSchema.md 参照）
- 各モジュールの公開 API リファレンス

他に README に追記したい内容や、実際に使うためのサンプルスクリプトを作成する希望があれば教えてください。