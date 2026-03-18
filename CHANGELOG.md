# Changelog

すべての重要な変更点を記録します。フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-03-18

### Added
- パッケージの初期リリース。トップレベルのパッケージ情報を追加
  - kabusys.__version__ = "0.1.0"
  - kabusys.__all__ に主要サブパッケージを公開（data, strategy, execution, monitoring）。
- 環境設定管理モジュール（kabusys.config）
  - プロジェクトルートを .git / pyproject.toml から自動検出する機能を実装（パッケージ配布後も動作する設計）。
  - .env / .env.local の自動ロード（優先度: OS 環境 > .env.local > .env）。自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env 行パーサー（export 句・クォート・インラインコメント・エスケープに対応）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の設定プロパティと入力検証（必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の許容値検証）を実装。
- データ取得/保存 - J-Quants クライアント（kabusys.data.jquants_client）
  - J-Quants API 呼び出しラッパーを実装。ページネーション、JSON デコード、エラーハンドリングをサポート。
  - レート制御（固定間隔スロットリング）を実装（120 req/min）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）と 401 受信時の自動トークンリフレッシュ（1 回のリフレッシュ試行）。
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar 等の取得関数（ページネーション対応）。
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を追加。INSERT ... ON CONFLICT DO UPDATE による重複排除と fetched_at 記録。
  - 型変換ユーティリティ（_to_float, _to_int）を追加。
- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード取得（fetch_rss）と記事前処理・正規化機能を実装。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）、記事 ID を正規化 URL の SHA-256（先頭32文字）で生成。
  - RSS パースで defusedxml を利用し XML 攻撃に対する保護。
  - SSRF 対策: リダイレクト時のスキーム/ホスト検証、プライベート IP 判定、許可スキームは http/https のみ。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）、gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - raw_news テーブルへの冪等保存（save_raw_news）はチャンク化（INSERT ... RETURNING）と単一トランザクションで実行、実際に挿入された ID リストを返す。
  - 記事と銘柄の紐付け（news_symbols）を一括挿入するユーティリティ（_save_news_symbols_bulk, save_news_symbols）。
  - テキストからの銘柄コード抽出（extract_stock_codes、4桁数字のみ、known_codes によるフィルタ）。
  - run_news_collection により複数ソースの安全な収集ワークフローを提供（ソース単位での例外隔離）。
- DuckDB スキーマ定義モジュール（kabusys.data.schema）
  - Raw 層の DDL を定義（raw_prices, raw_financials, raw_news, raw_executions の定義を含む）。
  - 初期化用 DDL 管理の土台を追加。
- 研究（Research）モジュール（kabusys.research）
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 calc_forward_returns（複数ホライズンを一度に取得、データ不足時は None を返す）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ、ランク関数 rank を内部提供）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム calc_momentum（1M/3M/6M リターン、MA200 乖離）。
    - ボラティリティ / 流動性 calc_volatility（20日 ATR、ATR 比率、20日平均売買代金、出来高比率）。
    - バリュー calc_value（raw_financials の最新財務データを用いた PER / ROE 計算）。
  - 結果は (date, code) キーの辞書リストとして返却する設計で、本番の発注 API 等にはアクセスしないことを明記。
- パッケージの公開 API（kabusys.research.__init__）に主要関数をエクスポート。
- その他
  - strategy/ および execution/ パッケージのプレースホルダ（__init__.py）を追加（将来の拡張準備）。

### Changed
- 初期リリースのため特別な既存機能の変更はなし。

### Fixed
- 初期リリースのため特別なバグ修正はなし。

### Security
- 外部入力（XML/RSS/URL）処理に対するセキュリティ対策を導入
  - defusedxml による XML パース（XML Bomb 等への対策）。
  - SSRF 対策: URL スキーム検証、リダイレクト先の事前検査、ホストのプライベート IP 判定。
  - RSS レスポンスの最大受信サイズ制限（メモリ DoS 対策）。
  - URL 正規化でトラッキングパラメータを除去（意図しない識別子の漏洩防止）。

### Performance
- J-Quants API 呼び出しで固定間隔レートリミッタを適用し、API レート制限を遵守。
- ニュース保存でチャンク化されたバルク INSERT を採用し、DB 操作のオーバーヘッドを低減。
- DuckDB 側のウィンドウ関数を活用してファクター計算・将来リターン計算を SQL レイヤで効率化。

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings から取得され、未設定時は ValueError を発生させます。
- .env 自動読込の挙動:
  - OS 環境変数が最優先。プロジェクトルートが特定できない場合は自動ロードをスキップします。
  - テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマは data/schema.py の DDL を参照してください。必要に応じてマイグレーション・初期化スクリプトを用意することを推奨します。
- 研究用 API（kabusys.research/*）は外部 API に依存せず、prices_daily / raw_financials テーブルだけを参照する想定です。本番口座や発注 API は呼び出しません。

---

今後のリリースでは strategy / execution / monitoring の具体実装や、スケジューラ・運用監視機能、追加のデータソース対応を予定しています。もし CHANGELOG に追記してほしい具体的な点（例: 日付修正、リリース名の変更、より詳細なカテゴリ分け）があれば教えてください。