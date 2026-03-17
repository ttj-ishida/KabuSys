# KabuSys — 日本株自動売買システム

軽量なデータ基盤と ETL / 監査ロジックを備えた日本株向け自動売買コンポーネント群です。  
主に J-Quants API からの市場データ取得、RSS ベースのニュース収集、DuckDB を用いたスキーマ管理・品質チェック、ETL パイプライン、マーケットカレンダー管理、監査ログ（発注〜約定のトレーサビリティ）を提供します。

---

## 主な機能

- 環境設定管理
  - .env/.env.local からの自動読み込み（プロジェクトルート検出）
  - 必須設定の明示的取得（`Settings`）

- J-Quants API クライアント（`kabusys.data.jquants_client`）
  - 日足（OHLCV）、財務データ、JPX マーケットカレンダーの取得
  - レートリミット（120 req/min）遵守、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存 API（ON CONFLICT … DO UPDATE）

- ニュース収集（`kabusys.data.news_collector`）
  - RSS フィード取得／XML パース（defusedxml で脆弱性対策）
  - URL 正規化・トラッキングパラメータ除去、SHA-256 ベースの記事 ID、SSRF 対策、受信サイズ制限
  - DuckDB への冪等保存（INSERT … RETURNING）と銘柄コード抽出/紐付け

- DuckDB スキーマ管理（`kabusys.data.schema`）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス作成、:memory: 対応

- ETL パイプライン（`kabusys.data.pipeline`）
  - 市場カレンダー・日足・財務データの差分取得（バックフィル対応）と保存
  - 品質チェック（欠損・重複・スパイク・日付不整合）との統合
  - 日次 ETL のエントリポイント（`run_daily_etl`）

- マーケットカレンダー管理（`kabusys.data.calendar_management`）
  - 営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - 夜間バッチ更新ジョブ（calendar_update_job）

- 監査ログ（`kabusys.data.audit`）
  - シグナル → 発注要求 → 約定 を UUID 階層でトレースする監査テーブル群と初期化関数
  - 発注の冪等キー管理、UTC タイムゾーン固定

- データ品質チェック（`kabusys.data.quality`）
  - 欠損、重複、スパイク、日付不整合（未来日・非営業日データ）を検出し QualityIssue を返却

---

## 必要条件 / 依存パッケージ

- Python 3.10 以上（型ヒントの union 表記などを使用）
- 依存ライブラリ（例）
  - duckdb
  - defusedxml

（導入方法は次の「セットアップ手順」を参照してください。）

---

## セットアップ手順

1. リポジトリをチェックアウト／クローン

   git clone <リポジトリURL>
   cd <リポジトリ>

2. 仮想環境を作成して有効化（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   pip install -U pip
   pip install duckdb defusedxml

   （将来的に requirements.txt / pyproject.toml があればそちらを利用してください）

4. 環境変数の設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を作成すると、パッケージ読み込み時に自動で読み込まれます。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
   - KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
   - SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV — 環境（development / paper_trading / live、デフォルト: development）
   - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

---

## 使い方（サンプル・コード例）

以下は簡単な対話的使用例です。プロジェクトの Python モジュールを import して使います。

- DuckDB スキーマ初期化（ファイル DB）

  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path を返す

- 日次 ETL を実行（市場データ取得→保存→品質チェック）

  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)
  print(result.to_dict())

- ニュース収集ジョブを実行（RSS から取得 → raw_news 保存 → 銘柄紐付け）

  from kabusys.data.news_collector import run_news_collection
  # known_codes は抽出に使う有効な銘柄コードのセット（例: {'7203','6758',...}）
  results = run_news_collection(conn, known_codes={'7203','6758'})
  print(results)  # {source_name: 新規保存件数}

- カレンダー夜間バッチ更新

  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"saved: {saved}")

- 監査ログテーブル初期化（監査専用 DB）

  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")

- J-Quants の id token を手動で取得（テストやトラブルシュート用）

  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用して取得

ログ出力の設定例（簡易）:

  import logging
  logging.basicConfig(level=settings.log_level)

注意:
- run_daily_etl などは例外を内部で捕捉してエラー一覧を ETLResult に格納します。戻り値の has_errors / has_quality_errors を確認してください。
- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して .env の自動読み込みを無効化できます。

---

## ディレクトリ構成

リポジトリ内の主要ファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義と初期化
    - pipeline.py            — ETL パイプライン（日次 ETL）
    - calendar_management.py — 市場カレンダー管理（営業日判定、更新ジョブ）
    - audit.py               — 監査ログ用テーブルと初期化
    - quality.py             — データ品質チェック
  - execution/
    - __init__.py            — 発注 / 約定 / ブローカー連携は今後実装想定
  - strategy/
    - __init__.py            — 戦略ロジック用プレースホルダ
  - monitoring/
    - __init__.py            — 監視・メトリクス用プレースホルダ

データ保存先の例:
- data/kabusys.duckdb           — メイン DuckDB（デフォルト）
- data/kabusys_audit.duckdb     — 監査ログ用 DuckDB（推奨分離）
- data/monitoring.db            — 監視用 SQLite（設定で指定）

---

## 設定 / 運用上の注意

- 機密情報（J-Quants トークン、kabu API パスワード、Slack トークンなど）は必ず安全に管理し、公開リポジトリにコミットしないでください。`.env.local` を local のみに置く運用が推奨されます。
- J-Quants のレート制限（120 req/min）を超えないように設計済みですが、運用で想定外の呼び出しが発生すると API 制限に達する可能性があるため監視を行ってください。
- DuckDB は単一ファイル DB で軽量ですが、複数プロセスでの同時書き込みには注意が必要です。長時間のトランザクションや並列書き込みは衝突の原因になります。
- XML パースや外部 URL の取得にあたっては SSRF / XXE / Gzip bomb 等の対策を組み込んでいますが、外部ソースの扱いには引き続き注意してください。

---

## 貢献 / 拡張

- strategy や execution パッケージはプレースホルダとして存在します。戦略実装、発注ブリッジ（kabuステーション連携）やモニタリング機能の追加が想定されます。
- プルリクエストやイシューで改善提案を歓迎します。特に次の点の拡張が有益です:
  - 発注実行フローの実装と証券会社 SDK との統合
  - より豊富なログ / メトリクス、監視アラート
  - テストカバレッジ（ユニット・統合テスト）

---

README の内容はこのコードベースの現状に基づいています。追加の使い方・スクリプト（CLI、ジョブスケジューラ連携等）を作成したい場合は、目的に合わせた補助例を提供できます。必要なら教えてください。