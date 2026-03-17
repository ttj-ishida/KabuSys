CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。
安定したリリースはセマンティックバージョニングに従います。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-17
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - 基本パッケージ定義（src/kabusys/__init__.py）
    - __version__ = "0.1.0"
    - パッケージエクスポート: data, strategy, execution, monitoring（空のモジュール枠含む）
- 環境設定モジュール（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの設定読み込み機能を実装
  - 自動ロードのルール: プロジェクトルート（.git または pyproject.toml）を基準に .env -> .env.local を適用
  - .env パーサ実装（コメント、export 形式、クォート・エスケープ対応、インラインコメント処理）
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
  - 必須環境変数取得用の _require()、Settings クラスを提供
  - 設定値のバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック）および便利プロパティ（is_live / is_paper / is_dev）
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日次株価、財務データ、マーケットカレンダー取得のための fetch_* 関数を実装（ページネーション対応）
  - RateLimiter による API レート制御（120 req/min、固定間隔スロットリング）
  - リトライ戦略（指数バックオフ、最大3回）、HTTP 408/429/5xx 対象
  - 401 応答時の自動トークンリフレッシュ（1回のみ）とトークンキャッシュ
  - get_id_token() によるリフレッシュトークンからの ID トークン取得
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）
    - ON CONFLICT DO UPDATE による重複解消
    - fetched_at に取得時刻（UTC）を付与
  - 型安全な変換ユーティリティ（_to_float/_to_int）
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得して raw_news / news_symbols に保存する一連の処理を実装
  - URL 正規化とトラッキングパラメータ除去（_normalize_url）
  - 記事ID の一意化: 正規化 URL の SHA-256（先頭32文字）を使用
  - defusedxml を用いた XML パース（XML Bomb 対策）
  - SSRF 対策:
    - 許可スキームは http/https のみ
    - リダイレクト時にスキームとホスト/IP の事前検証を行う専用ハンドラ（_SSRFBlockRedirectHandler）
    - ホスト名解決時にプライベート/ループバック/リンクローカル/マルチキャストを拒否
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）
  - コンテンツ前処理（URL除去、空白正規化）と pubDate の堅牢なパース（フォールバック時は現在時刻を採用）
  - DB 保存はトランザクションでまとめて実行、INSERT ... RETURNING を利用して実際に挿入された ID を返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）
  - 銘柄コード抽出ユーティリティ（4桁数字の候補から known_codes に基づき抽出）
  - run_news_collection による複数ソースの統合収集ジョブ（各ソースは独立してエラーハンドリング）
- DuckDB スキーマ定義/初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の 3 層（および Execution 層）に対応したテーブル定義を実装
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - カラム制約（CHECK、NOT NULL、PRIMARY KEY、FOREIGN KEY）を設計段階で明示
  - インデックス定義（頻出クエリパターン向け）
  - init_schema(db_path) による自動ディレクトリ作成と冪等なスキーマ初期化、get_connection() を提供
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新ロジック（DB の最終取得日から backfill を考慮して差分取得）
  - run_prices_etl（差分取得→保存のワークフロー）と補助ユーティリティ（get_last_price_date 等）
  - ETL 実行結果を表す ETLResult データクラス（品質チェック結果・エラーを収集して返す）
  - 市場カレンダーに基づく営業日調整ユーティリティ（_adjust_to_trading_day）
  - テスト容易性のため id_token 注入や内部関数の分離を考慮
- その他
  - type hints、ロギングメッセージを全体的に追加して運用/デバッグ性を向上
  - ネットワーク処理や DB 操作での例外ハンドリングを考慮した実装

Security
- XML parsing に defusedxml を使用して XXE / XML Bomb を防御
- RSS 取得時の SSRF 対策: スキーム検証、リダイレクト先の事前検証、プライベート IP の拒否
- レスポンスの最大バイト数チェック、gzip 解凍後サイズ検査でメモリ DoS（Gzip bomb）を防止
- .env の読み込みで OS 環境変数保護（protected set）を実装

Changed
- 新規初期リリースのため該当なし

Fixed
- 新規初期リリースのため該当なし

Deprecated
- 新規初期リリースのため該当なし

Removed
- 新規初期リリースのため該当なし

Notes / Observations
- 現在 strategy、execution、monitoring パッケージの __init__.py はプレースホルダ（将来的な実装領域）。
- jquants_client / news_collector の外部ネットワーク呼び出し部分はタイムアウトやリトライを持つが、実運用では API キーや環境変数の適切な管理（.env の構成）が必要。
- DuckDB スキーマは多くの制約と外部キーを含むため、既存データを手動マイグレーションする際は注意が必要。

--- 
この CHANGELOG はコードベースの内容から推測して作成しました。実際のリリースノートとして公開する場合は、日付・変更点の確定・責任者確認を行ってください。