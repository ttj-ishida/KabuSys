# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-18
初期リリース。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。公開されたサブパッケージ:
    - data, strategy, execution, monitoring（__all__ に含む）。
- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルート検出: .git または pyproject.toml を起点に探索して自動ロードを行う（CWD に依存しない設計）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効にするフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサの強化:
    - コメント行や空行の無視、`export KEY=val` 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなしの値に対するインラインコメント判定（直前が空白/タブの場合に # をコメントとして扱う）。
  - 環境変数取得ユーティリティ Settings を提供:
    - 必須値の取得（_require により未設定は ValueError）。
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB/SQLite）など主要設定をプロパティで公開。
    - KABUSYS_ENV と LOG_LEVEL の値検証（有限セットのみ許容）。
    - is_live / is_paper / is_dev の補助プロパティ。
- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制限遵守（120 req/min）。
    - リトライ処理（指数バックオフ、最大 3 回）。HTTP 408/429/5xx をリトライ対象。
    - 401 発生時にリフレッシュトークンで自動的に id_token を再取得して 1 回リトライ。
    - ページネーション対応（pagination_key を追跡）。
    - fetch_* 系で日足・財務・カレンダーを取得する関数を提供。
  - DuckDB への保存関数を実装（冪等性を重視）:
    - save_daily_quotes, save_financial_statements, save_market_calendar：ON CONFLICT DO UPDATE を用いた更新挙動。
    - レコードの前処理（型変換用ユーティリティ _to_float / _to_int）。
    - PK 欠損行のスキップ・ログ警告。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事収集パイプラインを実装。
    - RSS 取得 (fetch_rss)、テキスト前処理、記事ID生成、DuckDB への保存を含むワンストップ実装。
    - 記事 ID は URL 正規化（トラッキングパラメータ削除・ソート等）後の SHA-256 の先頭 32 文字で生成し、冪等性を担保。
    - defusedxml を利用した XML パース（XML Bomb 対策）。
    - HTTP レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後サイズチェック（Gzip bomb 対策）。
    - リダイレクト時にスキーム/ホスト検査を行うカスタムリダイレクトハンドラを提供（SSRF 対策）。
    - URL スキーム検証（http/https のみ許可）とプライベートホスト判定を実施。
    - raw_news, news_symbols テーブルへの冪等保存（チャンク分割、トランザクション、INSERT ... RETURNING を利用）。
    - テキストから銘柄コード（4桁）を抽出するユーティリティ extract_stock_codes を提供。
    - デフォルト RSS ソースを一つ（Yahoo Finance のビジネスカテゴリ）として用意。
- Research（特徴量・ファクター）モジュール (kabusys.research)
  - feature_exploration:
    - calc_forward_returns: 指定日からの将来リターンを一括 SQL で取得。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を計算する実装（ties の平均ランク対応）。
    - rank, factor_summary: ランキングと基本統計量計算の純粋 Python 実装（外部依存なし）。
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の SQL ウィンドウ関数で計算。
    - calc_volatility: ATR(20)、相対 ATR、20日平均売買代金、出来高比率を計算（true range の NULL 伝播制御を含む）。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を算出（最新財務レコードを選択）。
  - 研究系関数はすべて DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみを参照する設計（本番 API にはアクセスしない）。
  - pandas 等の外部ライブラリに依存しない純粋標準ライブラリ実装を目指す。
- DuckDB スキーマ初期化 (kabusys.data.schema)
  - Raw レイヤー用のテーブル DDL を実装（raw_prices, raw_financials, raw_news, raw_executions 等の定義）。
  - 各テーブルに制約（PRIMARY KEY、CHECK 等）を追加してデータ整合性を強化。

### Fixed
- データ型変換の堅牢化
  - _to_int: "1.0" のような文字列を float 経由で安全に int に変換、浮動小数部が存在する場合は None を返すことで意図しない切り捨てを防止。
  - RSS/HTML テキスト前処理で URL 除去と空白正規化を統一的に実行。

### Security
- News Collector における SSRF 対策強化
  - リダイレクト先のスキーム検証とプライベートアドレス判定（DNS 解決結果や直接 IP 指定の判定含む）。
  - defusedxml を利用して XML パースの安全性を向上。
  - レスポンスサイズ制限・gzip 解凍後のサイズチェックで DoS 対策を追加。
- J-Quants クライアント
  - ID トークンの自動リフレッシュを制御し、無限再帰を防止するフラグ allow_refresh を導入。
  - レート制限とリトライの実装で外部 API 呼び出しの安定性を向上。

### Notes / Implementation details
- Research 系の関数はパフォーマンスを意識して SQL ウィンドウ関数で可能な限り計算を行う実装。
- calc_forward_returns / calc_momentum 等は「営業日」 ≒ 連続レコード数（LAG / LEAD のオフセット）を用いるため、カレンダー日数の不足を補うためにスキャン範囲にバッファ（倍数の日数）を取っている。
- .env パーサは複雑なクォート/エスケープや inline コメントを扱うためテストが必要（自動ロードはテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。

### Breaking Changes
- なし（初期リリース）。

### Deprecated
- なし。