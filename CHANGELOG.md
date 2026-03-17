CHANGELOG
=========

すべての重要な変更点は Keep a Changelog（https://keepachangelog.com/）準拠で記載しています。  
バージョン番号はパッケージ内の __version__ に準拠しています。

Unreleased
----------
（なし）

0.1.0 - 2026-03-17
-----------------

Added
- 初回公開リリース。日本株自動売買プラットフォーム「KabuSys」のコア基盤を実装。
- パッケージ構成を追加
  - kabusys: パッケージ公開点（__init__.py、__version__ = "0.1.0"）
  - サブパッケージの雛形: data, strategy, execution, monitoring（strategy/execution/monitoring は現状で空の __init__）
- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env / .env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して決定）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）
  - .env パーサ（引用符、export プレフィックス、インラインコメント処理等に対応）
  - OS 環境変数保護（.env.local による上書き制御）
  - Settings クラスを通じた型付きアクセス（J-Quants、kabu API、Slack、DBパス、環境モード、ログレベル 等）
  - 環境値検証（KABUSYS_ENV / LOG_LEVEL の有効値チェック）、is_live / is_paper / is_dev ヘルパー
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - /token/auth_refresh による id_token 取得（get_id_token）
  - 日足（fetch_daily_quotes）、財務（fetch_financial_statements）、市場カレンダー（fetch_market_calendar）の取得機能（ページネーション対応）
  - レート制御（固定間隔スロットリング）を実装（デフォルト 120 req/min）
  - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx をリトライ対象）
  - 401 受信時はトークン自動リフレッシュして 1 回リトライ
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE により冪等性を確保
  - データの fetched_at に UTC タイムスタンプを記録（Look-ahead bias 対策用）
  - 値変換ユーティリティ（_to_float, _to_int）で堅牢なパース
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード取得（fetch_rss）と raw_news への保存（save_raw_news）、および銘柄紐付け（save_news_symbols, _save_news_symbols_bulk）
  - セキュア設計: defusedxml を用いた XML パース、SSRF 対策（スキーム検証、リダイレクト時のホスト検査、プライベート IP 拒否）、受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）
  - gzip 圧縮のサポートと Gzip-bomb 対策（解凍後サイズチェック）
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と SHA-256（先頭32文字）による記事ID生成（冪等性）
  - テキスト前処理（URL 除去、空白正規化）
  - 銘柄コード抽出（4桁数字、既知銘柄リストによるフィルタ）
  - バルク挿入のチャンク処理とトランザクション化、INSERT ... RETURNING による正確な挿入件数取得
  - デフォルトRSSソース（Yahoo Finance のビジネスカテゴリ）
  - 統合ジョブ run_news_collection により、複数ソースの収集とエラーハンドリングを個別に実施
- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層にわたるテーブル定義を網羅的に実装
    - 例: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など
  - 制約（CHECK / PRIMARY KEY / FOREIGN KEY）とインデックス（頻出クエリ向け）を定義
  - init_schema(db_path) による初期化（親ディレクトリ自動作成、冪等的にテーブル作成）
  - get_connection(db_path) による既存 DB への接続
- ETL パイプラインの骨組み（src/kabusys/data/pipeline.py）
  - ETLResult dataclass により ETL の集計結果・品質問題・エラーを構造化
  - 差分更新ヘルパー（最終取得日の取得、営業日調整 _adjust_to_trading_day）
  - run_prices_etl の差分更新ロジック（最終取得日からの backfill を考慮して date_from を算出、fetch と保存の呼び出し）
  - 市場カレンダーの先読み設定、デフォルトバックフィル日数等の定数化
  - テスト容易性を考慮し id_token の注入を許容

Security
- ニュース収集での SSRF 対策（スキーム検証、プライベートアドレスの検出、リダイレクト時検査）
- defusedxml を用いた安全な XML パース（XML Bomb 対応）
- HTTP レスポンスサイズ上限と Gzip 解凍後のサイズ検査による DoS 保護
- .env 読み込みで OS 環境変数の不意な上書きを防ぐ保護機構

Performance & Reliability
- API クライアントにレートリミッタと再試行（指数バックオフ）を実装し、J-Quants レート制限を尊重
- DuckDB 向けのバルクインサート（チャンク分割）とトランザクション管理で IO/オーバーヘッドを低減
- 保存処理は可能な限り冪等（ON CONFLICT）にして多重実行に耐える設計

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Removed
- N/A（初回リリース）

Deprecated
- N/A（初回リリース）

Notes / Known issues
- src/kabusys/data/pipeline.py の run_prices_etl の末尾の戻り値が不完全（コード断片のため、タプルの 2 番目が欠けているように見える）。実装完了（prices_saved を返す等）が必要。
- strategy / execution / monitoring サブパッケージは現状で実装がほとんど無く、上位ロジック（シグナル生成、発注処理、監視）は今後の追加が想定される。
- 単体テスト、統合テスト、および外部 API 呼び出しのモックに関するテストスイートは提供されていない（テストヘルパーを今後追加予定）。

開発上の備考
- 設定は Settings クラス経由で取得することを想定（直接 os.environ を参照しないこと推奨）
- DuckDB スキーマは init_schema() をプロジェクト初期化時に一度だけ呼ぶ設計。既存 DB には get_connection() を利用する。
- ニュース収集での外部依存（DNS 解決、外部 RSS）はランタイム環境でのネットワークポリシーに依存するため、運用時はプロキシ/ネットワーク設定に注意。

作者
- KabuSys コアチーム（コードベースから推測した初期実装内容を基に記載）

（この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のリリースノートを生成する際はコミット履歴やリリースノート原稿に基づいて調整してください。）