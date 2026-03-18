# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、重大度 (Added, Changed, Fixed, Security, etc.) に分類しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-18
初回リリース。日本株向け自動売買・データプラットフォーム「KabuSys」の基盤モジュールを追加。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にバージョン情報と公開サブパッケージ一覧を追加 (バージョン 0.1.0)。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env/.env.local ファイルからの自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用途）。
    - 高度な .env パーサ（export 形式、クォート内のエスケープ、インラインコメント処理など）。
    - Settings クラスで必要な設定値をプロパティ経由で取得（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等）。
    - KABUSYS_ENV / LOG_LEVEL の値検証と is_live / is_paper / is_dev ヘルパー。

- J-Quants データクライアント
  - src/kabusys/data/jquants_client.py
    - J-Quants API からのデータ取得（株価日足 / 財務データ / 取引カレンダー）。
    - 固定間隔ベースのレートリミッタ実装（120 req/min を遵守）。
    - ページネーション対応（pagination_key を利用）。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx 対応）。
    - 401 応答時の自動トークンリフレッシュ（1 回のみ再試行、無限再帰防止）。
    - 取得時刻 (fetched_at) を UTC で記録し Look-ahead Bias のトレースを可能に。
    - DuckDB への保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を提供。INSERT は ON CONFLICT DO UPDATE で冪等性を担保。
    - 型変換ユーティリティ (_to_float, _to_int) を実装し不正値に寛容に対応。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィードからニュースを取得して raw_news に保存する一連処理を実装。
    - 安全設計:
      - defusedxml を利用して XML Bomb 等を防御。
      - SSRF 対策: URL スキーム検証、プライベート IP/ホストの検査、リダイレクト時の検査ハンドラ実装。
      - レスポンスサイズ上限 (MAX_RESPONSE_BYTES) の導入（受信・解凍後ともチェック）。
      - gzip 圧縮対応（解凍失敗は安全にスキップ）。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ先頭32文字で生成し冪等性を担保（utm_* 等のトラッキングパラメータ除去、クエリソート、フラグメント除去）。
    - テキスト前処理（URL 除去、空白正規化）。
    - raw_news の冪等保存（INSERT ... ON CONFLICT DO NOTHING RETURNING id）と、news_symbols への銘柄紐付けをサポート（チャンク挿入、トランザクション管理）。
    - 銘柄コード抽出ユーティリティ（4桁数字パターンに対して known_codes フィルタを適用）。

- DuckDB スキーマ初期化
  - src/kabusys/data/schema.py
    - Raw 層テーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions など）。DataSchema.md に基づく 3 層構成（Raw / Processed / Feature / Execution）の土台を用意。
    - スキーマは CREATE TABLE IF NOT EXISTS を使用し安全に初期化可能。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日移動平均乖離）、ボラティリティ（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、バリュー（PER, ROE）を計算する関数を追加。
    - DuckDB の prices_daily / raw_financials テーブルのみ参照し外部 API へはアクセスしない設計。
    - データ不足に対しては None を返す挙動を明確化。
    - スキャン範囲バッファを採用して週末/祝日を吸収（カレンダー日で余裕を持たせる）。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、1 クエリで取得）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ、ランク計算は平均ランク tie 処理あり）。
    - 基本統計量 factor_summary（count/mean/std/min/max/median）。
    - rank ユーティリティ（同順位は平均ランク、浮動小数丸め対策あり）。
    - 設計上 pandas 等の外部ライブラリに依存せず標準ライブラリと DuckDB のみで動作。

  - src/kabusys/research/__init__.py に主要関数をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Changed
- （初回リリースのため過去変更はなし）

### Fixed
- （初回リリースのため修正履歴はなし）

### Security
- news_collector:
  - SSRF 対策（プライベート IP/ホスト除外、スキーム検証、リダイレクト検査）。
  - defusedxml による XML パース防御。
  - レスポンスサイズ制限でメモリ DoS を緩和。

- jquants_client:
  - トークン自動リフレッシュ時に無限再帰を防止するフラグ (allow_refresh) を導入。

### Performance
- jquants_client:
  - レートリミッタを導入し API レート制限に従うことでスロットリング制御を明確化。
  - ページネーションで pagination_key を再利用し効率的に全件取得。

- research:
  - 将来リターンやファクター計算で可能な限り単一 SQL を利用して DuckDB 側で集計を行い Python 側のループを削減。

### Compatibility / Notes
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装を目指しているため、既存の pandas ベースのツールとは API/戻り値形式で差異がある可能性があります。
- settings から必須値を取得するプロパティは未設定時に ValueError を送出します。リポジトリ内の .env.example を参考に設定してください。
- news_collector は defusedxml を利用するため、実行環境に該当パッケージ（あるいは同等の XML の安全パーサ）が必要です。
- DuckDB スキーマの定義は schema.py の DDL を参照してください。既存 DB に対する変更は CREATE TABLE IF NOT EXISTS ベースのため安全に実行できますが、スキーマの互換性変更時はマイグレーションが必要になります。

### Known limitations
- 一部の機能（例: PBR・配当利回り等のバリューファクター、Strategy / Execution の詳細実装）は現時点で未実装またはスケルトンのままです（モジュール __init__.py が空など）。
- research.calc_* 関数は営業日ベース（連続レコード数）でホライズンを扱う設計のため、カレンダー日と厳密に一致しない場合があります（設計上の注記あり）。

---

今後のリリースでは、Strategy/Execution 層の実装強化、テスト追加、CI/デプロイの整備、及びさらなるファクタの追加・チューニングを予定しています。