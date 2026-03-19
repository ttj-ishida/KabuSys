# KabuSys

日本株向けの自動売買基盤ライブラリ群（リサーチ / データプラットフォーム / 戦略 / 発注監査）。  
このリポジトリは、J-Quants API などから市場データを取得して DuckDB に蓄積し、ファクター計算・特徴量整形・シグナル生成を行い、発注・監査用のスキーマを備えた設計になっています。

主な設計方針（要点）
- ルックアヘッドバイアス防止 — target_date 時点のデータのみで処理
- 冪等性 — DB への保存は ON CONFLICT / トランザクションで安全
- テストしやすさ — 認証トークンの注入や自動 .env ロード抑止機構あり
- 外部依存を最小化 — pandas 等に依存せず標準ライブラリ/duckdb 等で実装

---

## 機能一覧

- データ取得・保存（data/jquants_client）
  - J-Quants から株価日足、財務情報、マーケットカレンダーを取得（ページネーション対応）
  - レートリミット・リトライ・トークン自動リフレッシュ対応
  - DuckDB への冪等保存関数（raw_prices / raw_financials / market_calendar など）

- ETL パイプライン（data/pipeline）
  - 差分取得（最終取得日からの再取得＋バックフィル）・保存・品質チェック
  - 日次 ETL エントリ run_daily_etl

- スキーマ定義（data/schema）
  - DuckDB 用の Raw / Processed / Feature / Execution 層テーブルを定義・初期化
  - インデックス、FK（DuckDB の制約を考慮）を含む

- ニュース収集（data/news_collector）
  - RSS 取得・前処理・ID 生成・raw_news・news_symbols への冪等保存
  - SSRF 対策、サイズ制限、XML パースの安全化（defusedxml）

- マーケットカレンダー管理（data/calendar_management）
  - JPX カレンダーの差分更新、営業日 / SQ 判定、次/前営業日の取得等

- 監査ログ（data/audit）
  - signal_events / order_requests / executions 等、発注から約定までの監査テーブルを提供

- 統計ユーティリティ（data/stats）
  - クロスセクションの Z スコア正規化（zscore_normalize）

- リサーチ（research）
  - ファクター計算（momentum / volatility / value）および特徴量探索（forward returns / IC / summary）

- 戦略（strategy）
  - feature_engineering.build_features: 生ファクタ→正規化→features テーブルへの保存
  - signal_generator.generate_signals: features + ai_scores を統合して BUY/SELL シグナルを生成し signals テーブルへ保存

- 発注・実行（execution）および監視（monitoring）
  - パッケージ構成上のモジュールプレースホルダ（必要に応じて実装）

---

## セットアップ手順

前提
- Python 3.9+（型ヒントに基づくが、実行環境の Python バージョンに応じて調整してください）
- DuckDB を利用するためネイティブ拡張が必要（pip でインストール可能）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要なパッケージをインストール
   - 最低限必要な外部パッケージ：
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - 開発用にパッケージ化されていれば editable インストール:
     ```
     pip install -e .
     ```

4. 環境変数の設定
   - 本プロジェクトは環境変数 / .env から設定を読み込みます（自動ロード機能あり）。
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知に使用（必須）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル（必須）
   - 省略時のデフォルトや補助変数:
     - KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live"), デフォルト "development"
     - LOG_LEVEL — ログレベル ("INFO" 等), デフォルト "INFO"
     - KABU_API_BASE_URL — kabu API のベース URL, デフォルト "http://localhost:18080/kabusapi"
     - DUCKDB_PATH — DuckDB ファイルパス, デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH — SQLite（監視用）パス, デフォルト "data/monitoring.db"
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" にすると自動 .env ロードを無効化（テスト用）
   - .env に記載する場合はプロジェクトルート（.git または pyproject.toml のあるディレクトリ）に置いてください。
     - 自動ロードは .env → .env.local の順で読み込み（OS 環境変数優先）

5. DB スキーマ初期化
   - Python REPL やスクリプトから DuckDB を初期化:
     ```python
     from kabusys.data.schema import init_schema, get_connection
     conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ可
     ```

---

## 使い方（代表的な操作例）

- 日次 ETL（市場カレンダー / 株価 / 財務 を取得し品質チェックまで実施）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量ビルド（build_features）
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2025, 1, 15))
  print(f"features upserted: {n}")
  ```

- シグナル生成（generate_signals）
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025, 1, 15))
  print(f"signals generated: {total}")
  ```

- ニュース収集ジョブ実行
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(results)
  ```

- カレンダー更新バッチ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

備考
- jquants_client の fetch_* 関数は id_token を引数で注入可能（テスト時にモックする際に便利）。
- run_daily_etl は品質チェックモジュール quality を呼び出すため、品質チェック実装が必要（存在しない場合は例外となる可能性あり）。

---

## ディレクトリ構成

（src/kabusys 配下の主要ファイルと説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings オブジェクト（settings）を提供
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント、fetch/save 系関数
    - schema.py — DuckDB スキーマ定義・init_schema / get_connection
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - news_collector.py — RSS 収集・前処理・DB 保存
    - calendar_management.py — カレンダー更新・営業日ロジック
    - features.py — zscore_normalize の再エクスポート
    - stats.py — zscore_normalize 実装（共通統計ユーティリティ）
    - audit.py — 発注〜約定の監査ログスキーマ定義
    - quality.py (?) — 品質チェックモジュール（pipeline から参照、存在が期待される）
  - research/
    - __init__.py
    - factor_research.py — momentum / volatility / value 等のファクター計算
    - feature_exploration.py — forward returns, IC, summary, rank
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features: ファクター正規化 → features テーブル
    - signal_generator.py — generate_signals: final_score 計算 → signals テーブル
  - execution/
    - __init__.py
    - （発注 API 連携・注文キュー管理等はここで実装）
  - monitoring/
    - __init__.py
    - （監視・アラート・Slack 通知等の実装を想定）

注: 上記は主要ファイルのみ抜粋。詳細はソースコードを参照してください。

---

## 注意事項・運用上のヒント

- 環境変数の自動ロードは config.py により .env/.env.local をプロジェクトルートから探索して行われます。テスト時や特殊な環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効にできます。
- DuckDB のファイルパスは既定で data/kabusys.duckdb。コンテナ運用やバックアップを考慮して適切な永続ボリュームに配置してください。
- J-Quants の API レート制限（120 req/min）やリトライ/429 の Retry-After を尊重する実装になっています。ただし大量の銘柄を一度にバックフィルする際は時間がかかります。
- ニュース収集は外部 RSS を使うため SSRF / XML攻撃 / 大量レスポンス等への防御（実装済）も考慮されていますが、運用時に許可する RSS ドメインを限定する運用が安全です。
- signals → 発注 → executions のフローは監査テーブルで追跡可能ですが、実際のブローカー連携実装（execution 層）は別途必要です。

---

この README はコードベースの現状実装に基づいて作成しました。追加で「README に入れてほしい実例スクリプト」「運用手順（cron / k8s ジョブ化）」「CI 用テスト実行方法」などがあれば追記します。