# CHANGELOG

すべての変更は「Keep a Changelog」（https://keepachangelog.com/）に準拠して記録しています。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

### Added
- 開発中のタスクや未リリースの修正・改善点をここに記載します（現時点では特記事項なし）。

### Known issues / To do
- run_prices_etl の戻り値仕様（(取得数, 保存数)）が実装上不整合になっています。現行実装は最後に `return len(records),` のように 1 要素のタプルしか返さないため、呼び出し側で 2 値アンパックを期待している場合にエラーになります — 修正が必要です。
- strategy/execution パッケージはプレースホルダ（空 __init__）のままです。戦略ロジックや発注実装は今後追加予定。

---

## [0.1.0] - 2026-03-17

### Added
- 初回リリース: KabuSys v0.1.0
  - パッケージのバージョンは `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` を設定。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加（settings インスタンスを提供）。
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づく .env 自動ロード（優先順位: OS 環境変数 > .env.local > .env）。
  - .env の行解析は export プレフィックス、クォート内部のエスケープ、インラインコメント処理などを考慮する堅牢なパーサを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 設定プロパティ（J-Quants、kabuステーション、Slack、DB パス、環境名検証、ログレベル検証、is_live/is_paper/is_dev ヘルパー）を提供。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API ベース実装（トークン取得 / リフレッシュ、データ取得、ページネーション対応）。
  - レート制限器（固定間隔スロットリング）による 120 req/min の制御を実装。
  - リトライロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）を実装。429 の場合は Retry-After を尊重。
  - 401 受信時のトークン自動リフレッシュを 1 回だけ行う安全な実装（無限再帰回避）。
  - id_token のモジュールレベルキャッシュを導入し、ページネーション間で共有。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期 BS/PL、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等性を確保する ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ変換ユーティリティ `_to_float`, `_to_int` を用意し、入力の健全性を担保。
  - 取得時刻（fetched_at）を UTC ISO 形式で記録し、Look-ahead Bias の防止に配慮。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集し、前処理・正規化したうえで raw_news テーブルへ冪等保存する機能を実装。
  - defusedxml を利用して XML Bomb 等から保護。
  - SSRF 対策を多層で実装:
    - URL スキーム検証（http/https のみ許可）
    - リダイレクト時にもスキーム/ホスト検証を行う専用ハンドラ（_SSRFBlockRedirectHandler）
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば拒否
    - DNS 解決を行い A/AAAA レコードをチェック（解決失敗は安全側に扱う）
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後の再チェックによりメモリ DoS / GZip bomb を軽減。
  - URL 正規化でトラッキングパラメータ（utm_*, fbclid 等）を除去し、正規化後の SHA-256（先頭32文字）を記事 ID として冪等性を保証。
  - テキスト前処理（URL 除去・空白正規化）。
  - DB 保存:
    - save_raw_news: チャンク INSERT + TRANSACTION + INSERT ... RETURNING id により新規挿入 ID を正確に収集。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンクして保存（ON CONFLICT DO NOTHING、RETURNING で挿入数算出）。
  - 銘柄コード抽出ロジック（4 桁数字の候補を正規表現で抽出し、known_codes に基づきフィルタ）。
  - run_news_collection: 複数ソースからの収集を統合し、失敗しても他ソースへ影響を与えない堅牢なジョブ。

- DuckDB スキーマ & 初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層に対応した詳細な DDL を提供。
  - テーブル一覧: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等。
  - 運用上有用なインデックス群を作成（銘柄×日付、ステータス検索など）。
  - init_schema(db_path) でディレクトリ自動作成→接続→DDL 実行（冪等）。
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない点に注意）。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日からの差分取得）を行う ETL 支援ユーティリティを提供。
  - ETLResult dataclass により ETL の結果・品質問題・エラーを構造化して返却可能。
  - 市場カレンダー調整ロジック（非営業日は直近の営業日に調整）を実装。
  - raw_prices/raw_financials/market_calendar の最終取得日取得ユーティリティ。
  - run_prices_etl の骨組みを実装（差分算出、J-Quants からの取得、保存の呼出し）。※ただし現状戻り値実装に不整合あり（Known issues を参照）。

### Security
- RSS XML パースに defusedxml を使用して XML 関連の脅威に対策。
- RSS フェッチでのリダイレクト時にスキーム検査・プライベートアドレス検査を行い SSRF を低減。
- .env 読み込み時のファイル入出力エラーは警告ログに記録し、プロセスを停止させない設計。

### Performance / Reliability
- API クライアントにレートリミッタ・リトライ・トークンキャッシュを組み合わせて信頼性を向上。
- DuckDB へのバルク挿入をチャンクに分割しトランザクション単位で処理、INSERT ... RETURNING により正確な挿入数算出。
- RSS 取得時に Content-Length および実際読み込みバイト数を検査して大規模レスポンスを早期に拒否。

### Fixed
- （初回リリースのため該当なし）

### Known issues
- run_prices_etl の戻り値が（取得数, 保存数）を返す旨のドキュメントと実装が一致していません。実装は現状 `return len(records),` のようになっており 2 要素タプルではないため、呼び出し側で受け取りエラーが発生する可能性があります。修正が必要です。
- strategy / execution の具体実装は未提供（空パッケージ）。実運用前に戦略実装・発注実装を追加してください。

---

作業予定 / 次回リリース案
- run_prices_etl の戻り値修正と単体テスト追加。
- strategy / execution モジュールの実装と統合テスト。
- quality モジュール（ETL 品質チェック）の実装・連携強化。
- CI（自動テスト）・ロギング/メトリクスの整備・ドキュメント充実。

もし CHANGELOG に特に追加してほしい観点（例: 変更履歴に含めたいコミットや設計上の決定、優先的に伝えたい既知の不具合など）があれば教えてください。必要に応じて更新します。