Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。
フォーマットは Keep a Changelog に従い、セマンティックバージョニングを採用します。

0.1.0 - 2026-03-17
------------------

Added
- 初回リリース: kabusys パッケージ (バージョン 0.1.0)
  - パッケージの公開メタ情報: __version__ = "0.1.0"

- 環境設定管理 (kabusys.config)
  - プロジェクトルート検出: .git または pyproject.toml を起点に自動でルートを探索する実装を追加。パッケージ配布後も動作するよう CWD に依存しない設計。
  - .env 読み込み: .env と .env.local を自動ロード（OS 環境変数を保護し .env.local は上書き）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 柔軟な .env パーサ: export プレフィックス、シングル/ダブルクォート、エスケープ、コメント処理などに対応するパーサ実装。
  - Settings クラス: J-Quants / kabuステーション / Slack / データベース / システム設定を環境変数から取得するプロパティを提供。値検証（KABUSYS_ENV, LOG_LEVEL）とデフォルト値を設定。
  - DB パスは Path 型で返却（expanduser 対応）。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - データ取得機能:
    - 株価日足 (fetch_daily_quotes)
    - 財務データ（四半期 BS/PL）（fetch_financial_statements）
    - JPX マーケットカレンダー（fetch_market_calendar）
  - API 呼び出しの設計:
    - レート制限 (120 req/min) を守る固定間隔スロットリング実装（_RateLimiter）。
    - 冪等性: DuckDB 保存用の save_* 関数は ON CONFLICT を利用して重複を排除。
    - ページネーション対応（pagination_key を追跡して全件取得）。
    - リトライロジック: 指数バックオフで最大 3 回リトライ（408/429/5xx を対象）。429 の場合は Retry-After ヘッダを優先。
    - 401 処理: id_token の自動リフレッシュを行い 1 回再試行する仕組み（無限再帰対策あり）。
    - id_token キャッシュ: モジュールレベルでトークンをキャッシュしページネーション間で再利用。
    - 取得メタ情報: fetched_at を UTC タイムスタンプで記録して Look-ahead Bias を防止。
  - 保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar を提供。PK 欠損行のスキップ、保存件数ログ、ON CONFLICT DO UPDATE による更新をサポート。
  - 型変換ユーティリティ: _to_float, _to_int（浮動小数文字列の扱いを明示）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード取得 (fetch_rss) と記事保存 (save_raw_news / save_news_symbols / _save_news_symbols_bulk) の実装。
  - セキュリティ / 堅牢性:
    - defusedxml を使用して XML BOM 等の攻撃を防止。
    - SSRF 対策: HTTP リダイレクト前にスキームとホストの検査を行う _SSRFBlockRedirectHandler、および初回ホスト検証（プライベートアドレス判定）を実装。
    - 許可スキームは http/https のみ。
    - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10MB) を採用し、gzip 解凍後のサイズチェックを含む（Gzip bomb 対策）。
    - User-Agent / Accept-Encoding 指定とタイムアウトの利用。
  - データ整形 / 冪等性:
    - URL 正規化 (_normalize_url): トラッキングパラメータ除去 (utm_ など)、スキーム/ホストの小文字化、フラグメント除去、クエリパラメータソート。
    - 記事ID: 正規化 URL の SHA-256 の先頭32文字を使用して冪等性を担保。
    - テキスト前処理 (preprocess_text): URL 除去、空白正規化。
    - raw_news への一括 INSERT はチャンク化してトランザクション内で実行し、INSERT ... RETURNING により実際に挿入された ID を返す。
    - news_symbols の一括登録もチャンク化して ON CONFLICT DO NOTHING + RETURNING で正確な挿入数を返す。
  - 銘柄抽出:
    - extract_stock_codes: テキスト中の 4 桁数字候補を抽出し、known_codes によるフィルタリングで有効銘柄のみを返す（重複除去）。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataSchema.md に基づく多層スキーマを定義・初期化:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・チェック制約・PRIMARY KEY を設定。
  - インデックス定義: よく使うクエリパターンに基づくインデックスを作成。
  - init_schema(db_path): ディレクトリ作成（必要な場合）→ 全DDL/インデックス実行 → DuckDB 接続を返却。冪等にテーブル作成。
  - get_connection(db_path): 既存 DB への接続取得（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の基本方針とユーティリティを実装:
    - ETLResult データクラス: ETL 実行結果（取得/保存件数、品質問題、エラー）を集約し、辞書化可能にする。
    - 差分更新ヘルパー: _table_exists, _get_max_date を実装し、get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
    - 市場カレンダーヘルパー: _adjust_to_trading_day（非営業日の調整）。
    - run_prices_etl: 差分更新ロジック（最終取得日に基づく date_from 自動算出、backfill_days デフォルト=3、最小取得日 _MIN_DATA_DATE=2017-01-01）による株価データ取得→保存の実装（fetch + save）。品質チェックモジュールとの連携を想定した設計。
    - カレンダー先読み日数、バックフィル日数等の定数を定義。

Security
- 外部データ取得を伴うコンポーネントに対して以下の保護を実装:
  - defusedxml による XML パース保護
  - SSRF を抑止するリダイレクト検査とプライベート IP 判定
  - レスポンスサイズ制限と Gzip 解凍後の再チェック（DoS 対策）
  - 環境変数ロード時に OS 環境変数を保護する仕組み

Performance / Reliability
- API レート制限遵守のための固定間隔スロットリング
- リトライ（指数バックオフ）と 429/Retry-After の扱い
- ページネーション対応・トークンキャッシュによる効率化
- DuckDB 側はチャンク化・トランザクションでの一括挿入を採用してオーバーヘッドを低減

Internal / Developer notes
- テスト容易性のためにいくつかの箇所で注入・モックポイントを用意（例: news_collector._urlopen をモック可能）。
- settings の自動ロードはテスト実行時に無効化できるフラグを提供。
- 一部の関数は将来の拡張（品質チェックモジュール quality との連携、ETL の完全ワークフロー）を想定した設計となっている。

Known issues / TODO
- pipeline.run_prices_etl は差分取得と保存の主要ロジックを実装しているが、品質チェック呼び出しや最終の ETLResult 生成・返却の統合など追加実装箇所が残る可能性があります（今後のリリースで拡張予定）。

作者・貢献
- 初回実装に含まれる主要モジュール:
  - kabusys.config
  - kabusys.data.jquants_client
  - kabusys.data.news_collector
  - kabusys.data.schema
  - kabusys.data.pipeline
  - パッケージ初期化: kabusys.__init__.py

--------------------------------------------------------------------------------
今後のリリースでは、ETL 完全ワークフロー、品質チェック（quality モジュールとの統合）、strategy / execution 層の具体的な実装、運用向けモニタリング・アラート機能を追加する予定です。