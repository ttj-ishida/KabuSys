# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-19
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージ名を kabusys として初期モジュールを追加。バージョンは 0.1.0（src/kabusys/__init__.py）。
  - パッケージ公開用の __all__ に data, strategy, execution, monitoring を設定。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出機能を追加 (.git または pyproject.toml を探索)。
  - .env のパースを独自実装（コメント、export プレフィックス、クォートとエスケープ処理、インラインコメント処理等を考慮）。
  - 自動読み込みの優先順位を実装：OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live） / ログレベル等の取得と簡易バリデーションを実装。
  - 必須環境変数未設定時に ValueError を投げる _require ヘルパーを導入。

- データ取得クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を固定間隔のスロットリングで制御する RateLimiter を実装。
  - リトライロジック（指数バックオフ、最大 3 回）、および HTTP 429 の Retry-After ヘッダ対応を実装。
  - 401 Unauthorized 受信時にリフレッシュトークンで id_token を自動更新して再試行する仕組みを実装（キャッシュ付き）。
  - ページネーション対応のデータ取得関数を追加:
    - fetch_daily_quotes (日足)
    - fetch_financial_statements (財務)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB へ保存する冪等的関数を追加（ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes -> raw_prices
    - save_financial_statements -> raw_financials
    - save_market_calendar -> market_calendar
  - 型変換ユーティリティ (_to_float, _to_int) を実装（不正値を None にする挙動を明示）。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集機能を実装。
  - セキュリティ対策を多数導入:
    - defusedxml を使った XML パース（XML Bomb 等対策）。
    - SSRF 対策（リダイレクト先のスキーム検証、プライベートIP/ループバック判定、リダイレクトハンドラで事前検証）。
    - URL スキームは http/https のみ許可。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - 記事整備機能:
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去）。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
    - テキスト前処理（URL除去、空白正規化）。
    - pubDate のパースと UTC への正規化。
  - DB 保存機能（DuckDB）:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用いた一括挿入（チャンク処理、トランザクションでまとめてコミット）。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへ記事と銘柄の紐付けを一括保存（ON CONFLICT DO NOTHING + RETURNING による実際の挿入数の検出）。
  - 銘柄コード抽出機能（4桁数字の検出と known_codes によるフィルタリング）。
  - run_news_collection: 複数 RSS ソースの収集を統合するジョブを実装（ソース単位でエラーハンドリングし、銘柄紐付けまで実行）。

- Research（特徴量・因子計算）
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns: 指定日の終値から複数ホライズン（デフォルト 1,5,21 営業日）の将来リターンをまとめて取得する処理を実装（DuckDB 上で LEAD を使った1クエリ取得）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。欠損/非有限値の除外、最小サンプル数チェックを含む。
    - rank: 同順位は平均ランクにするランク化処理（丸めによる浮動小数点の ties 対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ機能。
  - src/kabusys/research/factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離率）を計算。過去データ不足時は None を返す設計。
    - calc_volatility: 20日 ATR（atr_20）および相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御や cnt チェックを実装。
    - calc_value: raw_financials から target_date 以前の最新財務（eps, roe）を取得して PER / ROE を計算（EPS 欠損や 0 の場合は PER = None）。
  - src/kabusys/research/__init__.py:
    - 主要関数とユーティリティ（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を公開。

- DuckDB スキーマ（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層を想定したスキーマ定義モジュールを追加。
  - raw_prices, raw_financials, raw_news 等の CREATE TABLE DDL を定義（PRIMARY KEY, CHECK 制約等を含む）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- news_collector:
  - RSS 収集周りで SSRF 防止（ホストの私的アドレスチェック、リダイレクト時検査）、XML パースに defusedxml を採用、レスポンスサイズ上限の導入など複数の安全対策を実装。
- jquants_client:
  - API レート制限順守とエラー時の安全なリトライ／トークンリフレッシュ処理を導入。

### Notes / Limitations
- strategy/execution パッケージはプレースホルダ（__init__.py は存在）で、発注ロジックなどの実装は含まれていません。
- Research モジュールは DuckDB のテーブル（prices_daily / raw_financials 等）を前提とし、本番 API（発注等）にはアクセスしない設計です。
- schema.py 内の実装は DDL の一部を含みます（raw_executions 等の定義はファイル末尾に続く想定）。
- 外部依存を最小化する設計方針（pandas 等を使用しない関数がある）ですが、一部機能は将来的にライブラリ導入で簡潔化可能です。

--- 

今後のリリースでは、strategy/ execution 層の実装、モジュール間の統合テスト、ドキュメント（API/DB スキーマ/運用手順）の充実を予定しています。