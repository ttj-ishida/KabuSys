# CHANGELOG

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  

[Unreleased]: https://example.com/kabusys/compare/v0.1.0...HEAD

## [0.1.0] - 2026-03-19

初回公開リリース。以下の主要機能・モジュールを実装しました。

### Added
- パッケージの基本情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。
  - パッケージ公開用のエクスポート一覧を `__all__` に定義（data / strategy / execution / monitoring）。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出機能を導入（.git または pyproject.toml を基準に探索）。
  - .env / .env.local の読み込み順序をサポート（OS環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env パースの堅牢化（コメント、export プレフィックス、引用符・エスケープ対応、インラインコメント処理）。
  - 必須環境変数を取得する `_require` と `Settings` クラスを追加（J-Quants / kabu / Slack / DB パス / ログレベル等）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL）とユーティリティプロパティ（is_live / is_paper / is_dev）を提供。

- データ取得・永続化（J-Quants クライアント） (`kabusys.data.jquants_client`)
  - J-Quants API 用クライアントを実装（ID トークン取得、自動リフレッシュ対応）。
  - API レート制御用の固定間隔レートリミッタを実装（120 req/min を想定）。
  - HTTP リトライ（指数バックオフ、最大 3 回）、429 の Retry-After 優先処理、408/429/5xx の再試行処理を実装。
  - ページネーション対応のフェッチ関数を追加:
    - fetch_daily_quotes（OHLCV）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数を実装（冪等化のため ON CONFLICT DO UPDATE を利用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 入力変換ユーティリティ `_to_float`, `_to_int` を追加し不正値の安全な扱いを実現。
  - ページングやトークンキャッシュを踏まえた設計により look‑ahead bias の説明（fetched_at の記録）を考慮。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードから記事を収集し DuckDB raw_news / news_symbols に保存するパイプラインを実装。
  - セキュリティ対策：
    - defusedxml を用いた XML パース（XML bomb 等の防御）。
    - SSRF 対策（リダイレクト時のスキーム/ホスト検査、プライベートアドレス拒否）。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）チェックと gzip 解凍後の再チェック（Gzip bombing 対策）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と SHA-256 ベースの記事 ID 生成（先頭32文字）で冪等性を確保。
  - テキスト前処理ユーティリティ（URL 除去・空白正規化）。
  - RSS パースの堅牢化（content:encoded の名前空間対応、fallback 検出）。
  - DB 保存の効率化: チャンク INSERT、1 トランザクションでのバルク挿入、INSERT ... RETURNING を用いて実際に挿入された数を取得。
  - 銘柄コード抽出と紐付け機能（4桁コード抽出、既知コードセットとの照合）。
  - 統合ジョブ run_news_collection により複数ソースの収集を一括実行・エラーハンドリング。

- リサーチ（特徴量・ファクター計算） (`kabusys.research`)
  - feature_exploration:
    - calc_forward_returns: 指定日から将来（営業日ベース）リターンを計算（複数ホライズン対応、最大252日制約）。
    - calc_ic: Spearman ランク相関（IC）計算。欠損レコード/足りないデータ時の安全処理。
    - rank: 同順位は平均ランクを返すランク関数（丸め対策あり）。
    - factor_summary: カラムごとの基本統計量（count/mean/std/min/max/median）。
    - 実装は標準ライブラリのみを利用（pandas 非依存）、DuckDB を入力として想定。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比を計算（true_range の NULL 伝播を考慮）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER（EPS が有効な場合）/ROE を計算。report_date <= target_date の最新財務データを採用。
    - 各計算は DuckDB のウィンドウ関数を活用し、欠損やデータ不足時は None を返す堅牢な設計。
  - research パッケージの __init__ に主要関数を公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- データベーススキーマ (`kabusys.data.schema`)
  - DuckDB 用のスキーマ定義（Raw / Processed / Feature / Execution 層）を追加。
  - raw_prices / raw_financials / raw_news / raw_executions などの DDL を実装（制約・型・PRIMARY KEY 定義含む）。
  - 初期化と DDL 管理のためのモジュール骨格を追加。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集での複数の SSRF / XML / DoS 対策を導入：
  - defusedxml を用いた XML パース。
  - リダイレクト先のスキームとホスト検査、プライベートアドレス拒否。
  - レスポンスサイズ上限と gzip 解凍後の再チェック。

### Notes / Design decisions
- DuckDB を中心に設計しており、research・data モジュールは prices_daily / raw_financials / raw_* テーブルのみを参照する前提で実装。発注 API 等の外部リソースへのアクセスは行わない設計です（安全性・検証容易性のため）。
- J-Quants クライアントは rate limit（120 req/min）を前提に設計。必要に応じてレートやリトライ挙動は将来調整可能。
- ニュース記事 ID は URL 正規化後のハッシュを使用するため、クエリパラメータの順序やトラッキングパラメータの違いによる重複登録を防止。

---

今後のリリースでは以下を予定しています（案）
- Strategy / Execution 層の発注ロジック実装（kabuステーション連携）。
- モニタリング・アラート機能（Slack 通知の具体実装）。
- テストカバレッジ拡充・CI/CD 設定の追加。
- データ処理パフォーマンス改善（並列化・バッチ処理最適化）。

[0.1.0]: https://example.com/kabusys/releases/tag/v0.1.0