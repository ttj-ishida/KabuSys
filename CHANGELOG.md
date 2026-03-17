# Changelog

すべての注目すべき変更履歴をここに記録します。本ファイルは「Keep a Changelog」規約に準拠します。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買システム「KabuSys」のコアライブラリを収録します。主要な追加点は以下の通りです。

### 追加 (Added)

- パッケージ基盤
  - パッケージのメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 設定管理 (kabusys.config)
  - 環境変数 / .env ファイル読み込みを提供する Settings クラスを追加。
  - .env 自動読み込み機能（プロジェクトルートを .git / pyproject.toml で検出）。
  - 自動読み込み無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーは以下に対応：
    - export KEY=VAL 形式
    - シングル/ダブルクォート、バックスラッシュエスケープ
    - インラインコメントの扱い（クォート有無に応じた解釈）
  - 必須環境変数の取得ヘルパー (_require) と、DuckDB/SQLite パス、ログレベル、環境種別（development/paper_trading/live）チェックを実装。
  - Settings インスタンスを settings として公開。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - J-Quants からのデータ取得（株価日足、財務データ、マーケットカレンダー）を行う fetch_* 関数を追加。
  - ページネーション対応（pagination_key を用いたループ取得）。
  - レート制御：120 req/min を守る固定間隔スロットリング _RateLimiter を実装。
  - リトライ戦略：指数バックオフ（最大 3 回）、対象ステータス (408, 429, 5xx) をリトライ。
  - 401 Unauthorized を検出した場合の自動トークンリフレッシュ（1 回のみリトライ）を実装。
  - get_id_token によるリフレッシュトークンからの id_token 取得（POST）。
  - DuckDB へ冪等保存を行う save_* 関数を追加（ON CONFLICT DO UPDATE を使用）：
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ保存時に fetched_at を UTC ISO8601 で付与し、Look-ahead Bias のトレースを可能に。
  - 数値変換ユーティリティ (_to_float, _to_int) を実装し、空値・不正値に対して安全に None を返す。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからのニュース取得、前処理、DuckDB への保存ワークフローを実装。
  - デフォルト RSS ソースに Yahoo Finance のカテゴリRSS を追加。
  - セキュリティ対策：
    - defusedxml を使った安全な XML パース（XML Bomb 等への防御）。
    - SSRF 対策としてリダイレクト時にスキーム検査・プライベートアドレス検査を行う _SSRFBlockRedirectHandler と _is_private_host を実装。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10 MB) と gzip 解凍後の検査（Gzip bomb 対策）。
  - URL 正規化と記事ID生成：
    - トラッキングパラメータ（utm_*, fbclid, gclid 等）を除去してクエリソートする _normalize_url。
    - 正規化 URL から SHA-256 の先頭32文字を記事 ID とする _make_article_id により冪等性を担保。
  - テキスト前処理（URL除去、空白正規化）と pubDate の安全なパースを実装。
  - DB 保存ロジック：
    - save_raw_news: INSERT ... RETURNING id を使って新規挿入IDを正確に取得（チャンク＆トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING、INSERT ... RETURNING を利用）。
  - 銘柄コード抽出ユーティリティ extract_stock_codes を追加（4桁数字パターン + known_codes フィルタリング）。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の 3 層＋実行層に対応したテーブル定義を追加。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw レイヤーテーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed レイヤーテーブルを定義。
  - features, ai_scores 等の Feature レイヤーテーブルを定義。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution レイヤーテーブルを定義。
  - 典型的なクエリ向けのインデックスを複数定義。
  - init_schema(db_path) によりディレクトリ作成を含めたスキーマ初期化（冪等）を実装。
  - get_connection(db_path) で既存 DB への接続を返すユーティリティを提供。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分取得・保存のための ETL 基盤を実装。
  - ETLResult dataclass を導入し、実行結果・品質問題・エラーを集約。
  - 差分更新ヘルパー（最終取得日の検出 get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - 営業日調整ヘルパー _adjust_to_trading_day（market_calendar に基づく調整）。
  - run_prices_etl: 最終取得日を元に差分または初回全件を取得し、jquants_client 経由で保存する処理（backfill_days による後出し修正吸収）。

### セキュリティ (Security)

- RSS取得処理における SSRF 対策を強化：
  - リダイレクト先でのスキーム検証・ホストのプライベートアドレス判定を行い、内部ネットワークへのアクセスを拒否。
  - URL スキームの厳密チェック（http/https のみ）。
  - XML パースに defusedxml を採用して XML による攻撃を緩和。
  - レスポンスサイズ上限と Gzip 解凍後の検査によりメモリ DoS を防止。

### その他

- テストしやすさの配慮：
  - jquants_client のリクエストで id_token を注入可能（テストでのトークン差し替えを容易に）。
  - news_collector の _urlopen をモック可能な実装にして外部呼出しを差し替えられる設計。
- ロギングを随所に追加し、処理状況・警告・失敗原因を追跡可能に。

### 既知の制限・注意点 (Known issues / Notes)

- ETL の品質チェックモジュール quality の実装（参照）は存在する前提で処理が組まれています。品質チェックロジックの詳細は別途実装が必要です（本リリースでは pipeline 側からの呼び出しインフラを用意）。
- 初期リリースでは strategy, execution, monitoring のサブパッケージはプレースホルダ（__init__.py のみ）で、戦略実装や実行ロジックは今後追加予定です。
- SQLite 用のモニタリングDB など一部外部連携は環境変数設定が必要（.env.example を参照して .env を作成してください）。環境変数未設定時は Settings._require により ValueError が発生します。

-----

このCHANGELOGはコードベースの実装内容から推測して作成しています。実際のリリースノートとして公開する際は、リリース担当者による確認・修正を推奨します。