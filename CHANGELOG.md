# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のバージョンはパッケージ内の __version__ に合わせて 0.1.0 です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-17

初期リリース。日本株自動売買システム「KabuSys」のコア基盤を実装しました。以下は、このリリースで追加された主要な機能・設計要素・既知の問題点の要約です。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージエントリポイントを定義（__version__ = 0.1.0、公開サブパッケージ指定）。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよびOS環境変数から設定を読み込む自動ローダー（プロジェクトルートを .git / pyproject.toml で探索）。
    - .env/.env.local の読み込み順序、OS 環境変数の保護（protected set）、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化フラグ。
    - 行パーサ（コメント、export 形式、クォート内のエスケープ処理、インラインコメント処理）を実装。
    - Settings クラスを提供（J-Quants トークン、kabu API 設定、Slack トークン・チャンネル、DB パス、環境名/ログレベルの検証、is_live/is_paper/is_dev プロパティ）。

- J-Quants API クライアント（データ取得）
  - src/kabusys/data/jquants_client.py
    - API レート制御（_RateLimiter: 120 req/min 固定間隔スロットリング）。
    - HTTP リクエストユーティリティ（_request）：JSON デコード、タイムアウト、リトライ（指数バックオフ、最大 3 回）、ステータスコード 408/429/5xx の再試行、429 の Retry-After 考慮。
    - トークン処理：ID トークンのキャッシュ共有、401 受信時の自動リフレッシュ（1 回のみ再試行）と get_id_token().
    - ページネーション対応のデータ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への冪等保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用）。
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を防止。
    - 型変換ユーティリティ: _to_float, _to_int（安全な数値変換と不正値処理）。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィード取得と記事保存パイプライン（DEFAULT_RSS_SOURCES をデフォルトとして実装）。
    - セキュリティ対策: defusedxml による XML パース、SSRF 対策（URL スキーム検証、プライベートIP/ループバックの検出、リダイレクト先検査）、受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズ検査。
    - URL 正規化: トラッキングパラメータ除去（utm_ 等）、スキーム/ホスト小文字化、フラグメント除去、クエリソート。
    - 記事ID 生成: 正規化 URL の SHA-256 ハッシュ先頭 32 文字（冪等性確保）。
    - テキスト前処理: URL 除去、空白正規化。
    - RSS -> NewsArticle 抽出（content:encoded 対応、pubDate パース）。
    - DuckDB への保存: save_raw_news（チャンク INSERT、INSERT ... RETURNING により新規挿入 ID を正確に取得）、save_news_symbols、_save_news_symbols_bulk（チャンク処理、トランザクションにまとめて挿入）。
    - 銘柄コード抽出: 4 桁数字パターンによる抽出（known_codes によるフィルタ、重複除去）。
    - run_news_collection: 複数 RSS ソースの一括収集、ソース毎に独立して例外処理（1 ソース失敗でも継続）、新規記事に対する銘柄紐付け処理。

- DuckDB スキーマ定義と初期化
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution 層に分けたスキーマを定義（raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signals, signal_queue, orders, trades, positions, など）。
    - 制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックス（頻出クエリパターン向け）を定義。
    - init_schema(db_path) によりディレクトリ作成→接続→DDL実行して初期化（冪等）。get_connection() を提供。

- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py
    - ETL ワークフローと方針（差分更新、backfill 日数、品質チェックの扱い）を実装。
    - ETLResult dataclass（結果集約、品質問題のシリアライズ）。
    - テーブル存在チェックや最大日付取得ヘルパー（_table_exists, _get_max_date）。
    - 市場カレンダー補正ヘルパー（_adjust_to_trading_day）。
    - 差分取得ヘルパー（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - run_prices_etl: 差分更新ロジック、デフォルト backfill_days = 3、最小データ日付は 2017-01-01、J-Quants から取得して保存する一連の処理を着手。

### Security
- XML 処理に defusedxml を採用して XML-based 攻撃（XML bomb 等）を軽減。
- RSS フェッチ時の SSRF 防止:
  - 非 http/https スキーム拒否。
  - ホストがプライベート/ループバック/リンクローカル/IP マルチキャストかどうかの検査（直接 IP と DNS 解決結果を両方検査）。
  - リダイレクト時にもスキームとホストの検査を実行（_SSRFBlockRedirectHandler）。
- レスポンスサイズ上限（MAX_RESPONSE_BYTES）によりメモリ DoS を軽減。
- 外部からの URL を正規化して不要なトラッキングパラメータを除去。

### Performance / Reliability
- API レート制御（_RateLimiter）でレート違反を回避。
- HTTP リトライ（指数バックオフ、Retry-After 優先）により一時障害に耐性を強化。
- DuckDB 側はバルク/チャンク挿入、トランザクション、INSERT ... RETURNING を活用して実際に追加されたレコード数を正確に把握。
- インデックスやテーブル設計により頻出クエリを想定した高速化を図る。
- モジュールレベルの ID トークンキャッシュでページネーション間のトークン取得オーバーヘッドを削減。

### Testing / Extensibility
- _urlopen は内部でラップしているため、テストでモック差し替えが可能（news_collector のユニットテスト容易化）。
- jquants_client の各関数は id_token を引数注入可能（テストでのスタブ容易化）。
- 環境読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD によりテストで無効化可能。

### Fixed / Known issues
- run_prices_etl の戻り値が未完（実装途中）:
  - 現状コードの最後に `return len(records),` とだけあり、関数シグネチャでは (int, int) を期待しているため戻り値が不正（1 要素のタプル）になります。ETL の最終的な saved 値の返却ロジックが未完です。次版で修正予定です。
- その他: 一部関数のエラーメッセージやログは今後整備する予定（国際化・詳細レベルの統一など）。

### Breaking Changes
- なし（初回リリース）。

---

今後の予定（例）:
- run_prices_etl の戻り値修正・単体テスト追加。
- pipeline の品質チェック（quality モジュール）連携とエラー分類の運用整備。
- execution 層（kabu/station 連携）と monitoring 周りの実装強化。
- ドキュメント（DataPlatform.md, DataSchema.md）に沿った運用ガイドの整備。

(注) 本 CHANGELOG はコードベースから推測して作成しています。実装の詳細や追加の変更点はソース管理のコミットログ・差分を参照してください。