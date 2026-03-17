CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog 準拠で管理しています。
最新版: 0.1.0

[Unreleased]
-------------

- なし

0.1.0 - 2026-03-17
------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" の基本コンポーネントを追加。
  - パッケージエントリポイントを追加 (kabusys/__init__.py)
    - __version__ = "0.1.0"
    - 公開モジュール: data, strategy, execution, monitoring
  - 設定管理モジュール (kabusys.config)
    - .env / 環境変数の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）
    - .env ローダーは .env → .env.local の順で読み込み、.env.local が上書き
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
    - .env 行パーサ（export 文、クォート、インラインコメント等に対応）
    - Settings クラスを公開（J-Quants / kabu API / Slack / DBパス / 環境・ログレベル判定等）
    - 入力値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）
  - J-Quants API クライアント (kabusys.data.jquants_client)
    - ベース機能: トークン取得 (get_id_token), ページネーション対応の取得関数(fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar)
    - レート制御: 固定間隔スロットリングによる 120 req/min 制限 (_RateLimiter)
    - 再試行/バックオフ: 指数バックオフ、最大リトライ回数、429 の Retry-After 優先処理
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有
    - DuckDB へ冪等的に保存する save_* 関数（ON CONFLICT DO UPDATE）
    - 型変換ユーティリティ (_to_float / _to_int) による堅牢なデータ変換
  - ニュース収集モジュール (kabusys.data.news_collector)
    - RSS 取得(fetch_rss) と記事前処理(preprocess_text)、URL 正規化(_normalize_url)
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保
    - defusedxml を利用した安全な XML パース（XML Bomb 等への防御）
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - ホストのプライベートアドレス判定（_is_private_host）
      - リダイレクト時の事前検査用ハンドラ (_SSRFBlockRedirectHandler)
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）や gzip 解凍後の再チェック
    - DuckDB へのバルク挿入とトランザクション管理（save_raw_news, save_news_symbols, _save_news_symbols_bulk）
    - 銘柄コード抽出 (extract_stock_codes)：4桁数値マッチング＋既知コードフィルタ
    - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリ追加
  - DuckDB スキーマ管理 (kabusys.data.schema)
    - DataPlatform 設計に基づくスキーマを定義（Raw / Processed / Feature / Execution 層）
    - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル
    - features, ai_scores といった Feature 層
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層
    - インデックスの作成（よく使われるクエリを想定）
    - init_schema(db_path) でディレクトリ自動作成・DDL 実行・インデックス作成を実行
    - get_connection(db_path) で既存 DB への接続を提供
  - ETL パイプライン骨子 (kabusys.data.pipeline)
    - ETLResult データクラスによる ETL 実行結果の集約（品質問題・エラーの収集）
    - 差分更新ヘルパー: テーブル最終取得日取得関数 (get_last_price_date / get_last_financial_date / get_last_calendar_date)
    - 市場カレンダーに基づく営業日調整ヘルパー (_adjust_to_trading_day)
    - run_prices_etl による差分取得フロー（バックフィル日数設定、最小取得日考慮、jquants_client との連携）
    - 品質チェック（quality モジュール）を呼び出す前提で設計（問題の致命度に応じた判断を呼び出し元に委譲）
  - ロギング／堅牢性
    - 各処理に情報・警告ログを追加し監査しやすく実装
    - ネットワーク・XML・DB トランザクションの例外処理とロールバック

Changed
- 初版のため "Changed" に記載する差分は特になし（新規追加）。

Fixed
- 実装段階で次の点を考慮して修正済みの挙動を導入:
  - DB 書き込みは全て冪等性を意識（ON CONFLICT 句を利用）して設計
  - fetch_* 関数はページネーションキーの重複防止を実装
  - news_collector の insert はチャンク化・INSERT ... RETURNING を用い、実際に挿入された件数を正確に取得

Security
- RSS パーサに defusedxml を採用して XML ベースの攻撃を緩和
- SSRF 対策を導入（スキーム検証、ホストのプライベート判定、リダイレクト前検査）
- レスポンスサイズ上限および gzip 解凍後のサイズ検査を実装してメモリDoS対策を追加

Notes / Known issues
- run_prices_etl の末尾がソース断片のため、現在の実装（このコミット時点）では戻り値の組み立てが未完の可能性があります。実際の返却は意図としては (fetched_count, saved_count) を返す設計ですが、最終行の実装確認・単体テストを要します。
- strategy/, execution/, monitoring/ の __init__.py は存在するものの中身が空のプレースホルダになっており、各レイヤの実装は今後のリリースで追加予定です。
- quality モジュールは参照されているが（pipeline 内）、品質チェックの具体的実装は別途提供される想定です。
- 単体テストおよび統合テストの適用状況はソースからは判断できないため、CI 設計・テスト整備が推奨されます。

公平な使用上の注意
- 外部 API（J-Quants / kabuステーション / Slack 等）に依存するため、本ライブラリを動かす際は各種 API トークン・設定を .env や環境変数で適切に設定してください（Settings が未設定の必須変数については ValueError を送出します）。

ライセンス、寄稿、今後の開発方針
- 本 CHANGELOG はソースコードの現状からの推測に基づいて作成しています。今後は以下を計画しています:
  - strategy, execution, monitoring 層の実装充実
  - 単体テスト・統合テストの追加と CI の整備
  - run_prices_etl 等の ETL 処理の追加安定化（バックフィル戦略・品質チェックの実装強化）
  - ドキュメント（DataPlatform.md 等）との整合性チェック

以上