# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリです。  
データ取得（J-Quants）、DuckDB によるデータ基盤、ファクター計算・特徴量作成、シグナル生成、ニュース収集、監査ログなど、研究〜本番運用に必要な機能群をモジュール化して提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみで計算）
- DuckDB をコア DB として冪等性を意識した保存ロジックを採用
- API 呼び出しはレート制御・リトライ・トークン自動更新など堅牢な実装
- 研究（research）と実運用（strategy / execution）を分離

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（jquants_client）：日足・財務・カレンダーを取得、DuckDB に冪等保存
  - ニュース収集（news_collector）：RSS 取得、前処理、記事保存、銘柄抽出
  - データパイプライン（pipeline）：差分取得、バックフィル、品質チェックの統合ジョブ
  - カレンダー管理（calendar_management）：JPX カレンダーの更新・営業日判定

- データ層（DuckDB スキーマ）
  - schema モジュールで Raw / Processed / Feature / Execution 層のテーブルを初期化

- 研究・特徴量
  - factor_research：モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_engineering：ファクター正規化・ユニバースフィルタ・features テーブルへの書き込み
  - feature_exploration：将来リターン計算、IC（Spearman）や統計サマリ等

- 戦略
  - signal_generator：正規化済みファクター + AI スコアを統合して BUY/SELL シグナルを生成
  - 重み・閾値をパラメータ化、Bear レジームで BUY を抑制、保有ポジションのエグジット判定

- 実行・監査
  - audit：シグナル→発注→約定のトレーサビリティ用テーブル定義（監査ログ）
  - execution（未実装の詳細層あり）：発注フローと連携するためのインタフェース層想定

- 共通ユーティリティ
  - data.stats: Z スコア正規化等の統計ユーティリティ
  - 設定管理（config）：.env 自動ロード、必須環境変数チェック、動作環境判別

---

## 動作環境・前提

- Python 3.10 以上（型注釈で X | Y 記法を使用）
- 主要依存（例）:
  - duckdb
  - defusedxml
- ネットワークアクセスが必要（J-Quants API / RSS ソース）
- DuckDB ファイル保存先ディレクトリへの書き込み権限

（実際の依存は pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージと依存をインストール
   - 開発環境ではプロジェクトルートに pyproject.toml がある想定:
     - python -m pip install -e .
   - または最低限の依存を個別に:
     - python -m pip install duckdb defusedxml

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（ただしテスト時などは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - SLACK_BOT_TOKEN (必須)
     - SLACK_CHANNEL_ID (必須)
   - 任意・デフォルトあり:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB スキーマの初期化
   - Python スクリプト/REPL で:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - ":memory:" を渡すとインメモリ DB になります（テスト向け）。

---

## 使い方（主要なサンプル）

以下は最小の利用例です。実運用では適切なログ・エラーハンドリングやスケジューリング（cron 等）を併用してください。

- DB 初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（市場カレンダー・株価・財務データ取得、品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- カレンダー更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- ニュース収集（RSS 取得 → raw_news 保存 → 銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄リスト（例: {'7203', '6758', ...}）
  stats = run_news_collection(conn, sources=None, known_codes=set(), timeout=30)
  print(stats)
  ```

- ファクター計算・特徴量作成
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  cnt = build_features(conn, target_date=date(2025, 1, 6))
  print("features upserted:", cnt)
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, target_date=date(2025, 1, 6))
  print("signals written:", total)
  ```

- 直接 J-Quants API 呼び出し（トークン取得・データ取得）
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
  token = get_id_token()  # settings.jquants_refresh_token を使用
  recs = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,12,31))
  saved = save_daily_quotes(conn, recs)
  ```

- テスト時のヒント
  - 環境変数の自動ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - DuckDB をインメモリで使用して副作用を避ける: init_schema(":memory:")

---

## 主要ディレクトリ構成

（リポジトリの src ディレクトリ配下を例示）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動ロードと Settings クラス（必須 env 取得）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py — RSS 収集、前処理、保存、銘柄抽出
    - schema.py — DuckDB スキーマ定義・初期化
    - stats.py — Zスコア正規化などの統計ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — カレンダー更新・営業日判定
    - audit.py — 発注・約定の監査ログ用テーブル定義
    - features.py — data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — モメンタム／ボラティリティ／バリュー等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - strategy/
    - __init__.py (build_features, generate_signals を公開)
    - feature_engineering.py — ファクター正規化・ユニバースフィルタ・features アップサート
    - signal_generator.py — final_score 計算と BUY/SELL 判定、signals テーブル書込
  - execution/ (発注・実行層のためのパッケージ領域、実装は拡張想定)
  - monitoring/ (Slack 通知など監視用モジュールが入る想定)

---

## 設定・運用上の注意

- 環境（KABUSYS_ENV）は development / paper_trading / live を想定。live では特に発注ロジックの安全性を厳密に確認してください。
- J-Quants API はレート制限があるため大量リクエスト時は十分に間隔を確保。モジュールは内部で固定間隔スロットリングとリトライを提供します。
- DuckDB のファイルはバックアップ・スナップショットを定期的に行ってください（監査ログ等を保持する場合は容量が増加します）。
- ニュース収集では外部 URL の検証・SSRF 防御・XML の安全なパースを行っていますが、ソース追加時は信頼性を確認してください。
- 実運用で証券会社の API（kabu）と連携する場合、発注/監査の整合性と二重発注防止（冪等キー）を厳格に扱ってください。

---

## 貢献・拡張

- strategy / execution / monitoring 層はプロジェクト固有のロジックに合わせて拡張を想定しています。
- テストの追加、監視/アラート（Slack 経由）やリスク管理ルールの導入を推奨します。

---

必要であれば README にサンプル .env.example、CI 設定、より詳細な API 使用例（パラメータの意味や想定される戻り値の例）を追記します。どの部分をより詳しく書くか指示してください。