CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠し、このリポジトリで行われたすべての注目すべき変更を記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注意: 以下の変更点はソースコードの内容から推測して作成しています。

Unreleased
----------

- なし

0.1.0 - 2026-03-17
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ: src/kabusys/__init__.py にて __version__ = "0.1.0"、公開モジュールを __all__ で定義。

- 環境設定管理
  - .env/.env.local と OS 環境変数を統合して読み込む自動ローダーを実装（src/kabusys/config.py）。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない。
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化。
    - .env 行パーサは export 句、クォート、エスケープ、インラインコメント等に対応。
    - protected パラメータにより OS 環境変数の上書きを防止。
  - Settings クラスを公開（settings）。以下の基本設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパス、Path を返す）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL の検証
    - ヘルパー: is_live / is_paper / is_dev

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - ベース実装:
    - レート制限（120 req/min）を守る固定間隔スロットリング（内部 _RateLimiter）。
    - 冪等なページネーション対応 fetch API:
      - fetch_daily_quotes (OHLCV 日足)
      - fetch_financial_statements (四半期 BS/PL)
      - fetch_market_calendar (JPX カレンダー)
    - HTTP レイヤでの堅牢性:
      - リトライ: 指数バックオフ（最大 3 回）、対象ステータス 408/429 および 5xx。
      - 429 の場合は Retry-After を尊重。
      - 401 受信時はリフレッシュトークンで id_token を自動更新して 1 回リトライ（無限再帰防止）。
      - id_token のモジュールレベルキャッシュを実装。
    - JSON デコード失敗時の明確なエラー。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar: ON CONFLICT DO UPDATE による冪等（重複更新）保存。
    - PK 欠損行スキップ、保存件数をログ出力。
  - 値変換ユーティリティ:
    - _to_float, _to_int: 空値・不正値の安全な変換ロジック（"1.0" 等の扱いに注意）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集して DuckDB に保存するための包括的実装:
    - フィード取得（fetch_rss）:
      - defusedxml を利用した安全な XML パース（XML Bomb 等への対策）。
      - gzip 圧縮対応、最大受信サイズ制限（10 MB）と解凍後の再チェック（Gzip-bomb 対策）。
      - SSRF 対策:
        - URL スキーム検証（http/https のみ許可）。
        - リダイレクト時にスキームとリダイレクト先のホストがプライベートアドレスか検査する専用ハンドラ（_SSRFBlockRedirectHandler）。
        - 初回接続前にホストのプライベートアドレスチェックを実行。
      - 不正なスキームやサイズ超過時は安全にスキップ。
      - content:encoded 名称空間の優先処理、pubDate のパースと UTC 正規化。
      - URL 正規化とトラッキングパラメータ除去（_normalize_url）。
      - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
      - テキスト前処理（URL 除去、空白正規化）。
    - DB 保存:
      - save_raw_news: チャンク分割して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDを返す。1 トランザクション内で実行。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンクで保存（ON CONFLICT で重複を除外）。INSERT ... RETURNING で実挿入数を算出。
    - 銘柄コード抽出:
      - extract_stock_codes: 正規表現による 4 桁数字抽出と known_codes によるフィルタリング（重複除去）。
    - デフォルト RSS ソースとして Yahoo Finance のビジネス RSS を設定（DEFAULT_RSS_SOURCES）。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - DataPlatform.md に基づく 3 層 + Execution レイヤの DDL を実装:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（PK, CHECK, FOREIGN KEY）を設定し、典型的なクエリ用に複数インデックスを作成。
  - init_schema(db_path) でディレクトリ自動作成、全テーブル・インデックスの作成（冪等）。
  - get_connection(db_path) で既存 DB への接続を取得（スキーマ初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult データクラス: 実行結果の集約（品質問題リスト、エラーメッセージ等）、辞書化ユーティリティ。
  - 差分更新ロジックのヘルパー:
    - テーブル存在チェック、最大日付取得 (_get_max_date)、市場カレンダーに基づく営業日調整 (_adjust_to_trading_day)。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date。
  - run_prices_etl:
    - 差分更新の実装方針: 最終取得日から backfill_days 日分を遡って再取得（デフォルト backfill_days=3）。初回は J-Quants が提供する最小日（2017-01-01）から取得。
    - fetch -> 保存（jquants_client.save_*） -> ロギングの流れを実装。

Changed
- 初版につき該当なし（新規実装）。

Fixed
- 初版につき該当なし。

Security
- 複数のセキュリティ対策を導入:
  - RSS/HTTP 周りの SSRF 防止（スキーム検証・ホストのプライベートIPチェック・リダイレクト検査）。
  - XML パースで defusedxml を使用し XML 関連攻撃を軽減。
  - .env ローダーでパスワード等の OS 環境変数上書きを保護。

Notes / Known issues
- run_prices_etl の戻り値
  - run_prices_etl の最後の return 文は現状 (len(records),) のように単一要素のタプルを返す実装になっており、関数アノテーション tuple[int, int] と整合していません。呼び出し側で (fetched, saved) を期待するため、保存件数を含める適切な戻り値へ修正が必要です。

- ネットワーク / 外部 API 依存
  - J-Quants API、RSS フィード、kabu API、Slack 等の外部サービスへの依存があるため、運用時は認証情報・接続先の設定を正しく行ってください（settings 参照）。

- テスト容易性
  - news_collector._urlopen などはテスト用にモック差し替え可能な設計になっていますが、統合テストでは外部ネットワーク切断や環境変数の保護を考慮してください。

Upgrade notes
- v0.1.0 は初期リリースです。既存の機能に対する破壊的変更は今のところありません。今後のリリースで ETL の戻り値・エラーハンドリングの強化、監視・メトリクスの追加、kabu ステーション連携の実装が予定されます。

Contributing
- バグ修正（特に run_prices_etl の戻り値修正）やテストの追加、ドキュメント整備は歓迎します。