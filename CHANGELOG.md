# CHANGELOG

すべての注目すべき変更はこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠しています。

なお、本ファイルはリポジトリ内のコード内容から推測して作成した初期の変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-16
初回リリース

### Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）
  - 公開モジュール候補: data, strategy, execution, monitoring

- 環境設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を読み込む機能を実装
  - プロジェクトルート探索（.git または pyproject.toml を起点）により cwd に依存しない自動読み込みを実装
  - .env / .env.local の読み込み順位、OS環境変数の保護（protected keys）や override 挙動をサポート
  - export KEY=val 形式やクォート・エスケープ、インラインコメントなどの .env パース処理を実装
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD に対応（テスト時等に利用可能）
  - Settings クラスを提供し、J-Quants トークン、kabu API、Slack、DBパス、環境種別（development/paper_trading/live）、ログレベル等の取得をプロパティで提供
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の妥当性チェック）と必須値未設定時の明確なエラーメッセージを実装

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）
  - データ取得 API: 日次株価（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー を取得する fetch_* 関数群を実装
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）
  - リトライロジック（指数バックオフ, 最大 3 回）および 408/429/5xx に対する再試行
  - 401 受信時はリフレッシュトークンで自動的に id_token を更新して 1 回リトライ（無限再帰防止）
  - ページネーション対応（pagination_key を用いた繰り返し取得）
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を防止する方針を採用
  - DuckDB へ保存する save_* 関数群（save_daily_quotes, save_financial_statements, save_market_calendar）を実装
    - ON CONFLICT DO UPDATE による冪等性を確保（重複挿入を上書き）
    - PK 欠損行のスキップ（ログ出力）
  - 値変換ユーティリティ _to_float / _to_int を実装（耐障害性ある変換ルール）

- DuckDB スキーマ定義と初期化を追加（src/kabusys/data/schema.py）
  - 3層アーキテクチャに基づくテーブル定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY、CHECK）、型、インデックス定義を詳細に作成
  - init_schema(db_path) によりディレクトリ作成→テーブル/インデックス作成（冪等）を実装
  - get_connection(db_path) を提供（既存 DB への接続）

- ETL パイプラインを追加（src/kabusys/data/pipeline.py）
  - 日次 ETL のエントリポイント run_daily_etl を実装
    - 処理順: 市場カレンダー ETL → 株価日足 ETL → 財務データ ETL → 品質チェック
    - 各ステップは独立した例外ハンドリング（1ステップ失敗でも他ステップ継続）
  - 差分更新ロジック（DB の最終取得日から未取得分のみ取得）とデフォルトの backfill（既定: 3 日）を実装
  - カレンダーの先読み（既定: 90 日）による営業日調整実装
  - ETLResult dataclass による実行結果集約（取得・保存数、品質問題、エラー一覧）
  - run_prices_etl / run_financials_etl / run_calendar_etl を個別に提供
  - id_token 注入によりテスト容易性を確保

- 監査（Audit）スキーマと初期化を追加（src/kabusys/data/audit.py）
  - 監査ログ用テーブルを定義: signal_events, order_requests, executions
  - 冪等キー（order_request_id）を利用した発注ログ設計、ステータス遷移モデルを文書化
  - すべての TIMESTAMP を UTC で保存するため init_audit_schema で TimeZone を設定
  - init_audit_db(db_path) を提供（監査専用 DB 初期化）
  - インデックス（検索やジョインを想定したもの）を多数定義

- データ品質チェックモジュールを追加（src/kabusys/data/quality.py）
  - QualityIssue dataclass を定義（check_name, table, severity, detail, rows）
  - 実装されたチェック:
    - check_missing_data: raw_prices の open/high/low/close 欠損検出（サンプル行取得、カウント、severity="error"）
    - check_spike: 前日比スパイク検出（LAG ウィンドウ関数を用いた変動率判定、デフォルト閾値 50%）
  - 設計上は重複チェック・日付不整合検出等も想定（ドキュメント化）
  - DuckDB 接続を用いた効率的な SQL 実行、パラメータバインドによる安全性を確保
  - チェックは Fail-Fast ではなく全問題を収集する方針

- ドキュメント的な改善
  - 各モジュールに機能・設計原則・使用例を含む詳細な docstring を追加
  - ログ出力ポイントを設置（info/warning/error）して運用時の可観測性を確保

### Changed
- （初回リリースのためなし）

### Fixed
- DuckDB への挿入処理を冪等化（ON CONFLICT DO UPDATE）することで二重挿入や再取得時の不整合を防止

### Security
- .env の自動ロードは環境変数により無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）
- OS 環境変数は protected として .env による上書きを防止する挙動を実装

### Notes / Usage examples
- DB 初期化例:
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
- 日次 ETL 実行例:
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)
- J-Quants id_token は Settings から自動読み込みされるが、テスト時は id_token を明示注入可能

### Known limitations / TODO
- quality モジュールのドキュメントは重複チェックや日付不整合チェックを設計に含むが、現在の実装サンプルでは主に欠損検出とスパイク検出が実装済み。その他チェックは今後追加予定。
- strategy / execution / monitoring パッケージの具体的実装はスケルトン状態（パッケージ空ディレクトリ）で、今後戦略実装・ブローカ API 連携・監視機能の実装が期待される。

---

（注）この CHANGELOG はリポジトリに含まれるソースコードのコメント・実装から推測して作成しています。実際のリリースノートにはさらに運用上の注意や互換性情報を追記してください。