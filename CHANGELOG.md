Keep a Changelog
=================

すべての重要な変更はこのファイルで管理します。  
このプロジェクトは、https://keepachangelog.com/ja/ のフォーマットに準拠しています。

[Unreleased]: https://example.com/compare/v0.1.0...HEAD

0.1.0 - 2026-03-17
------------------

Added
- パッケージの初期リリースを追加（kabusys v0.1.0）。
  - パッケージ初期化:
    - src/kabusys/__init__.py にてバージョンおよび公開モジュール（data, strategy, execution, monitoring）を定義。

- 環境設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能（プロジェクトルート検出: .git / pyproject.toml）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD のサポート。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いを考慮）。
  - override / protected オプションによる上書き制御（OS 環境変数保護）。
  - Settings クラスで各種必須設定をプロパティとして公開:
    - J-Quants / kabuステーション / Slack / DB パスなど
    - 環境（development, paper_trading, live）とログレベルのバリデーション
    - is_live / is_paper / is_dev のユーティリティプロパティ

- J-Quants クライアントを追加（src/kabusys/data/jquants_client.py）。
  - 提供 API:
    - get_id_token: リフレッシュトークンから ID トークンを取得（POST）。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar: ページネーション対応でデータを取得。
    - save_daily_quotes / save_financial_statements / save_market_calendar: DuckDB へ冪等に保存（ON CONFLICT DO UPDATE）。
  - 実装上の特徴:
    - グローバルなレート制御（120 req/min、固定間隔スロットリング）。
    - リトライ戦略（最大 3 回、指数バックオフ、HTTP 408/429/5xx をリトライ対象）。
    - 401 応答時はトークン自動リフレッシュを行い 1 回リトライ（無限再帰を防ぐ仕組みあり）。
    - ページネーションでのトークン共有のためのモジュールレベルの ID トークンキャッシュ。
    - JSON デコード失敗時の明示的エラー、タイムアウト設定、ログ出力。
    - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止。
    - 型変換ユーティリティ (_to_float, _to_int) による堅牢なデータ整形。

- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
  - 機能:
    - RSS フィードから記事を取得し raw_news テーブルへ保存、銘柄紐付け（news_symbols）を作成。
    - デフォルト RSS ソースに Yahoo Finance のビジネス RSS を含む。
  - セキュリティ・堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - ホスト/IP の private/loopback/link-local/multicast 判定（DNS で解決した全 A/AAAA を検査）。
      - リダイレクト時にスキームとホストを検証するカスタム HTTPRedirectHandler を利用。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後サイズ再検証（Gzip bomb 対策）。
    - URL 正規化（スキーム/ホストの小文字化、トラッキングパラメータ削除、フラグメント削除、クエリキーソート）。
    - 記事IDは正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保（utm_* 等を除去してからハッシュ）。
  - データ処理:
    - テキスト前処理（URL 除去、空白正規化）。
    - pubDate の RFC 2822 パース（タイムゾーンを UTC に揃え、失敗時は警告ログで現在時刻にフォールバック）。
    - 銘柄コード抽出（4桁数字、known_codes によるフィルタリング、重複排除）。
    - DuckDB への保存はトランザクション化し、INSERT ... RETURNING を使って実際に挿入された件数を返す。
    - bulk な news_symbols 保存機能とチャンク処理による SQL 長対策。

- DuckDB スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）。
  - 3 層構造のテーブル定義（Raw / Processed / Feature）および Execution 層を実装。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・チェック制約を豊富に付与（NOT NULL, CHECK 等）。
  - パフォーマンス向上のためのインデックス定義（銘柄×日付スキャン、状態検索など）。
  - init_schema(db_path) による親ディレクトリ自動作成と冪等なテーブル作成。
  - get_connection(db_path) で既存 DB へ接続（初期化は行わない）。

- ETL パイプライン（部分実装）を追加（src/kabusys/data/pipeline.py）。
  - 目的: 差分更新 + 保存 + 品質チェックのフローを提供。
  - 実装済みの要素:
    - ETLResult dataclass: 実行メタ情報・品質問題・エラー一覧を保持し、辞書化機能を提供。
    - _table_exists / _get_max_date ヘルパー: テーブル存在確認と最大日付取得。
    - 市場カレンダーを使った営業日調整ヘルパー _adjust_to_trading_day。
    - 差分更新ヘルパー get_last_price_date / get_last_financial_date / get_last_calendar_date。
    - run_prices_etl: 差分更新ロジック（最終取得日から backfill_days 前を date_from にする）、J-Quants からの取得と DuckDB への保存を実行。デフォルトバックフィルは 3 日、データ開始日は 2017-01-01。

- テスト容易性の配慮:
  - jquants_client の id_token を外部注入可能（テスト用モックしやすい）。
  - news_collector の _urlopen を差し替え（モック）可能にして HTTP レスポンスをテストで制御可能。

Security
- RSS 収集で defusedxml と SSRF/内部アドレスチェック、受信上限や gzip 解凍後の再チェックを導入し、外部入力に対する防御を強化。

Notes / Known issues
- 本 CHANGELOG は現在のコードベースから推測して記載しています。将来的な実装追加・設計変更により記述内容が更新される可能性があります。
- pipeline.run_prices_etl は「(取得レコード数, 保存レコード数)」のタプルを返す設計になっており、ETLResult と連携する想定です。実装の続き（財務・カレンダー ETL、品質チェック連携、完全な戻り値処理など）は今後追加される予定です。

---

今後の予定（短期）
- ETL の残りジョブ（財務データ、カレンダーの差分更新）、品質チェックモジュールの統合。
- strategy / execution / monitoring パッケージの実装と、実取引向けの安全性検証（paper/live 切替の自動テスト）。
- CI / テストケース整備（外部 API をモックした統合テスト、RSS/SSRF のセキュリティテスト）。