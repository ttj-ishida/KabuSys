# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
このファイルはコードベースの現状から推測した初期リリースの変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-03-18
初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主に設定管理、データ収集/保存、DuckDB スキーマ、ETL パイプライン、ニュース収集、安全化対策を含みます。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを v0.1.0 として定義。公開サブパッケージ (data, strategy, execution, monitoring) を __all__ に列挙。

- 環境変数 / 設定管理 (kabusys.config)
  - .env および .env.local をプロジェクトルート（.git または pyproject.toml の位置を探索）から自動読み込みする仕組みを実装。
  - 環境変数自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用）。
  - .env のパーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメントの扱いなど）。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）をプロパティ経由で取得。入力値検証を行い不正値時は例外を発生させる。
  - デフォルト値（KABUSYS_ENV=development、LOG_LEVEL=INFO、KABU_API_BASE_URL 等）を定義。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 通信の共通ユーティリティを実装（URL 組立て、ヘッダ、JSON デコード）。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する _RateLimiter を導入。
  - リトライロジック: 指数バックオフ (base=2) で最大 3 回リトライ。対象ステータスに 408/429/5xx を含む。429 の場合は Retry-After ヘッダを尊重。
  - 401 応答時のトークン自動リフレッシュを 1 回のみ行う実装（無限再帰防止のため allow_refresh フラグ）。
  - ID トークンの取得関数 get_id_token（リフレッシュトークンを使用）。
  - ページネーション対応のデータ取得関数を実装:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存関数（冪等化: ON CONFLICT DO UPDATE）を実装:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ変換ユーティリティ (_to_float, _to_int) を実装し、入力の堅牢化（None/空文字/不正値の扱い）を行う。
  - 取得時刻（fetched_at）を UTC ISO 形式で保存し、Look-ahead Bias のトレーサビリティを確保。

- RSS/ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事収集、前処理、DuckDB への保存までを網羅するモジュールを実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パースで XML Bomb 等への対策。
    - リダイレクト時にスキームとホストの事前検証を行うカスタム RedirectHandler を導入し SSRF を防止。
    - URL スキームは http/https のみ許可。プライベート/ループバック/リンクローカル/マルチキャストアドレスは拒否。
    - レスポンス最大サイズ（MAX_RESPONSE_BYTES = 10MB）で受信上限を設定しメモリ DoS を軽減。gzip 解凍後のサイズ検査も実施（Gzip bomb 対策）。
  - URL 正規化:
    - _normalize_url によりスキーム/ホスト小文字化、トラッキングパラメータ（utm_ 等）の削除、フラグメント除去、クエリソートを実施。
    - 記事IDは正規化 URL の SHA-256 ハッシュ先頭32文字を使用し、冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - RSS 取得関数 fetch_rss を実装（content:encoded を優先、guid の代替扱い、pubDate パース）。
  - DuckDB 保存関数:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を使用。チャンク(1000件)でバルク挿入、1 トランザクションでコミット。新規挿入された記事ID一覧を返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルクで保存。ON CONFLICT DO NOTHING + RETURNING を利用し、実際に挿入された件数を返す。
  - 銘柄コード抽出ロジック (extract_stock_codes): 4桁数字を候補抽出し、known_codes に含まれるもののみを採用（重複削除）。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataSchema.md に基づく多層スキーマを定義（Raw / Processed / Feature / Execution レイヤー）。
  - 多数のテーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - 各テーブルに適切な型チェック・制約・PRIMARY KEY・FOREIGN KEY を定義。
  - 頻出クエリに備えたインデックス群を定義。
  - init_schema(db_path) により、親ディレクトリ自動作成／DDL 実行／インデックス作成まで行い、初期化済み DuckDB 接続を返す（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化を行わない既存接続取得）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL のフロー設計と一部実装を追加:
    - 差分更新の考え方（最終取得日から backfill_days 分の再取得で API の後出し修正を吸収）。
    - デフォルトバックフィル 3 日、カレンダー先読み 90 日、最小データ開始日 2017-01-01 を定義。
  - ETLResult データクラスを実装し、処理結果（取得数/保存数/品質問題/エラー）を集約。品質問題は辞書化可能。
  - DB ヘルパー: テーブル存在判定、日付最大値取得（_get_max_date）などを実装。
  - 市場カレンダー補助: 非営業日の場合に直近の営業日に調整する _adjust_to_trading_day を実装。
  - 差分ETL の一部: run_prices_etl を実装（date_from 自動算出、fetch_daily_quotes 呼び出し、save_daily_quotes 保存）。（注: pipeline モジュールは品質チェックの統合など追加実装余地あり）

### Security
- 複数の箇所で安全性を考慮:
  - RSS 処理で defusedxml を使用し XML 関連攻撃を回避。
  - SSRF 対策のリダイレクト検査、ホストのプライベートIPチェック。
  - .env パーサでの安全なクォート/エスケープ処理。
  - 外部 API 呼び出しでタイムアウト、再試行、RateLimit 制御を実装。

### Performance / Reliability
- DuckDB へのバルク挿入をチャンク化してオーバーヘッドを低減。
- save_* 関数は SQL 側で ON CONFLICT 対応し冪等性を確保。
- fetch_daily_quotes / fetch_financial_statements はページネーションに対応して全件取得可能。
- ニュース収集は個々の RSS ソースごとにエラーハンドリングし、1 ソースの失敗が他に影響しない設計。

### Internal / Refactor
- 各モジュールはテスト差し替えを考慮した設計（例: news_collector._urlopen をモック可能）。
- 一部モジュール（strategy, execution, monitoring）の __init__.py はプレースホルダとして存在（将来的な拡張用）。

### Known limitations / TODO
- pipeline モジュールに品質チェック（quality モジュール）との統合は想定されているが、現状は品質チェック呼び出しコードの統合や追加の ETL ジョブ（財務・カレンダーの完全な ETL 実装など）が必要。
- strategy / execution / monitoring の具体的な戦略・注文送信ロジックは未実装（パッケージ構造は用意済み）。
- 単体テスト・統合テストに関する記述は現コードからは確認できないため、テストの整備が必要。

---

（注）本 CHANGELOG は提供されたソースコードから推測して作成しています。実際のリリースノートやリリース日、バージョン方針はプロジェクトの正式な記録に準じてください。