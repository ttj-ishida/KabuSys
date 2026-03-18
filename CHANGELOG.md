CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

[unreleased]: https://example.com/kabusys/compare/v0.1.0...HEAD

v0.1.0 - 2026-03-18
-------------------

Added
- 初期リリース: KabuSys — 日本株自動売買システムのベース実装を追加。
  - パッケージ構成:
    - kabusys (トップレベルパッケージ)
    - サブパッケージ: data, strategy, execution, monitoring（エントリのみ含む）
  - バージョン: 0.1.0（src/kabusys/__init__.py の __version__）

- 環境設定/ロード機能（src/kabusys/config.py）
  - .env / .env.local ファイルおよび環境変数から設定を読み込む自動ローダー実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）により CWD 非依存でロード。
  - .env のパース実装:
    - コメント行 / 空行無視、export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い。
    - コメント判定のためのスペース/タブ考慮。
  - 上書き制御機能:
    - .env.local が .env より優先。
    - OS 環境変数を保護する protected セットを使った上書き制御。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト向け）。
  - Settings クラス:
    - J-Quants / kabu / Slack / DB パスなどの設定プロパティ（必須項目は未設定時に ValueError を送出）。
    - KABUSYS_ENV（development/paper_trading/live）の検証、LOG_LEVEL の検証、ユーティリティプロパティ（is_live, is_paper, is_dev）。

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API クライアント実装（価格日足・財務データ・カレンダー取得）。
  - レート制限制御: 固定間隔スロットリングで 120 req/min に対応（_RateLimiter）。
  - 再試行ロジック: 指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象。
  - トークン自動リフレッシュ: 401 受信時にリフレッシュして 1 回のみ再試行（無限再帰防止）。
  - ページネーション対応: pagination_key によるループ取得。
  - DuckDB への保存関数:
    - save_daily_quotes / save_financial_statements / save_market_calendar：ON CONFLICT DO UPDATE による冪等保存。
    - fetched_at を UTC ISO8601 (Z) で記録し、データ取得時刻を記録（Look-ahead Bias 対策）。
  - 型変換ユーティリティ: _to_float/_to_int（空文字や不正値を None に変換、int 変換時の小数切捨て回避）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集と DuckDB への堅牢な保存処理を実装。
  - 主要機能:
    - RSS 取得（gzip 対応）、XML パース（defusedxml を利用）、記事前処理（URL 除去・空白正規化）。
    - 記事ID は URL 正規化後の SHA-256 の先頭 32 文字で生成し冪等性を担保（UTM 等トラッキングパラメータ削除、クエリソート、フラグメント除去）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキーム・ホストを検証するカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）。
      - ホスト名の DNS 解決→IP 評価や直接 IP 解析によるプライベートアドレス判定。
    - リソース保護:
      - 受信バイト数上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS / Gzip Bomb 対策。
    - DB 保存:
      - save_raw_news: チャンク挿入、INSERT ... ON CONFLICT DO NOTHING RETURNING id で実際に挿入された記事IDを返す。トランザクションでまとめて処理。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを重複排除してチャンク単位で保存。INSERT ... RETURNING を利用して挿入数を正確に返却。
    - 銘柄コード抽出:
      - extract_stock_codes: 正規表現で 4 桁の候補を抽出し、known_codes に基づいてフィルタ、順序保持で重複除去。
    - run_news_collection: 複数 RSS ソースからの収集を統括。ソースごとに失敗を分離して継続。新規挿入記事に対して銘柄紐付けを一括で保存。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層を含む豊富なテーブル定義を追加。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型チェック／制約（CHECK、PRIMARY KEY、FOREIGN KEY）を設定。
  - インデックス定義（頻出クエリ向け）を追加。
  - init_schema(db_path): DB ファイル親ディレクトリの自動作成、全 DDL 実行、インデックス作成（冪等）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL 設計のベース実装:
    - 差分更新ロジック（最終取得日を参照して未取得分のみ取得）と backfill_days による後出し修正吸収方針。
    - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS）。
    - ETL 実行結果を表す ETLResult dataclass（品質問題 list やエラー list を含む）。
    - テーブル存在チェックと最大日付取得ユーティリティ。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date。
    - run_prices_etl: 差分取得→jquants_client による取得→保存、ログ出力を実装（差分計算、backfill を考慮）。

Changed
- N/A（初回リリースのため既存変更点はなし）。

Fixed
- N/A（初回リリース）。

Security
- 複数箇所でセキュリティ対策を実装:
  - RSS パーサで defusedxml を使用して XML ベースの攻撃を軽減。
  - RSS フェッチで SSRF 対策（スキーム検証、プライベートIPのブロック、リダイレクト前検査）。
  - ネットワーク呼び出しでタイムアウトと最大受信サイズチェックを行い資源枯渇攻撃を軽減。
  - 環境変数ロードで OS 環境変数の保護（protected セット）を提供。

Notes / Known issues
- run_prices_etl は差分取得～保存の主要処理を実装していますが、ファイル末尾の処理が途中で終わっている可能性があります（返却タプル等の実装確認を推奨）。本番導入前に ETL の統合テストを強く推奨します。
- strategy / execution / monitoring サブパッケージはエントリのみで、戦略ロジックや発注実行、監視の実装は別途追加が必要です。
- J-Quants / kabu / Slack の各機能は設定（環境変数）に依存します。README/.env.example を用意して設定方法を明記することを推奨します。

Migration
- 既存データがない初期導入向けのリリースです。データベースは init_schema() で初期化してください。既存 DuckDB を使用する場合はスキーマ互換性に注意してください（主にカラム名・制約）。

Acknowledgements
- 本実装はデータ取得・保存・前処理・スキーマ設計を中心とした基盤であり、戦略や注文の実行ロジックは今後のリリースで順次追加予定です。