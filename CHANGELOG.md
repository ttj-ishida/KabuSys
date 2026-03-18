CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

## [Unreleased]

なし

## [0.1.0] - 2026-03-18

### 追加
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報を src/kabusys/__init__.py にて設定（__version__ = "0.1.0"）。
  - パブリックサブパッケージとして data, strategy, execution, monitoring をエクスポート。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
  - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を検索（CWD 非依存）。
  - .env/.env.local の優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加（テスト用途）。
  - export KEY=val 形式、クォートやエスケープ、インラインコメント対応のパーサ実装。
  - 環境変数の必須チェック (_require) と型・範囲検証（KABUSYS_ENV、LOG_LEVEL 等）。
  - 設定取得用の Settings クラスを提供（J-Quants トークン、kabu API などのプロパティを含む）。

- データ取得クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。エンドポイント: 株価日足、財務データ、取引カレンダー等。
  - レート制御: 固定間隔スロットリング（_RateLimiter）で 120 req/min を厳守。
  - 再試行ロジック: 指数バックオフ（最大 3 回）、408/429/5xx に対するリトライ。
  - 401 発生時は ID トークンを自動リフレッシュして 1 回リトライする仕組みを導入。
  - ページネーション対応（pagination_key の追跡）。
  - DuckDB への保存関数（save_daily_quotes、save_financial_statements、save_market_calendar）を実装し、ON CONFLICT による冪等化を実現。
  - データ型変換ユーティリティ (_to_float, _to_int) を実装（不正値を安全に None に変換）。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード収集のフルスタック実装（フェッチ → 前処理 → DB 保存 → 銘柄紐付け）。
  - セキュリティ対策:
    - defusedxml を用いた XML パースで XML Bomb 等に対処。
    - SSRF 対策: リダイレクト監視ハンドラ（_SSRFBlockRedirectHandler）と事前ホスト検査（_is_private_host）。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES、デフォルト 10 MB）によるメモリ DoS 対策。gzip 解凍後もサイズを検証。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url）、正規化 URL の SHA-256（先頭32文字）で記事 ID を生成。
  - テキスト前処理（URL 除去・空白正規化）と RFC 準拠の pubDate パース（_parse_rss_datetime）。
  - raw_news への冪等保存（INSERT ... ON CONFLICT DO NOTHING + RETURNING）とチャンク挿入。トランザクション管理（commit/rollback）。
  - news_symbols（記事⇄銘柄紐付け）への一括保存ユーティリティ（_save_news_symbols_bulk）と単件保存（save_news_symbols）。
  - ニュース本文からの銘柄コード抽出機能（extract_stock_codes）。既知コード集合によるフィルタリングを想定。
  - run_news_collection により複数ソースを順次収集し、個々のソースの失敗が他ソースに影響しない設計。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - DataSchema に基づく 3 層構造のテーブル定義（Raw / Processed / Feature / Execution 層）。
  - Raw Layer DDL の実装（raw_prices, raw_financials, raw_news, raw_executions 等の定義）。（スキーマ定義は安全チェック（NOT NULL / CHECK / PRIMARY KEY）を含む）

- リサーチ / ファクター計算（src/kabusys/research/）
  - feature_exploration.py:
    - 将来リターン計算 calc_forward_returns（DuckDB の prices_daily を参照）。複数ホライズン対応（デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンランク相関、ties の扱い、最小サンプル検査）。
    - factor_summary（count/mean/std/min/max/median）と rank 関数を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - factor_research.py:
    - Momentum, Volatility, Value などの定量ファクターを計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - DuckDB ウィンドウ関数を活用した高速集計（LAG/AVG/COUNT OVER を利用）。
    - データ不足時の None ハンドリングや最小データ要件の検査（例: ma200 は 200 行未満で None）。
  - research パッケージ __all__ に主要ユーティリティを公開（zscore_normalize を含む外部ユーティリティ参照）。

### 変更
- （初回リリースのため過去バージョンからの変更はありません）

### 修正
- （初回リリースのため既知のバグ修正履歴はありません）

### セキュリティ
- ニュース収集における SSRF 対策、XML パースの安全化（defusedxml）、レスポンスサイズ検査など、外部データ取り込みに関する複数の防御層を導入。

### 備考 / 設計上の注意
- research モジュールは外部ライブラリ（pandas 等）へ依存せずに実装されており、DuckDB の prices_daily / raw_financials テーブルのみを参照する設計で、実稼働の発注 API 等にはアクセスしないことを明示している（Look-ahead Bias 回避）。
- J-Quants クライアントはトークンキャッシュをモジュールレベルで保持し、ページネーションや複数呼び出し間で共有する設計。トークンリフレッシュは 401 に対して 1 回のみ自動で行う。
- .env パーサは export キーワード、クォート内部のエスケープ、インラインコメント等多くのケースに対応しているが、特殊な .env 構成を使用する場合は挙動確認を推奨。

署名
----
このリリースは kabusys パッケージの初期公開版です。今後のバージョンでは API（関数署名や返却フォーマット）や DB スキーマに変更が入る可能性があります。アップグレード時は CHANGELOG とドキュメントの差分にご注意ください。