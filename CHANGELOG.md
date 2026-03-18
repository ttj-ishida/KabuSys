# Changelog

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」仕様に準拠します。

現在のリリース履歴は以下の通りです。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-18
初回リリース。KabuSys のコアデータ処理・リサーチ・データ取得・ニュース収集・設定管理の基盤機能を実装しました。

### Added
- パッケージ基盤
  - パッケージメタ情報および公開 API を定義（src/kabusys/__init__.py）。
  - strategy／execution サブパッケージのプレースホルダを追加（src/kabusys/strategy/__init__.py, src/kabusys/execution/__init__.py）。

- 設定管理
  - 環境変数／.env ファイル読み込みユーティリティを実装（src/kabusys/config.py）。
    - プロジェクトルート検出ロジック（.git または pyproject.toml 基準）を採用し、CWD に依存しない自動ロードを実現。
    - .env / .env.local の読み込み順序を定義（OS 環境変数 > .env.local > .env）。
    - export プレフィックス、クォート・エスケープ、行末コメントなどの .env 構文を考慮したパーサ実装。
    - 自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 必須環境変数取得ヘルパー _require と Settings クラスを提供（J-Quants、kabu API、Slack、DB パス、環境/ログレベル等）。

- Data: J-Quants クライアント
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - 固定間隔スロットリングによるレート制限（120 req/min）を実装（内部 RateLimiter）。
    - HTTP リクエスト共通処理にリトライ（指数バックオフ、最大 3 回）と 401 時のトークン自動リフレッシュを実装。
    - ページネーション対応のデータ取得関数を実装：fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar。
    - DuckDB へ冪等的に保存する関数を実装：save_daily_quotes、save_financial_statements、save_market_calendar（ON CONFLICT DO UPDATE）。
    - データ変換ユーティリティ（_to_float / _to_int）を実装。
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を追跡可能に。

- Data: ニュース収集
  - RSS フィード収集・前処理・DB 保存機能を実装（src/kabusys/data/news_collector.py）。
    - RSS フェッチ（fetch_rss）、記事正規化（URL 追跡パラメータ削除・正規化・記事 ID は正規化 URL の SHA-256 先頭32文字）、テキスト前処理（URL 除去・空白正規化）。
    - defusedxml を用いた XML パースで XML 攻撃対策を実施。
    - SSRF 対策：HTTP リダイレクト先のスキーム検証とプライベートアドレス判定（DNS 解決結果の IP を検査）を実装。
    - レスポンスサイズ上限（デフォルト 10MB）チェック、gzip の取り扱い（解凍後サイズ検証）を実装。
    - raw_news へのチャンク挿入と INSERT ... RETURNING を利用した冪等保存（save_raw_news）、news_symbols / bulk 紐付け保存ユーティリティを実装。
    - テキストから 4 桁銘柄コードを抽出するユーティリティ extract_stock_codes と、全ソース一括収集ジョブ run_news_collection を実装。
    - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを設定。

- Research（リサーチ）
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、単一クエリで取得）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ をランク化して算出、無効値/レコード数チェック対応）。
    - rank（同順位は平均ランク）と factor_summary（count/mean/std/min/max/median）を実装。
    - 標準ライブラリのみで動作する設計（pandas 等に依存しない）。
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - モメンタム calc_momentum（1M/3M/6M リターン・MA200 乖離）。
    - ボラティリティ/流動性 calc_volatility（20 日 ATR、ATR 比、20 日平均売買代金、出来高比）。
    - バリュー calc_value（raw_financials からの EPS/ROE を用いた PER/ROE 計算）。
    - DuckDB の prices_daily / raw_financials のみ参照する純粋な分析系関数として実装。

- Schema（DuckDB スキーマ）
  - DuckDB 用の DDL 定義と初期化ロジック（src/kabusys/data/schema.py）を追加。
    - Raw Layer のテーブル定義（raw_prices, raw_financials, raw_news, raw_executions 等）を含む（プロジェクト設計に基づく 3 層構造の記述あり）。
    - スキーマ名・列定義・制約（CHECK/PRIMARY KEY）を明示。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集モジュールに SSRF 対策、XML インジェクション対策（defusedxml）、レスポンスサイズ制限、許可スキームチェック等を実装。
- J-Quants クライアントは 401 時にトークンを自動リフレッシュするが、refresh の呼び出し時は無限再帰を防止する設計（allow_refresh フラグ）。

### Performance
- J-Quants API のレート制御を組み込み、ページネーションではモジュール内トークンキャッシュを共有して効率化。
- calc_forward_returns / calc_momentum / calc_volatility などは可能な限り単一 SQL クエリで計算し、スキャン範囲をカレンダーバッファで限定してパフォーマンスを考慮。

### Notes / Known limitations
- strategy / execution の具体的な売買ロジックや発注実装は現時点では未実装（プレースホルダのみ）。
- Research モジュールは pandas 等に依存せず標準ライブラリ + DuckDB で実装しているため、小規模データや分析パイプライン向け。大規模なデータ処理や高度な欠損処理が必要な場合は追加の前処理が必要になる可能性がある。
- DuckDB スキーマ定義は一部（raw_executions の続き等）でファイル内にまだ続きがあるため、DDL の完全性は実際のスキーマ初期化コードを参照してください。
- ロギングやエラーハンドリングは基本実装のみ。運用環境ではログ設定・監視連携（Slack 通知等）を追加することを推奨。

---

作成日: 2026-03-18

（注）この CHANGELOG は提示されたコードベースの内容から推測して作成しています。実際のリリースノートとして使用する場合は、必要に応じて担当者による追記・修正を行ってください。