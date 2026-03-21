# CHANGELOG

すべての注目すべき変更点をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]
- （無し）

## [0.1.0] - 2026-03-21
初回リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加点は以下のとおりです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化とバージョン情報（src/kabusys/__init__.py）。
  - strategy、execution、data、research、monitoring 等の主要モジュール群を公開。

- 環境設定・読み込み機能（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動ロードする機能を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - export KEY=val、クォート（シングル／ダブル）、エスケープ、インラインコメントなどを考慮した堅牢な .env パーサーを実装。
  - 必須環境変数取得時に未設定なら ValueError を送出する _require ユーティリティを提供。
  - 設定クラス Settings を提供（J-Quants トークン、kabu API 設定、Slack、DB パス、実行環境判定、ログレベル検証など）。

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）の固定間隔スロットリングによる制御。
  - リトライ（指数バックオフ、最大 3 回）、ネットワーク・HTTP エラーに対する再試行ロジック。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ管理。
  - ページネーション対応の fetch_* 系関数（株価、財務データ、マーケットカレンダー）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT ベースの冪等保存を行う。
  - 文字列 → float/int 変換ユーティリティ（_to_float / _to_int）を実装し、不正値を安全に扱う。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得して raw_news へ保存する機能を実装（デフォルトに Yahoo Finance の RSS を含む）。
  - URL 正規化（トラッキングパラメータ削除、クエリソート、小文字化、フラグメント削除）と記事IDのハッシュ化による冪等性。
  - defusedxml を用いた XML パース（XML Bomb 等の防御）、受信サイズ制限（10MB）、SSRF 緩和の考慮。
  - バルク INSERT のチャンク処理など性能・安全性を考慮した実装。

- リサーチ（src/kabusys/research/）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m / mom_3m / mom_6m、ma200_dev を計算。
    - calc_volatility: 20日 ATR・相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: 最新の財務データ（eps 等）と株価を用いて PER / ROE を計算。
    - DuckDB の prices_daily / raw_financials テーブルのみ参照する設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で計算。
    - calc_ic: Spearman ランク相関（Information Coefficient）を実装。
    - rank / factor_summary: ランク変換と基本統計量の集計を提供。
  - 研究用ユーティリティ群を __all__ にエクスポート。

- 戦略（src/kabusys/strategy/）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - 研究で算出した生ファクターを統合、ユニバースフィルタ（最低株価、最低平均売買代金）を適用。
    - 指定カラムの Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位での置換（DELETE → INSERT、トランザクション）による冪等処理を実装。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合してコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
    - final_score を重み付きで計算（デフォルト重みを定義）、閾値超過で BUY シグナルを生成。
    - Bear レジーム検知（AI の regime_score の平均が負）時は BUY を抑制。
    - エグジット判定（STOP LOSS: -8% 以下、スコア低下による売却）を実装（positions, prices を参照）。
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入）による冪等性を担保。
    - 重み検証ロジック（不正な重みを無視、合計を再スケール）を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- defusedxml の利用、RSS/HTTP 入力の検証（URL スキーム制限、受信サイズ制限）など、外部入力に対する基本的な安全対策を導入。
- J-Quants クライアントにおけるトークン自動リフレッシュ時の再帰防止（allow_refresh フラグ）を実装。

### Notes / Known limitations
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は現時点で未実装（コメントで言及）。positions テーブルに peak_price / entry_date 等が必要。
- research モジュールは DuckDB のテーブル（prices_daily / raw_financials 等）に依存するため、データロードが前提。
- news_collector の記事 ID は正規化後の SHA-256 を先頭 32 文字で利用する方針だが、外部データの性質により重複可能性はゼロではない。
- ロギングや警告メッセージが適切に設定されていることを想定（運用時はログ出力の設定を行ってください）。

---

（補足）この CHANGELOG はソースコードの実装内容から推測して作成しています。細かな API 仕様・公開インターフェースの変更は実際のリリースノートと異なる場合があります。