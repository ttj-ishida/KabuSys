# CHANGELOG

すべての注目すべき変更点をここに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

現在のバージョン: 0.1.0 - 初期リリース

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-17
初期リリース。日本株自動売買プラットフォームのコア機能を実装しました。

### 追加
- パッケージ構成を追加
  - モジュール: kabusys, kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring（公開 API を __all__ で定義）
  - バージョン情報: __version__ = "0.1.0"

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルート判定は .git / pyproject.toml を探索）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env/.env.local の優先度制御（OS 環境変数を保護する protected 機能）。
  - .env 行パーサを実装（export プレフィックス、クォートやエスケープ、インラインコメント対応）。
  - 必須変数チェック関数 _require と Settings クラスを提供（J-Quants, kabu, Slack, DB パス等のプロパティを含む）。
  - KABUSYS_ENV / LOG_LEVEL の入力値検証（許容値チェック）と便宜プロパティ（is_live, is_paper, is_dev）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本的な GET/POST リクエストの実装（JSON デコード、タイムアウト、ヘッダ設定）。
  - レート制御（_RateLimiter）: 120 req/min を固定間隔スロットリングで実施。
  - リトライロジック（指数バックオフ, 最大 3 回）。408/429/5xx に対する再試行処理。429 の Retry-After 優先。
  - 401 Unauthorized を検出した場合、自動でトークンをリフレッシュして 1 回だけ再試行。
  - ID トークンの取得関数 get_id_token（refresh token を使用）。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（OHLCV）
    - fetch_financial_statements（四半期 BS/PL）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB へ冪等保存する save_* 関数:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE により上書き保存
    - save_financial_statements: raw_financials テーブルへ冪等保存
    - save_market_calendar: market_calendar テーブルへ冪等保存
  - データ型変換ユーティリティ (_to_float, _to_int) を用意（不正値は None）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードの取得、記事整形、DuckDB への保存ワークフローを実装。
  - 安全対策:
    - defusedxml を利用した XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストのプライベートアドレス判定、リダイレクト時の検査用ハンドラ（_SSRFBlockRedirectHandler）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - URL 正規化とトラッキングパラメータ除去（utm_ 等）。
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
  - fetch_rss: RSS をパースして NewsArticle リストを返却（異常時はログと空リスト）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を利用し、新規挿入された記事IDを返す。チャンク挿入と 1 トランザクションで処理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク挿入・トランザクションで実行（ON CONFLICT DO NOTHING）。
  - テキスト前処理（URL除去、空白正規化）と銘柄コード抽出（4桁数字、重複除去、known_codes フィルタ）。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - 生データ層、加工層、特徴量層、実行層それぞれのテーブル DDL を定義。
  - 主なテーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など。
  - 制約（PRIMARY KEY, CHECK, FOREIGN KEY）とインデックス（頻出クエリ向け）を定義。
  - init_schema(db_path) でディレクトリ作成、全DDL とインデックスを冪等に実行して接続を返す。get_connection() で既存DBへ接続可能。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（差分取得）と保存、品質チェック（quality モジュール呼び出し想定）のフレームワークを実装。
  - ETLResult データクラス: 実行メタデータ、品質問題、エラー一覧を保持し、辞書化可能。
  - DB の最終取得日取得ヘルパ（get_last_price_date, get_last_financial_date, get_last_calendar_date）を提供。
  - 市場カレンダーに基づく取引日調整ヘルパ（_adjust_to_trading_day）。
  - run_prices_etl: 差分算出（最終取得日 - backfill）に基づく取得と保存のロジック（backfill デフォルト 3 日）。（注: ファイル末尾で実装途中の戻り値・処理継続の痕跡あり）

### 改善（設計上の注意・品質向上）
- 各所で冪等性を考慮した DB 操作（ON CONFLICT/DO UPDATE/DO NOTHING, INSERT ... RETURNING）を採用。
- ネットワーク周りでリトライ、レート制御、タイムアウトを包括的に実装。
- セキュリティ面で外部入力（RSS / URL / XML / .env）に対する防御（スキーム検証、プライベートIP拒否、Gzip/Content-Length 制限、defusedxml、.env パースの堅牢化）を実装。

### 既知の制限 / 追加実装予定
- pipeline.run_prices_etl の末尾がファイル断片で切れている箇所があり、戻り値の整合性（現在は途中で切れている）が要確認・補完が必要。
- quality モジュールの具体的な実装は本コードベースには含まれていない（pipeline は quality.QualityIssue を参照する設計）。
- strategy、execution、monitoring パッケージ内の具象実装は未提供（__init__.py は空）。
- 単体テスト・統合テストや CI ワークフロー、ドキュメント（DataPlatform.md / DataSchema.md 参照箇所）の追加を推奨。

### セキュリティ
- RSS/HTTP 関連の SSRF、防御策を追加（_SSRFBlockRedirectHandler、_is_private_host 判定、スキーム検証）。
- XML パースに defusedxml を使用して XML ベースの脅威を軽減。
- .env 読み込みで OS 環境変数を保護する protected 機能を実装。

---

今後のリリース予定:
- pipeline の残処理・品質チェックの統合
- strategy / execution の実装（発注ロジック、kabuステーション API 統合）
- モニタリング・アラート（Slack 通知等）の実装
- 単体テスト、静的型チェックの追加

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴と差異がある場合は適宜調整してください。）