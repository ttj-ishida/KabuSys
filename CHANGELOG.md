CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

[unreleased]: https://example.com/compare/v0.1.0...HEAD

リリースノート
-------------

[0.1.0] - 2026-03-17
^^^^^^^^^^^^^^^^^^^^

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パッケージ公開用の __all__ を定義（data, strategy, execution, monitoring）

- 環境変数・設定管理（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定を自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
  - .git または pyproject.toml を起点にプロジェクトルートを探索するため、CWD に依存しない実装。
  - .env のパースは export 形式、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - 必須設定取得用の _require と Settings クラスを実装。J-Quants トークン、kabuAPI パスワード、Slack トークン／チャンネル、DB パス等をプロパティで取得可能。
  - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）を実装。
  - デフォルトのデータベースパス（DuckDB / SQLite）を提供。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API へのリクエストラッパーを実装。特徴:
    - レート制限（120 req/min）を固定間隔スロットリングで遵守する RateLimiter を提供。
    - リトライ戦略（指数バックオフ、最大 3 回）を実装。対象ステータス: 408、429、5xx。
    - 401 受信時はリフレッシュトークンから id_token を自動更新して 1 回リトライ（無限再帰を防止）。
    - ページネーション対応（pagination_key を利用して全ページ取得）。
    - id_token 用のモジュールレベルキャッシュを実装し、ページ間でトークンを共有。
    - JSON デコードエラーやその他異常時の詳細なログ／例外を整備。
  - データ取得関数:
    - fetch_daily_quotes: 株価日足（OHLCV）のページネーション取得。
    - fetch_financial_statements: 四半期財務データのページネーション取得。
    - fetch_market_calendar: JPX マーケットカレンダーの取得。
  - DuckDB への保存関数（冪等設計、ON CONFLICT）:
    - save_daily_quotes: raw_prices へ保存（ON CONFLICT DO UPDATE）。
    - save_financial_statements: raw_financials へ保存（ON CONFLICT DO UPDATE）。
    - save_market_calendar: market_calendar へ保存（ON CONFLICT DO UPDATE）。
  - ロギングで取得件数・保存件数を報告し、PK 欠損行のスキップに警告を出す。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news に保存する一連の処理を実装。
  - セキュリティ・堅牢性のための実装:
    - defusedxml を利用して XML Bomb 等の攻撃を防御。
    - SSRF 対策: リダイレクト時のスキーム検証、ホストのプライベートアドレス判定（IP & DNS 解決）を行うカスタム RedirectHandler を導入。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンス受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - トラッキングパラメータ（utm_*, fbclid 等）を除去して URL 正規化。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
  - フィード処理:
    - fetch_rss: RSS 取得 → XML パース → item から記事抽出（title/description/content:encoded 優先）→ 前処理（URL 除去・空白正規化）→ NewsArticle 型で返却。
    - save_raw_news: DuckDB へのバルク挿入（チャンク化、トランザクション、INSERT ... RETURNING を利用）し、実際に挿入された記事IDを返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを冪等に保存、INSERT ... RETURNING を利用して挿入数を返す。
  - 銘柄抽出:
    - extract_stock_codes: 正規表現（4桁）で候補を抽出し、known_codes と照合して重複除去して返す。
  - run_news_collection: 複数ソースの一括収集ジョブを提供。各ソースは独立して例外処理され、1 ソースの失敗が他に影響しない。

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の階層を想定したテーブル定義を実装。
  - 代表的なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（PRIMARY KEY, CHECK, FOREIGN KEY 等）を設定し、クエリ頻度を鑑みたインデックスを用意。
  - init_schema(db_path) でディレクトリ作成（必要時）→ 全 DDL を実行して初期化（冪等）。
  - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL 実行結果を格納する ETLResult データクラスを実装（品質チェック結果やエラーの集約、辞書化メソッド含む）。
  - 差分更新に関するユーティリティ:
    - _table_exists / _get_max_date を実装し、raw_* の最終取得日を取得するヘルパを提供（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - _adjust_to_trading_day: 非営業日の場合に直近営業日に調整するロジック（market_calendar を参照）。
  - run_prices_etl: 差分更新を実行する関数を実装（最終取得日を考慮した date_from 自動計算、backfill による再取得、jquants_client 経由で取得→保存）。

Security
- RSS/HTTP 関連で SSRF 対策、XML の安全パーサ（defusedxml）、レスポンスサイズ制限、URL スキーム制限を導入。
- J-Quants クライアントでタイムアウト、リトライ、レート制限を実装し外部 API との安定的な通信を図る。

Fixed
- （初回リリースのため履歴なし。下記 Known issues を参照してください）

Known issues / Notes
- run_prices_etl の戻り値に関する実装上の不整合:
  - 関数のドキュメントは (取得件数, 保存件数) のタプルを返すと記載していますが、現行実装の末尾は "return len(records)," のように末尾カンマのみで帰しており、期待される 2 要素タプルではなく 1 要素のタプル／値になってしまう可能性があります。呼び出し側は戻り値の形を想定しているため、ここは修正（saved 変数を含めて返す）する必要があります。
- pipeline モジュールは差分 ETL の骨格を提供していますが、run_prices_etl 以外（財務データ/カレンダーの個別 ETL 実行関数）の完了状態はファイル上に部分的に実装されているため、運用前にエンドツーエンドでの検証が必要です。
- DB スキーマ追加は後方互換性を考慮して冪等に作成されますが、既存データとのマイグレーション方針はプロジェクト運用ルールに従ってください。init_schema() は既存テーブルを上書きしない設計です。

Upgrade / Migration notes
- 初めて利用する場合は schema.init_schema(settings.duckdb_path) を実行して DuckDB スキーマを作成してください。
- .env サポートと設定キーの追加に伴い、既存環境変数がある場合は優先されます。ローカルの .env.local で上書き可能。自動読み込みを停止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

開発者向けメモ
- jquants_client._request は allow_refresh=False を渡した場合に token の自動リフレッシュを行わないため、get_id_token 内部呼び出しやトークン取得ループでの無限再帰を回避しています。
- news_collector のネットワークアクセスは _urlopen を通す設計で、テスト時にはこの関数をモックして外部アクセスを差し替え可能です。
- DuckDB への大量挿入はチャンク単位で行い、トランザクションでまとめてコミット／ロールバックするため、部分挿入時の整合性が保たれます。

Authors
- コードベースに基づいて推測した実装内容を本 CHANGELOG に反映。

[0.1.0]: https://example.com/tag/v0.1.0