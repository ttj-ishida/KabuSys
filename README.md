# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ/ライブラリ層）

このリポジトリは、データ取得・永続化・品質管理・監査ログなど、戦略や発注エンジンの基盤となるモジュール群を提供します。
主に以下をサポートします：
- J-Quants API からの市場データ取得（OHLCV / 財務 / マーケットカレンダー）
- DuckDB を用いたスキーマ定義・永続化（Raw／Processed／Feature／Execution 層）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 環境設定の集中管理（.env 自動ロード、必須環境変数チェック）

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 要件
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数
- ディレクトリ構成

---

プロジェクト概要
- KabuSys はデータプラットフォーム部分を中心に設計された Python パッケージです。  
  データ収集（J-Quants）、DuckDB によるスキーマ管理、監査ログの整備、品質チェックなどを提供し、戦略層や実行層と連携して自動売買システムを安定して運用するための基盤を担います。

---

機能一覧
- 環境設定管理
  - プロジェクトルート（.git または pyproject.toml）を自動検出して .env/.env.local を読み込む（必要に応じて無効化可能）。
  - 必須の環境変数は Settings 経由で取得し、未設定時はエラーを投げる。
- J-Quants API クライアント（data/jquants_client.py）
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーをページネーション対応で取得。
  - API レート制御（120 req/min 固定間隔スロットリング）。
  - リトライ（指数バックオフ、最大 3 回）。401 の場合は自動トークンリフレッシュを 1 回試行。
  - DuckDB への保存用ユーティリティ（冪等 INSERT: ON CONFLICT DO UPDATE）。
- DuckDB スキーマ（data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル定義を提供。
  - init_schema() でデータベースを初期化（冪等）。
  - get_connection() で接続取得（初回は init_schema を推奨）。
- 監査ログ（data/audit.py）
  - signal_events / order_requests / executions の監査テーブルを定義・初期化。
  - 監査トレースのためのインデックス定義と UTC タイムゾーン設定。
- データ品質チェック（data/quality.py）
  - 欠損検出（OHLC 欠損）
  - 重複チェック（主キー重複）
  - スパイク検出（前日比 ±X% 以上）
  - 日付不整合（未来日付・非営業日のデータ）
  - run_all_checks() で一括実行し、QualityIssue のリストを返す。

---

要件
- Python 3.10 以上（| 型ヒントを使用）
- 外部パッケージ:
  - duckdb

（その他のコードで使用している標準ライブラリ: urllib, json, logging, pathlib, typing など）

---

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン／ワークツリーに移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate
3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb
   （プロジェクトに pyproject.toml や requirements.txt があればそれに従ってください）
4. 環境変数を設定
   - プロジェクトルートに .env を置くか、OS 環境変数で設定します（下記「環境変数」を参照）。
   - 自動 .env ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1  (Windows の PowerShell の場合は $env:KABUSYS_DISABLE_AUTO_ENV_LOAD = "1")
5. DuckDB スキーマ初期化（サンプル）
   - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

---

使い方（主要 API の例）

1) DuckDB スキーマ初期化
- Python REPL やスクリプトで:
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

  init_schema は親ディレクトリを自動作成し、全テーブルとインデックスを作成します。":memory:" を使うとインメモリ DB。

2) J-Quants から株価を取得して保存する（簡易例）
- 事前に JQUANTS_REFRESH_TOKEN を環境変数へ設定しておくこと。
- 例:
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
  - records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
  - save_daily_quotes(conn, records)

  fetch_* 関数はページネーション対応、内部でトークンの自動リフレッシュやレート制御、リトライ処理を行います。

3) 監査スキーマの初期化
- 既存の DuckDB 接続へ監査テーブルを追加する:
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn)

- 単独の監査 DB を初期化する場合は init_audit_db("data/audit.duckdb") を使用。

4) データ品質チェック
- from kabusys.data.quality import run_all_checks
- issues = run_all_checks(conn, target_date=None)
- 返り値は QualityIssue オブジェクトのリスト（severity によって処理を分岐可能）

QualityIssue の例:
- check_name: "missing_data", "spike", "duplicates", "future_date", "non_trading_day"
- severity: "error" または "warning"
- rows: 問題のサンプルレコード（最大 10 件）

---

環境変数（主要）
- JQUANTS_REFRESH_TOKEN (必須)  
  - J-Quants のリフレッシュトークン。get_id_token() により idToken を得るために使用されます。
- KABU_API_PASSWORD (必須)  
  - kabuステーション API のパスワード（将来の発注モジュールで使用想定）。
- KABU_API_BASE_URL (任意)  
  - デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須)  
  - Slack 通知用トークン（将来の監視用）。
- SLACK_CHANNEL_ID (必須)  
  - Slack 通知先チャンネル ID。
- DUCKDB_PATH (任意)  
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意)  
  - デフォルト: data/monitoring.db
- KABUSYS_ENV (任意)  
  - 有効値: development, paper_trading, live（デフォルト: development）
- LOG_LEVEL (任意)  
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意)  
  - 値を 1 にすると .env 自動ロードを無効化

.env の例（プロジェクトルートに置く）
- JQUANTS_REFRESH_TOKEN=xxxx
- KABU_API_PASSWORD=yyyy
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C12345678
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

---

設計上の注意点 / 実装メモ
- J-Quants クライアントは 120 req/min のレート制限を厳守するため固定間隔スロットリングを採用しています。短時間に多数のリクエストを投げる用途では注意してください。
- API 呼び出しは指数バックオフのリトライを行い、401 発生時はリフレッシュトークンから id_token を自動取得して再試行します（ただし無限再帰回避のため制御あり）。
- DuckDB のテーブル作成は冪等になっています。init_schema は既存テーブルを上書きせずにスキーマを整備します。
- 監査ログは削除しない前提で設計されており、ON DELETE RESTRICT などデータ保全を優先しています。
- データ品質チェックは Fail-Fast ではなく全てのチェック結果を収集して返す方針です。呼び出し元が severity に応じて処理を決定してください。
- すべての TIMESTAMP は UTC で保存する設計想定（監査スキーマ初期化時に TimeZone='UTC' をセットします）。

---

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                       - 環境変数 / Settings 管理
    - data/
      - __init__.py
      - jquants_client.py             - J-Quants API クライアント + DuckDB 保存関数
      - schema.py                     - DuckDB スキーマ定義と初期化
      - audit.py                      - 監査ログ（signal/order/execution）定義
      - quality.py                    - データ品質チェック
    - strategy/
      - __init__.py                    - 戦略モジュールのエントリ（未実装プレースホルダ）
    - execution/
      - __init__.py                    - 発注・約定関連（未実装プレースホルダ）
    - monitoring/
      - __init__.py                    - 監視用エンドポイント（未実装プレースホルダ）

---

今後の拡張ポイント（例）
- kabu ステーション / 証券会社向け発注ラッパーの実装（execution 層）
- 戦略定義・シグナル生成フレームワークの追加（strategy 層）
- Slack/監視アラート連携の実装（monitoring）
- CI 上での品質チェック自動実行・アラート出力パイプラインの整備

---

サポート / 貢献
- バグ修正やドキュメント改善、機能追加のプルリクエストを歓迎します。
- 重要環境変数（トークン等）は公開リポジトリに含めないでください。

以上。必要であれば README にセルフテスト用スクリプトや具体的なユースケース（バッチ ETL スクリプト例、戦略の流れ図など）を追加します。追加希望があれば教えてください。