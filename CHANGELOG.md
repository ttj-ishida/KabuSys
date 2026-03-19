# Changelog

すべての注目すべき変更はここに記録します。  
このファイルは「Keep a Changelog」規約に従って作成されています。

現在のバージョン: 0.1.0

[Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。日本株向け自動売買／データプラットフォームのコア機能を提供します。主な追加点は以下の通りです。

### 追加
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。サブパッケージとして data, strategy, execution, monitoring を公開。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を導入（プロジェクトルートは .git または pyproject.toml から検出）。
  - .env のパースに対応:
    - コメント行、先頭 export キーワード対応、シングル/ダブルクォート内のエスケープ対応。
    - 行内コメントの扱い（クォートの有無に応じた適切な取り扱い）。
    - 読み込み失敗時の警告出力。
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env と .env.local の優先順位（OS環境変数 > .env.local > .env）。.env.local は上書き（override=True）で適用。
  - Settings クラスを提供し、必要な環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_* 等）にアクセスするプロパティを定義。
  - env 値（KABUSYS_ENV）および LOG_LEVEL のバリデーション（許容値の検査）、便宜的な is_live / is_paper / is_dev プロパティ。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティ（_request）を実装。機能:
    - レート制限（120 req/min）を固定間隔スロットリングで遵守する RateLimiter。
    - リトライ／指数バックオフ（最大試行 3 回、対象ステータス 408/429/5xx）。429 の場合は Retry-After ヘッダ優先。
    - 401 Unauthorized を検出した場合、リフレッシュトークンで id_token を自動更新して 1 回だけ再試行。
    - ページネーション対応（pagination_key を用いた連続取得）。
    - JSON デコードエラーやネットワークエラーの適切なハンドリングとログ出力。
    - id_token のモジュールレベルキャッシュを保持（ページネーション間で共有）。
  - データ取得関数:
    - fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar（ページネーション対応）。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes（raw_prices）、save_financial_statements（raw_financials）、save_market_calendar（market_calendar）を実装。いずれも ON CONFLICT DO UPDATE による冪等性を保証。
  - ユーティリティ変換関数: _to_float, _to_int（厳密な変換ルールを採用）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集と DB 保存の統合機能を実装（run_news_collection）。
  - セキュリティ / ロバストネス:
    - defusedxml を用いた XML パース（XML Bomb 等に対する安全対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト時にスキームとホストの検証を行うカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストでないかを検査（DNS 解決で A/AAAA をチェック）。DNS 解決失敗は安全側に倒す実装。
    - レスポンスサイズ上限の導入（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ再チェック（Gzip bomb 対策）。
    - 不正スキームの link/guid をスキップ。
  - フィード処理:
    - URL 正規化（トラッキングパラメータ削除、キーソート、フラグメント除去）と記事ID生成（SHA-256 の先頭 32 文字）。
    - テキスト前処理（URL 除去、空白正規化）。
    - pubDate の RFC 2822 パース（タイムゾーン処理: UTC に標準化、失敗時は現在時刻にフォールバック）。
  - DB 保存の最適化:
    - save_raw_news はチャンク挿入（_INSERT_CHUNK_SIZE）と INSERT ... RETURNING id を使用し、新規登録された記事IDを返す。
    - save_news_symbols / _save_news_symbols_bulk により記事と銘柄紐付けをチャンク化して一括挿入（ON CONFLICT DO NOTHING、トランザクションでまとめる）。
  - 銘柄コード抽出ユーティリティ（extract_stock_codes）: 4桁の数字を抽出し、既知の銘柄集合でフィルタリング・重複除去。

- データスキーマ（kabusys.data.schema）
  - DuckDB 用の DDL 定義を導入（Raw 層を中心に定義）。
  - raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義（PRIMARY KEY、CHECK 制約、fetched_at カラムなど）。

- リサーチ / ファクター計算（kabusys.research）
  - feature_exploration:
    - calc_forward_returns（複数ホライズンの将来リターンを一度に取得）、calc_ic（スピアマンのランク相関）、rank（同順位は平均ランク）、factor_summary（基本統計量）。
    - 標準ライブラリのみでの実装方針（pandas 等に依存しない）。
  - factor_research:
    - calc_momentum（mom: 1m/3m/6m、MA200 乖離率）、calc_volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）、calc_value（PER, ROE を raw_financials と組合せて計算）。
    - データは DuckDB の prices_daily / raw_financials のみ参照。結果は (date, code) をキーとする dict のリスト形式で返す。
  - research.__init__ で主要関数を再エクスポート（zscore_normalize を含む）。

### 変更
- （初版のため過去からの変更は無し）

### 修正（バグ修正）
- （初版のため過去からの修正は無し）

### セキュリティ
- RSS パーサに defusedxml を採用し、SSRF 対策、レスポンスサイズ制限、gzip 解凍後サイズチェックなど複数の防御層を追加。
- J-Quants クライアントは認証トークンの自動更新と最大再試行ロジックにより認証関連の安定性を向上。

### 注意事項 / 既知の制約
- DuckDB スキーマは DataSchema.md に基づくが、スキーマ定義（execution 層など）は将来的に拡張される可能性あり（本リリースでは一部を定義）。
- news_collector の extract_stock_codes は単純に 4 桁数字を抽出する実装のため、文脈判定や企業名からの抽出は行わない（既知コードセットを与える必要あり）。
- research モジュールは prices_daily / raw_financials テーブルの整備されたデータを前提としており、データ不足の銘柄は None を返すことがある。

---

将来のリリースでは次のような改善を計画しています:
- schema の Execution 層・Feature 層の追加定義とマイグレーションユーティリティ
- strategy / execution サブパッケージの具現化（発注・ポジション管理の実装）
- パフォーマンス最適化（バルク処理、並列フェッチ等）
- テストカバレッジの拡充と CI ワークフローの整備

（必要であれば、上記の各変更点についてさらに詳細な説明や関連ファイル/関数の一覧を追加します。）