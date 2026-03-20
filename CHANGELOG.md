# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルは現在のリポジトリのコード内容から推測して作成しています（自動生成ではなくコードベースの観察に基づく要約です）。

新しいリリースは semantic versioning に従います。パッケージのバージョンは `src/kabusys/__init__.py` の `__version__` に基づきます。

## [Unreleased]

（現在のスナップショットは 0.1.0 の初期リリース相当です。今後の変更はここに追加してください）

## [0.1.0] - 2026-03-20

初回公開リリース。主な機能・モジュールと実装上の設計要旨は以下の通りです。

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys（`src/kabusys`）
  - エクスポート: data, strategy, execution, monitoring（`__all__`）

- 環境設定読み込み・管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルートは `.git` または `pyproject.toml` を基準に探索）
  - 自動ロードの無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`
  - .env 行パーサーの実装（コメント、export プレフィックス、クォート・エスケープ対応）
  - 必須環境変数取得ユーティリティ `_require` と `Settings` クラスを提供
    - 必須項目例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DBパスデフォルト: DUCKDB_PATH=`data/kabusys.duckdb`, SQLITE_PATH=`data/monitoring.db`
    - 環境種別検証: KABUSYS_ENV の許容値は `development`, `paper_trading`, `live`
    - ログレベル検証: LOG_LEVEL は `DEBUG/INFO/WARNING/ERROR/CRITICAL`

- Data 層: J-Quants API クライアント（kabusys.data.jquants_client）
  - レート制限管理（固定間隔スロットリング、120 req/min）
  - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx に対応）
  - 401 受信時の自動トークンリフレッシュ（1 回のみ再試行）
  - ページネーション対応の取得関数
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存関数（冪等）
    - save_daily_quotes → raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements → raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar → market_calendar（ON CONFLICT DO UPDATE）
  - 型変換ユーティリティ `_to_float`, `_to_int`
  - fetched_at を UTC ISO8601 で記録し、look-ahead バイアスの監査を容易に

- Data 層: ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集パイプライン（デフォルトソース: Yahoo Finance のビジネスカテゴリ）
  - URL 正規化（トラッキングパラメータ除去、クエリキーソート、フラグメント削除）
  - 記事 ID は正規化 URL の SHA-256 の先頭 32 文字で生成して冪等性を担保
  - defusedxml の利用による XML 安全化
  - HTTP レスポンスサイズ制限（最大 10 MB）
  - DB へのバルク挿入（チャンク化、トランザクションでまとめる）
  - SSRF や意図しないスキームを考慮した実装方針（実装内でのチェックを想定）

- Research 層（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）
    - calc_volatility: ATR(20)/atr_pct / avg_turnover / volume_ratio（20日）
    - calc_value: per / roe（raw_financials と prices_daily を組合せ）
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - calc_forward_returns: 将来リターン（複数ホライズン、既定 [1,5,21]）
    - calc_ic: スピアマンランク相関（IC）計算（ペアが 3 件未満なら None）
    - factor_summary: 基本統計量（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクで処理（丸めによる tie 検出をサポート）
  - research パッケージの __all__ を定義して主要関数を公開

- Strategy 層（kabusys.strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - research モジュールの生ファクターを統合し features テーブルへ UPSERT
    - ユニバースフィルタ: 最低株価（300 円）・20日平均売買代金（5 億円）を適用
    - 正規化: z-score（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ
    - 日付単位の置換（トランザクション + バルク挿入）で冪等性と原子性を保証
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合して final_score を計算
      - コンポーネント: momentum(0.40), value(0.20), volatility(0.15), liquidity(0.15), news(0.10)（デフォルト重み）
      - 重みは渡し値で上書き可能（入力のバリデーションと再スケーリングあり）
    - スコア変換: Z スコアをシグモイドで [0,1] に変換
    - Bear レジーム判定: ai_scores の regime_score 平均が負なら Bear（ただしサンプル数閾値あり）
    - BUY シグナル: threshold（デフォルト 0.60）以上の銘柄を採用（Bear では抑制）
    - SELL シグナル（エグジット）:
      - ストップロス: 現在価格と avg_price の PnL が -8% 以下
      - final_score が threshold 未満
      - SELL は BUY より優先し、同日の signals テーブルは日別置換で保存
    - signals テーブルへの日付単位置換をトランザクションで実施（ロールバック対応）
  - strategy パッケージの __all__ に主要 API を公開（build_features, generate_signals）

### Changed
- 初期リリースのため「変更」は特になし（初期導入機能を列挙）

### Fixed
- .env パーサーの堅牢化
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメント処理などを実装
- DuckDB への保存で PK 欠損行をスキップしログ出力するようにして不正データを無害化
- API クライアントで JSON デコード失敗時に詳細なエラーメッセージを付与

### Security
- ニュース XML パースに defusedxml を採用して XML ベースの攻撃に対処
- ニュース収集で受信最大バイト数を制限してメモリ DoS に対処
- J-Quants クライアントでトークンリフレッシュ処理を明示的に制御し無限再帰を防止
- RSS URL 正規化でトラッキングパラメータ除去、スキームチェック等の SSRF/プライバシー対策を考慮

### Internal / Implementation details
- DuckDB を中心としたデータパイプライン設計（テーブル想定: raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news 等）
- ロギングを各モジュールで使用（重要操作で info/debug/warning を出力）
- トランザクションの一貫性を重視（BEGIN / COMMIT / ROLLBACK と例外時ロールバックの扱い）
- モジュールレベルの ID トークンキャッシュを導入（ページネーション間で共有）

### Notes / Migration / Required DB schema
- 本リリースは複数の DuckDB テーブル（下記参照）を前提に動作します。必要なスキーマを用意してください（カラム名・主キーはコード内 SQL を参照）。
  - raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at)
  - raw_financials (code, report_date, period_type, revenue, operating_profit, net_income, eps, roe, fetched_at)
  - market_calendar (date, is_trading_day, is_half_day, is_sq_day, holiday_name)
  - prices_daily (date, code, close, high, low, volume, turnover, ...)
  - features (date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev, created_at)
  - ai_scores (date, code, ai_score, regime_score, ...)
  - positions (date, code, avg_price, position_size, ...)
  - signals (date, code, side, score, signal_rank, ...)
  - raw_news (id, datetime, source, title, content, url, ...)
- 環境変数必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- .env 自動ロードはプロジェクトルートを検出できない場合はスキップされます（配布後の動作を考慮）

### Breaking Changes
- 初回リリースのため既存互換性に関する破壊的変更はありません。

---

（付記）
- 本 CHANGELOG はコードの現状から推測して作成した要約です。実運用にあたっては README やドキュメント、実際の DB スキーマ定義、テストケースを参照してください。必要であれば、テーブル定義例や環境変数のサンプル（.env.example）を別途作成します。