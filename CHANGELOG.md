Keep a Changelog
=================

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

Unreleased
---------

（なし）

0.1.0 - 2026-03-18
-----------------

初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装しました。主にデータ収集・スキーマ・ETL の基盤を提供します。

Added
- パッケージ初期化
  - src/kabusys/__init__.py に基本エクスポートとバージョン (0.1.0) を追加。

- 環境設定・自動 .env ロード
  - src/kabusys/config.py
    - プロジェクトルートを .git / pyproject.toml から探索する _find_project_root を実装。カレントワーキングディレクトリに依存しない自動環境読み込みを実現。
    - .env ファイルの柔軟なパースを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメント処理など）。
    - .env と .env.local の読み込み優先順位（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
    - Settings クラスを導入し、J-Quants / kabu API / Slack / DB パス / 実行環境・ログレベル等のプロパティを提供。KABUSYS_ENV / LOG_LEVEL の検証ロジックを実装。
    - 必須環境変数取得時のエラーメッセージ化（_require）。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - API 呼び出しユーティリティ _request を実装。機能：
      - レート制限制御（_RateLimiter: 120 req/min 固定間隔スロットリング）
      - リトライ（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）
      - 401 受信時はトークン自動リフレッシュ（1 回のみ）
      - JSON デコードエラーハンドリング
    - get_id_token (リフレッシュトークンから idToken 取得) とモジュールレベルの id_token キャッシュ実装。
    - データ取得関数を実装（ページネーション対応）:
      - fetch_daily_quotes（株価日足: OHLCV）
      - fetch_financial_statements（四半期財務データ）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB への保存関数（冪等）を実装:
      - save_daily_quotes / save_financial_statements / save_market_calendar
      - ON CONFLICT DO UPDATE による上書きで冪等性を保証
      - fetched_at に UTC タイムスタンプを記録
    - 型変換ユーティリティ (_to_float / _to_int) を実装（安全に None を返す挙動）。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィード収集フロー（DataPlatform 設計に基づく）を実装。
    - セキュリティ / 頑健性設計:
      - defusedxml を利用した XML パース（XML Bomb 等の防御）。
      - SSRF 対策: リダイレクト検査用ハンドラ _SSRFBlockRedirectHandler、取得前のホスト検証、プライベートアドレス拒否。
      - URL スキーム検証（http/https のみ許可）。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）・gzip 解凍後の再検査。
      - トラッキングパラメータ除去および URL 正規化（_normalize_url）。
      - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を担保。
      - HTML 文中の URL 除去・空白正規化を行う前処理 (preprocess_text)。
      - 銘柄コード抽出ロジック（4桁数字、known_codes フィルタ）。
      - DB 保存: save_raw_news / save_news_symbols / _save_news_symbols_bulk（チャンク分割、トランザクション、INSERT ... RETURNING を使用して実際に挿入された件数を取得）。
    - デフォルト RSS ソースに Yahoo Finance の日本ビジネス RSS を追加（DEFAULT_RSS_SOURCES）。

- DuckDB スキーマ定義と初期化
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution レイヤに対応したテーブル群の DDL を実装。
    - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
    - features, ai_scores 等の Feature テーブル。
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル。
    - 頻用クエリ向けのインデックス定義。
    - init_schema(db_path) によるディレクトリ自動作成とテーブル初期化、get_connection の提供。

- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py
    - ETLResult dataclass を導入（対象日、取得/保存件数、品質問題、エラー等を集約）。
    - 差分更新用ユーティリティ: テーブル存在検査 (_table_exists)、最大日付取得 (_get_max_date)、営業日調整 (_adjust_to_trading_day)。
    - 差分更新ヘルパー: get_last_price_date / get_last_financial_date / get_last_calendar_date。
    - run_prices_etl を実装（差分判定、backfill_days による後出し修正吸収、J-Quants から取得し保存する流れ）。
    - ETL の設計方針（差分更新、バックフィル、品質チェックは非致命扱いで収集継続など）を反映。

- テスト支援 / モック用箇所
  - news_collector._urlopen はテストで差し替え可能（モックしやすい構造）。

Changed
- N/A（初回リリースのため変更履歴はなし）

Fixed
- N/A（初回リリース）

Security
- RSS パーサに defusedxml を採用し XML 攻撃に備え、SSRF 対策（リダイレクト先検査、プライベートホスト判定）・レスポンスサイズ制限を実装。
- .env 読み込みで OS 環境変数を保護する protected 機構を追加（.env.local/.env の override 挙動制御）。

Deprecated
- N/A

Removed
- N/A

注意点 / 既知の問題
- run_prices_etl の末尾の return 文が不完全なように見えます（現在のソースでは (len(records), として 2 番目の値が返されていない／コード断片で終わっている）。実行時に戻り値や例外の問題が発生する可能性があるため、戻り値の整合性を確認・修正してください。
- strategy/execution パッケージはプレースホルダ（__init__.py が存在するのみ）であり、実際の戦略・発注ロジックは未実装です。
- 初期化: データベースを利用する前に schema.init_schema(db_path) を呼び出してテーブルを作成してください。既存 DB に対するマイグレーション機能は本リリースでは未提供です。
- J-Quants の rate limit・認証まわりは実装済みですが、実運用に際してはトークン管理・監視・バックオフ戦略の微調整を推奨します。
- news_collector の既定ソースは限定的（1 ソース）です。運用では sources 辞書を与えて拡張してください。

移行／アップグレードノート
- なし（初回公開）

貢献
- このプロジェクトへの貢献は歓迎します。バグ報告や機能提案、プルリクエストは README に従ってください（ドキュメントは別途整備予定）。