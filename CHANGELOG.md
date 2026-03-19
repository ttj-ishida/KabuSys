KEEP A CHANGELOG 準拠 — CHANGELOG.md
※コードベースの内容から推測して作成しています。リリース日や文言は推測値です。

全般的な注意
- 本ファイルは Keep a Changelog の形式に従います。
- バージョン番号はパッケージ内の __version__ = "0.1.0" に基づきます。

Unreleased
---------
- なし

[0.1.0] - 2026-03-19
-------------------
Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報を公開するための __init__.py を追加（__version__ = "0.1.0"）。__all__ で主要サブパッケージを明示。
- 環境設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動ロードする仕組みを追加。
  - .env 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - .env 行パーサーを実装（# コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメント処理等）。
  - Settings クラスを追加し、以下の設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV（development/paper_trading/live のバリデーション）、LOG_LEVEL のバリデーション
    - 環境判定ヘルパー: is_live / is_paper / is_dev
  - 必須キー未設定時に ValueError を送出する _require ユーティリティを提供。
- データ取得・保存: J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API 用クライアントを実装。
  - レート制限対応: 固定間隔スロットリングを行う内部 RateLimiter（120 req/min）。
  - リトライロジック: 指数バックオフ、最大3回、408/429/5xx に対する再試行。429 の場合は Retry-After ヘッダを尊重。
  - 401 エラー時の自動トークンリフレッシュ（1 回のみ）をサポート。リフレッシュは get_id_token 経由。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB への冪等保存関数を実装:
    - save_daily_quotes -> raw_prices テーブル（ON CONFLICT DO UPDATE）
    - save_financial_statements -> raw_financials テーブル（ON CONFLICT DO UPDATE）
    - save_market_calendar -> market_calendar テーブル（ON CONFLICT DO UPDATE）
  - データ型変換ユーティリティ _to_float / _to_int を追加（空値・不正値を安全に None に変換）。
  - fetched_at を UTC で記録して Look-ahead Bias を追跡可能にする設計。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集パイプラインを実装:
    - fetch_rss: RSS 取得、XML パース（defusedxml 使用）と記事抽出（title, description/content:encoded, link/guid, pubDate）
    - preprocess_text: URL 除去、空白正規化
    - URL 正規化と記事 ID 生成 (_normalize_url / _make_article_id): トラッキングパラメータ削除、小文字化、フラグメント削除、クエリソート。SHA-256 の先頭32文字を記事IDに使用。
    - SSRF 対策: リダイレクト時の検査用ハンドラ、ホストのプライベート IP 判定、スキーム検証（http/https のみ許可）。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検証（Gzip bomb 対策）。
    - XML パース失敗や不正コンテンツ時は警告ログを出力して安全にスキップ。
    - save_raw_news: チャンク化された INSERT ... RETURNING による冪等保存（トランザクションまとめて実行）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付け保存（重複排除、チャンク挿入、INSERT ... RETURNING による実際に挿入された件数返却）。
    - extract_stock_codes: テキスト内の 4 桁数字抽出と known_codes によるフィルタリング（重複除去）。
    - run_news_collection: 複数 RSS ソースからの収集ジョブ、各ソースを独立して処理し失敗を分離、既知銘柄との紐付け処理を実行。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを追加。
- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataSchema に基づく初期テーブル DDL の追加（Raw / Processed / Feature / Execution 層の設計に向けた定義）。
  - raw テーブル用の DDL 断片を実装（raw_prices, raw_financials, raw_news, raw_executions 等）。
  - テーブル定義には型制約・チェック制約・PRIMARY KEY を含む。
- リサーチ / ファクター計算 (kabusys.research)
  - feature_exploration モジュール:
    - calc_forward_returns: 指定基準日から各ホライズン（デフォルト 1,5,21）について将来リターンを一括 SQL で計算。入力検証（horizons の範囲チェック）あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（None/NaN 排除、3 件未満で None を返す）。
    - rank: 同順位は平均ランクとする実装（丸めによる ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
    - 標準ライブラリのみで実装（pandas 非依存）で、DuckDB の prices_daily テーブル参照を想定。
  - factor_research モジュール:
    - calc_momentum: mom_1m / mom_3m / mom_6m と 200 日移動平均乖離率（ma200_dev）を計算。データ不足時は None。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、avg_turnover、volume_ratio を計算。true_range 計算で NULL 伝播を適切に制御。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算（EPS が 0/欠損 は None）。DuckDB 側で最新財務レコードを ROW_NUMBER により取得。
    - スキャン範囲は週末・祝日を考慮した余裕を持たせた calendar-day バッファを使用。
  - research パッケージの __init__ で主要関数をエクスポート（zscore_normalize を含む）。
- API デザイン / 安全策
  - 重要操作（ネットワーク、DB 書き込み）に対して詳細なログ出力を実施（logger を利用）。
  - DB 書き込みは可能な限り冪等化（ON CONFLICT）やトランザクションでまとめて実行。
  - 外部入力（RSS, URL）に対する複数の防御（SSRF 判定、スキームチェック、受信サイズ制限、defusedxml）を導入。
- ユーティリティ
  - 各モジュールに入力検証・エラーハンドリングを実装（例: horizons の範囲チェック、env 値バリデーション、_to_int の小数切捨て防止など）。

Changed
- 初版リリースのため該当なし。

Fixed
- 初版リリースのため該当なし。

Security
- RSS/XML 解析に defusedxml を使用して XXE 等の攻撃を回避。
- RSS フェッチ時にリダイレクト先のスキームとホストを検証し、内部ネットワーク（プライベート IP / ループバック等）へのアクセスを拒否（SSRF 対策）。
- URL 正規化でトラッキングパラメータを除去し、一意の ID を安全に作成。

Compatibility / Breaking Changes
- 初版のため互換性破壊は無し。

Notes / Limitations
- research モジュールは pandas 等の外部ライブラリに依存しない実装だが、大量データ処理の性能は将来的な見直し対象。
- calc_value では PBR・配当利回りは未実装（コメントとして明記）。
- news_collector の初期既知銘柄セット（known_codes）は呼び出し側で供給する必要がある。
- DuckDB スキーマ断片はファイル内で定義されているが、実際のスキーマ作成コード（CREATE TABLE 実行ラッパー）の導出は利用側で行う想定。

Authors
- kabusys 開発チーム（コードベースのコメントと実装に基づき推測して記載）

References
- パッケージ内の docstring やコメント（DataPlatform.md / StrategyModel.md / DataSchema.md 参照想定）に基づき設計方針を反映。

（以上）