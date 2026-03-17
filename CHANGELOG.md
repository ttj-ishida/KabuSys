Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
形式は "Keep a Changelog" に準拠します。

Unreleased
----------

- なし

0.1.0 - 2026-03-17
------------------

Added
- 基本パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__、__version__ = 0.1.0）。
  - サブパッケージ骨格を追加（data, strategy, execution, monitoring を想定）。
- 環境変数 / 設定管理（kabusys.config）
  - .env/.env.local からの自動読み込みを実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能を追加（テスト用）。
  - .env パーサを実装（export プレフィックス、クォート、インラインコメント対応）。
  - OS 環境変数の保護（.env.local は既存 OS 環境変数を保護しつつ上書き可能）。
  - Settings クラスを導入し、アプリ固有設定（J-Quants / kabuステーション / Slack / DB パス / ログレベル / 環境）の取得と検証を提供。
  - env 値や log_level に対するバリデーション（許容値チェック）を実装。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - API へのリクエストユーティリティを実装（JSON 取得、タイムアウト処理、JSON デコードエラーハンドリング）。
  - レート制限対策として固定間隔スロットリング（_RateLimiter）を実装（デフォルト 120 req/min）。
  - 冪等性や信頼性向上のためのリトライロジックを実装（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
  - 401 Unauthorized 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュを実装。
  - ページネーション対応（pagination_key を利用）で fetch_daily_quotes / fetch_financial_statements を実装。
  - fetch_market_calendar を実装（祝日 / 半日 / SQ の取得）。
  - DuckDB へ保存する idempotent な保存関数を実装（save_daily_quotes / save_financial_statements / save_market_calendar、ON CONFLICT DO UPDATE）。
  - データの fetched_at を UTC で記録し、Look-ahead Bias に配慮。
  - 型変換ユーティリティ（_to_float / _to_int）を追加し、破損データや空値を安全に扱う。
- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからの記事取得と前処理、DuckDB への保存ワークフローを実装（fetch_rss / save_raw_news）。
  - 記事ID を URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を保証。
  - URL 正規化でトラッキングパラメータ削除（utm_* 等）、スキーム小文字化、フラグメント削除、クエリキーソートを実装。
  - defusedxml を使った XML パースで XML-Bomb 等の脅威に対処。
  - SSRF 対策を複合的に実装：
    - fetch 前のホスト検査（プライベートアドレス拒否）
    - リダイレクト時にスキーム/ホストを検証するカスタムリダイレクトハンドラを導入（_SSRFBlockRedirectHandler）
    - _urlopen を分離してテスト時にモック可能に設計
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入しメモリ DoS を防止。gzip 解凍後のサイズ検査も実施。
  - content:encoded を優先して本文を取得、URL 除去・空白正規化などの前処理を実装。
  - DB 保存はチャンク（デフォルト1000）でまとめてトランザクション化し、INSERT ... RETURNING によって実際に挿入された件数を取得する実装（save_raw_news / save_news_symbols / _save_news_symbols_bulk）。
  - 銘柄コード抽出ユーティリティを実装（4桁数字パターン、known_codes によるフィルタリング）。
  - run_news_collection により複数 RSS ソースを独立して取得し、取得失敗が他ソースへ波及しない実行を実現。
- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層にまたがるテーブル群を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 各テーブルに適切な制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を付与。
  - 頻出クエリに備えたインデックス群を定義。
  - init_schema(db_path) により親ディレクトリ自動作成、全DDL/インデックスを冪等的に実行して接続を返す。get_connection も提供。
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（差分取得）・保存・品質チェックのためのパイプライン骨格を実装。
  - ETLResult データクラスを追加し、取得件数・保存件数・品質問題・エラー一覧を一元管理可能に。
  - 市場カレンダーの先読み（日数設定）や、デフォルトの backfill（3日）を導入し、API 後出し修正に対応。
  - DB の最終取得日を調べるユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）と、営業日に調整するヘルパー（_adjust_to_trading_day）を実装。
  - run_prices_etl による株価日足の差分 ETL を実装（差分計算・jquants_client による取得・保存）。

Security
- XML 処理に defusedxml を使用して XXE / XML Bomb の脅威を低減。
- RSS フェッチで SSRF を考慮した多層防御（スキーム検証、プライベートアドレス拒否、リダイレクト時の事前検証）。
- .env 読み込みで OS 環境変数を保護する仕組みを導入（protected set）。

Performance
- J-Quants API のレート制御（固定間隔スロットリング）で API 制限を順守。
- リトライ時は指数バックオフと Retry-After ヘッダを考慮。
- ニュースの DB 保存はバルク挿入・チャンク化してトランザクションをまとめ、オーバーヘッドを削減。
- ページネーションで効率的に全データを取得。

Maintenance / Reliability
- ID トークンのモジュールキャッシュを導入しページネーション間でトークンを共有。
- DuckDB 側は ON CONFLICT DO UPDATE / DO NOTHING を多用し冪等性を確保。
- 各種ユーティリティにおいて入力検証と例外ハンドリングを整備（日時パースの代替値、型変換の失敗時の安全復帰など）。
- ネットワーク / HTTP エラーを考慮した詳細なログ出力を追加しトラブルシュートを容易化。

Notes / Misc
- news_collector._urlopen を分離しているため、テストで容易に外部 HTTP をモック可能。
- schema.init_schema(":memory:") でインメモリ DuckDB を利用可能（テスト用途）。

Breaking Changes
- なし（初回リリース）。

Acknowledgements
- 初回リリースでデータ収集・保存・ETL の基盤を実装しました。戦略実装（strategy）、実行コンポーネント（execution）、モニタリング（monitoring）は今後の拡張対象です。

--- 

（注）この CHANGELOG は提示されたコードベースを基に推測して作成しています。実際の仕様やリリース履歴と差異がある可能性があります。必要であれば日付、バージョン、追加・修正項目の微調整を行います。