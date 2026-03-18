CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは「Keep a Changelog」仕様に準拠しています。

フォーマット:
- Unreleased — 今後の変更
- バージョン — リリース日（YYYY-MM-DD）

Unreleased
----------
（現在のところ未定義）

0.1.0 - 2026-03-18
-----------------

Added
- 初回リリース。KabuSys 日本株自動売買システムの基盤を提供する。
- パッケージメタ情報
  - パッケージバージョンを kabusys.__version__ = "0.1.0" として導入。
  - 公開モジュール: data, strategy, execution, monitoring のエクスポートを定義。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出: .git または pyproject.toml を起点にプロジェクトルートを探索。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env 解析器の実装:
    - export KEY=val 形式のサポート、シングル/ダブルクォートのエスケープ対応、インラインコメント処理。
  - Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / DB パス 等のプロパティを定義（必須項目は未設定時に ValueError）。
    - 環境（development / paper_trading / live）とログレベルの検証ロジック。
    - is_live / is_paper / is_dev のヘルパー。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API から日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得するクライアントを実装。
  - 設計上の特徴:
    - レート制限対応: 固定間隔スロットリングで 120 req/min を守る RateLimiter を実装。
    - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx に対する再試行を実装。
    - 401 処理: トークン期限切れ検知で自動リフレッシュして 1 回だけ再試行。
    - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias のトレースを可能に。
    - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で上書き可能。
  - 提供関数:
    - get_id_token(): リフレッシュトークンから id token を取得。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar: ページネーション対応でデータを取得。
    - save_daily_quotes / save_financial_statements / save_market_calendar: DuckDB へ冪等に保存するユーティリティを実装。
  - 値変換ユーティリティ: 安全な _to_float/_to_int 実装（不正な数値や小数の扱いに注意）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュース記事を収集し raw_news に保存する機能を実装。
  - 安全設計:
    - defusedxml を用いて XML 攻撃（XML Bomb 等）を緩和。
    - SSRF 対策: リダイレクト時のスキーム検査、プライベート IP/ホストの検出とブロック。
    - URL スキームは http/https のみ許可。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査。
  - データ処理:
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去）。
    - 記事IDは正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成して冪等性を保証。
    - テキストの前処理（URL 除去、空白正規化）。
    - 銘柄コード抽出ロジック（4桁数字を正規表現で抽出し、known_codes と照合）。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING を用いたチャンク単位のバルク挿入（トランザクション制御）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けをまとめて挿入、ON CONFLICT で重複排除。
  - run_news_collection: 複数 RSS ソースの統合収集ジョブ（ソース単位でエラーハンドリングを行い継続処理）。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataPlatform 設計に基づくスキーマを定義・初期化する init_schema() を実装。
  - 層構造:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions 等。
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等。
    - Feature Layer: features, ai_scores。
    - Execution Layer: signals, signal_queue, orders, trades, positions, portfolio_performance 等。
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックス（頻出クエリ向け）を定義。
  - get_connection(): 既存 DB へ接続するユーティリティ。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新を行う ETL パイプラインの基礎実装。
  - 設計上の特徴:
    - 差分更新: DB の最終取得日を参照して未取得分のみ API から取得（デフォルトの backfill_days=3 を使用して後出し修正に対応）。
    - 市場カレンダーは将来日を先読み可能（_CALENDAR_LOOKAHEAD_DAYS）。
    - 品質チェックモジュール（quality）との連携を想定。品質問題は集約して呼び出し元に報告（Fail-Fast ではない）。
    - ETLResult データクラス: 実行結果、検出された品質問題、エラーの集約を提供。
  - ヘルパー関数:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date: 各テーブルの最終日取得。
    - _adjust_to_trading_day: 非営業日の調整（最大 30 日遡り）を実装。
    - run_prices_etl: 差分取得→保存の流れ（fetch + save）を実装（バックフィル処理を含む）。

Changed
- 初回リリースのため変更履歴なし（ベースラインの導入）。

Fixed
- 初回リリースのため修正履歴なし。

Security
- RSS パーシングにおいて defusedxml を採用し、XML 関連の脆弱性を軽減。
- ニュース収集で SSRF 対策（リダイレクト検証、プライベート IP/ホストのブロック、許可スキームの限定）を実装。
- 外部 API 呼び出しでタイムアウト、リトライ、Retry-After の考慮など耐障害性を強化。

Notes / Known limitations
- strategy/ と execution/ パッケージは空の初期化ファイルのみで、実際の戦略ロジックや発注処理は未実装（今後の追加予定）。
- pipeline.run_prices_etl の末尾が一部切れているように見える（実装継続・完了の必要あり）。（コードベースから推測される TODO）
- quality モジュールの実装はこの差分からは確認できず、ETL の品質チェック連携は別途実装が必要。
- DuckDB スキーマは初期化ロジックを提供するが、マイグレーション/バージョン管理機能は含まれていない。

Acknowledgements
- 本リリースはデータ収集・保存・ETL の基盤を提供することを目的としています。今後、戦略実装・実行層の統合・品質チェック機能の拡張を予定しています。

ライセンスや貢献方法などの情報はリポジトリの README を参照してください。