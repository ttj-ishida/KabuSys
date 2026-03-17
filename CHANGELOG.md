Keep a Changelog 準拠の CHANGELOG.md（日本語）
※この変更履歴は提示されたコードベースから推測して作成しています。

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ初期リリース。基本モジュールを追加。
  - src/kabusys/__init__.py にパッケージメタ情報（__version__ = "0.1.0"）を追加。
- 環境設定管理
  - src/kabusys/config.py: .env / 環境変数の自動ロード機能を追加。
    - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - export 付きの行、シングル/ダブルクォート、エスケープ、インラインコメントなどを考慮した .env パーサ実装。
    - OS 環境変数を保護するための protected 上書きロジック（.env.local の override）を実装。
    - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス / 環境・ログレベル等の設定プロパティとバリデーションを実装。
- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py:
    - 日足（OHLCV）、財務データ、マーケットカレンダーの取得関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を追加。ページネーション対応。
    - get_id_token によるリフレッシュトークン → IDトークン取得（POST）。
    - レート制御（固定間隔スロットリング _RateLimiter）で API レート制限（120 req/min）を順守。
    - 再試行（指数バックオフ、最大 3 回）、HTTP 408/429/5xx に対するリトライ、429 時の Retry-After 優先処理を実装。
    - 401 受信時にトークン自動リフレッシュして 1 回リトライするロジックを実装（無限再帰回避）。
    - DuckDB へ冪等保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE による重複排除。
    - fetched_at を UTC で記録してデータ取得時点をトレース可能に（Look-ahead bias 対策）。
    - 型変換ユーティリティ（_to_float, _to_int）を実装して不正値耐性を確保。
- ニュース収集モジュール
  - src/kabusys/data/news_collector.py:
    - RSS フィード取得（fetch_rss）と記事保存（save_raw_news）/銘柄紐付け（save_news_symbols, _save_news_symbols_bulk）を実装。
    - トラッキングパラメータ（utm_* 等）除去およびクエリソートによる URL 正規化 (_normalize_url) と、正規化 URL からの SHA-256 ベース記事ID生成（先頭32文字）。
    - defusedxml を利用した安全な XML パース、防御的なエラーハンドリング。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキームとプライベートアドレスを検査する _SSRFBlockRedirectHandler。
      - ホストがプライベート/ループバック等かを判定する _is_private_host（IP と DNS 解決で判定）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズチェック（Gzip bomb 対策）。
    - コンテンツ前処理（URL 除去・空白正規化）と pubDate を UTC に正規化するロジック。
    - 銘柄コード抽出（4桁数字）と既知銘柄セットによるフィルタ（extract_stock_codes）。
    - 大量挿入向けにチャンク分割とトランザクション管理、INSERT ... RETURNING を使用して実際に挿入された件数を正確に返す。
    - デフォルト RSS ソース定義（Yahoo Finance のビジネスカテゴリ等）。
- DuckDB スキーマ管理
  - src/kabusys/data/schema.py:
    - Raw / Processed / Feature / Execution 層を備えた包括的なテーブル定義を追加（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
    - 各テーブルに制約（PRIMARY KEY, CHECK 等）を付与してデータ整合性を確保。
    - 頻出クエリ用のインデックスを定義。
    - init_schema(db_path) によりディレクトリ作成→全DDL・インデックスを実行して接続を返す。get_connection() も提供。
- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py:
    - 差分更新・バックフィル機能を備えた ETL 実行ロジックの骨組み（run_prices_etl 等の実装開始）。
    - 差分計算ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）を追加。
    - 市場カレンダーに基づく営業日調整ヘルパー（_adjust_to_trading_day）。
    - ETLResult データクラスによる結果集約（品質チェック結果やエラー一覧を含む）。
    - デフォルトのバックフィル日数（3日）やカレンダー先読み日数等の定数を導入。
    - quality モジュールとの連携フック（品質チェックの取り込みを想定）。
- パッケージ構成
  - src/kabusys/data, src/kabusys/strategy, src/kabusys/execution の初期モジュールを追加（strategy と execution はプレースホルダで構成の土台を提供）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ニュース収集でのセキュリティ強化:
  - defusedxml による XML パース、防御的な XML パース失敗のハンドリング。
  - SSRF 対策（スキーム検証、プライベートアドレス判定、リダイレクト時検査）。
  - レスポンスサイズ制限と gzip 解凍後のサイズ検査によりメモリ DoS / Zip bomb を軽減。
- jquants_client の HTTP リトライ/バックオフや token refresh により不正な状態での無限ループを回避する設計。

Notes / Known limitations
- pipeline モジュールは品質チェックフレームワーク（quality）に依存する設計になっているが、品質チェックの実装はこのコード断片からは完全に確認できないため、フックとして提供。
- strategy / execution パッケージは骨格のみ（詳細な戦略ロジック・発注実装は別途実装が必要）。
- 一部のユーティリティ（例: テスト用の _urlopen モックポイント）や詳細実装はテストコードでの差し替えを想定。

ライセンスや貢献方法、リリースポリシー等はリポジトリのドキュメントに従ってください。