# Changelog

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog のフォーマットに準拠しています。  
フォーマット: https://keepachangelog.com/ja/

## [0.1.0] - 2026-03-15

### 追加 (Added)
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報: src/kabusys/__init__.py にて version=0.1.0、公開モジュール一覧を __all__ に定義。
- 環境設定管理モジュールを追加 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して決定（CWD 非依存）。
  - .env のパース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - 自動読み込みの優先順位: OS 環境変数 ＞ .env.local ＞ .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
  - Settings クラスを提供し、J-Quants トークン、kabu API、Slack、DB パス、動作環境（development/paper_trading/live）、ログレベル等のプロパティを公開。未設定の必須値は _require() によりエラーを発生。
  - env / log_level のバリデーション（許容値セットのチェック）とユーティリティプロパティ（is_live / is_paper / is_dev）を追加。
- J-Quants API クライアントを追加 (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得するフェッチ関数を実装（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
  - API レート制御: 固定間隔スロットリングによる RateLimiter（120 req/min 想定）。
  - リトライ戦略: 指数バックオフ、最大 3 回、HTTP 408/429/5xx やネットワークエラーに対するリトライ。429 の場合は Retry-After ヘッダを尊重。
  - 認証: refresh token から id_token を取得する get_id_token()。401 受信時は id_token を自動リフレッシュして 1 回だけリトライ。
  - ページネーション対応: pagination_key を用いた継続取得と重複検出。
  - データ永続化: DuckDB への保存関数（save_daily_quotes、save_financial_statements、save_market_calendar）を提供。ON CONFLICT DO UPDATE により冪等性を確保。fetch 時刻は UTC で fetched_at に記録（Look-ahead Bias 対策）。
  - データ変換ユーティリティ: _to_float / _to_int（空値・不正値を None にする挙動、int 変換時の小数部チェックなど）。
- DuckDB スキーマ定義と初期化モジュールを追加 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の各レイヤーに対応したテーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - テーブル作成順は外部キー依存を考慮して定義。インデックスも主要クエリパターンに合わせて作成。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成、全 DDL/インデックスを実行して接続を返す。get_connection() で既存 DB へ接続可能。
- 監査ログ（トレーサビリティ）モジュールを追加 (src/kabusys/data/audit.py)
  - signal_events（戦略が生成したシグナルログ）、order_requests（冪等キー付き発注要求）、executions（約定ログ）テーブルを定義。
  - 監査設計原則を反映（UUID 連鎖によるトレース、order_request_id による冪等性、created_at/updated_at、UTC タイムゾーン、FK の ON DELETE RESTRICT 等）。
  - init_audit_schema(conn) により既存の DuckDB 接続に監査テーブルを追加。init_audit_db(db_path) で専用 DB を初期化して返却。
- パッケージ構造準備ファイル追加
  - data、strategy、execution、monitoring パッケージの __init__.py（空のプレースホルダ）を追加。

### 変更 (Changed)
- （初回リリースのため履歴なし）

### 修正 (Fixed)
- （初回リリースのため履歴なし）

### 注記 (Notes)
- すべての TIMESTAMP は設計上 UTC で保存することを明示（監査モジュール、保存関数での fetched_at）。
- DuckDB のスキーマは初期化時に既存テーブルがあればスキップする設計で冪等性を担保。
- ネットワーク/API エラーに対する堅牢性（リトライ、トークン自動リフレッシュ、レート制御）に重点を置いて実装。
- 将来的な拡張点として、strategy / execution / monitoring の具体的実装・テスト・CLI / サービス起動ロジックが想定される。

-------------------------------------
（この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のコミット履歴やリリースノートに基づいて必要に応じて調整してください。）