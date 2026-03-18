CHANGELOG
=========

すべての変更は Keep a Changelog の規約に従って記載しています。
このファイルはパッケージのコードベースから推測して作成された変更履歴です。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連の対策
- Known issues: 既知の問題や注意点

[Unreleased]
-------------

- Known issues:
  - run_prices_etl() が型注釈上は (取得数, 保存数) を返す仕様であるにも関わらず、
    実装では返り値が 1 要素のタプル (fetched_count,) になっている（saved 値を含めていない）。
    - これにより呼び出し側で期待通り saved 値を受け取れない可能性がある。
    - 修正案: return len(records), saved に変更する必要あり。

- TODO / 未実装（コードから推測）:
  - data.pipeline モジュール内で prices 以外の ETL ジョブ（financials, calendar 等）の
    上位統合処理の完遂が未確認。
  - strategy / execution パッケージの __init__.py はプレースホルダのみ。

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージ基盤
  - kabusys パッケージ初期バージョンを追加。パッケージバージョンは __version__ = "0.1.0"。
  - __all__ に data, strategy, execution, monitoring を定義（各サブパッケージのエントリポイント）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートの検出は __file__ を基点に .git または pyproject.toml を探索（CWD 非依存）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを実装:
    - export KEY=val 形式、シングル/ダブルクォート、エスケープ処理、行内コメント処理に対応。
  - Settings クラスを提供:
    - J-Quants / kabu ステーション / Slack / DB パス / 環境（development/paper_trading/live）/
      ログレベル等のプロパティを提供。
    - env と log_level の値検証を実装。
    - デフォルト値（KABUSYS_ENV=development、LOG_LEVEL=INFO 等）を設定。

- J-Quants クライアント（kabusys.data.jquants_client）
  - API クライアントを実装。
    - ベースURL、レート制限（120 req/min）を厳守する固定間隔スロットリング(_RateLimiter)を実装。
    - 冪等性を意識した fetch / save パターン。
    - リクエストの再試行（指数バックオフ）を実装（最大 3 回）。対象ステータス: 408, 429, 5xx。
    - 401 Unauthorized 受信時はリフレッシュトークンから id_token を自動更新して 1 回のみリトライ。
    - id_token のモジュールレベルキャッシュを実装（ページネーション間での共有）。
    - JSON デコードエラー等に対する明確な例外メッセージ。
  - データ取得関数:
    - fetch_daily_quotes (株価日足、ページネーション対応)
    - fetch_financial_statements (四半期財務、ページネーション対応)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB への保存関数（冪等保存を重視）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE を用いた保存。
    - save_financial_statements: raw_financials テーブルへの保存（ON CONFLICT DO UPDATE）。
    - save_market_calendar: market_calendar テーブルへの保存（ON CONFLICT DO UPDATE）。
  - 値変換ユーティリティ:
    - _to_float, _to_int を実装し、空値・異常値を安全に扱う。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからニュースを収集して raw_news に保存する機能を実装。
  - 主な機能・設計上の特徴:
    - デフォルト RSS ソース定義（例: Yahoo Finance のビジネスカテゴリ）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入し、メモリ DoS を緩和。
    - gzip 圧縮レスポンスの自動解凍と Gzip bomb に対するサイズ再チェック。
    - defusedxml を使った XML パース（XML Bomg 等の防御）。
    - SSRF 対策:
      - リダイレクト検査用の _SSRFBlockRedirectHandler（リダイレクト先のスキーム/ホストを検査）。
      - 最終 URL のスキームとホスト（プライベートアドレス判定）を再検証。
      - URL スキームは http/https のみ許可。
      - _is_private_host() により IP/ホスト名をチェック（IP直判定 + DNS解決して A/AAAA を検査）。
    - URL 正規化とトラッキングパラメータ除去（_normalize_url）。記事 ID は正規化後の SHA-256 先頭32文字。
    - テキスト前処理（URL除去、空白正規化）。
    - RSS の pubDate を RFC2822 から UTC naive datetime に安全に変換（失敗時は現在時刻で代替し警告ログ）。
    - DB 保存:
      - save_raw_news: INSERT ... RETURNING id を用いて実際に挿入された記事IDを返す。チャンク単位 (_INSERT_CHUNK_SIZE) で処理、トランザクション管理。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付け挿入（ON CONFLICT DO NOTHING / RETURNING）を実装。
    - 銘柄抽出:
      - 4桁数字を候補とする正規表現による抽出（extract_stock_codes）。known_codes によるフィルタリングと重複排除。

- スキーマ定義（kabusys.data.schema）
  - DuckDB 用のスキーマを DataPlatform.md に基づき実装。3 層（Raw / Processed / Feature）および Execution レイヤを定義。
  - Raw テーブル: raw_prices, raw_financials, raw_news, raw_executions
  - Processed テーブル: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature テーブル: features, ai_scores
  - Execution テーブル: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対する制約（PRIMARY KEY / CHECK / FOREIGN KEY）を定義。
  - 頻出クエリに対する INDEX 定義を多数追加。
  - init_schema(db_path) による初期化関数を提供。既存テーブルはスキップ（冪等）。親ディレクトリの自動作成対応。
  - get_connection(db_path) で既存 DB への接続を提供。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計とユーティリティを実装:
    - 差分更新のための最終取得日取得関数（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - 営業日調整ヘルパー (_adjust_to_trading_day) を実装。
    - ETLResult データクラスを実装し、品質検査結果やエラー集約を保持・辞書化する to_dict() を提供。
    - run_prices_etl の実装（差分算出、backfill_days の適用、fetch および save の呼び出し）。※返り値に関する既知の問題あり（Unreleased / Known issues 参照）。
  - 設計方針:
    - 差分更新のデフォルト単位は営業日 1 日分。
    - backfill_days により過去数日を再取得して API の後出し修正を吸収。
    - 品質チェックは致命的な問題があっても ETL 自体は継続して結果を返す（呼び出し側の判断に委ねる）。

Security
- 複数のセキュリティ対策を実装:
  - defusedxml を使った XML パース（XML 関連攻撃対策）。
  - RSS フェッチに対する SSRF 対策（リダイレクト検査・ホストプライベート判定・スキーム制限）。
  - レスポンスサイズ上限と gzip 解凍後の再チェックによる DoS 緩和。
  - .env パーサにおけるエスケープ処理等の安全な取り扱い。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Notes
- この CHANGELOG はコードベースからの推測に基づいて作成しています。実際のリリースノートや設計文書とは差異があり得ます。
- run_prices_etl の返り値の不整合は重要な問題につながるため、早めの修正を推奨します。
- strategy / execution / monitoring の各サブパッケージは将来的な機能拡張のためのエントリポイントを用意していますが、実装はこれからの模様です。