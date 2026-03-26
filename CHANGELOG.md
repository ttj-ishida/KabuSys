CHANGELOG
=========

すべての重要な変更点をここに記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
日付はリリース日を示します。

Unreleased
----------

### Added
- 設計上の未実装・改良候補を列挙（今後のリリースで対応予定）
  - 銘柄ごとの単元情報を考慮した position_sizing の拡張（現状は global lot_size のみ）。comments に将来の lot_map 拡張の記載あり。
  - price 欠損時のフォールバック価格（前日終値や取得原価等）を用いる処理の追加。現状は price が欠損のときはスキップまたは過少見積のリスクがある旨の TODO コメントあり。
  - positions テーブルに peak_price / entry_date を保持してトレーリングストップ・時間決済を実装（コメントで未実装として明記）。
  - 追加的なレジーム/スコアリングのチューニングや AI スコアの扱い改善。

### Fixed / Changed / Security
- （未リリース）細かなログ・検証強化、weights パラメータのバリデーション改善などを予定。

0.1.0 - 2026-03-26
------------------

### Added
- パッケージの初期リリース（kabusys v0.1.0）
- 基本モジュール
  - パッケージ初期化情報 (src/kabusys/__init__.py)
    - __version__ = "0.1.0"
    - 主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）
- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env/.env.local の自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を基準）
  - export 形式やクォート／エスケープ、インラインコメント処理に対応した .env パーサ実装
  - OS 環境変数を保護する protected オプションと override 制御
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグ
  - Settings クラスによる型付きアクセス（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）、バリデーション（KABUSYS_ENV, LOG_LEVEL）
- ポートフォリオ構築（src/kabusys/portfolio/）
  - portfolio_builder
    - select_candidates: スコア降順で候補選定（signal_rank によるタイブレーク）
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）
  - risk_adjustment
    - apply_sector_cap: 同一セクター集中の上限チェック（sell 予定銘柄をエクスポージャー計算から除外可能）
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear）
  - position_sizing
    - calc_position_sizes: allocation_method に基づく株数計算（risk_based / equal / score をサポート）
    - 単元（lot_size）丸め、per-position 上限、aggregate cap（available_cash によるスケーリング）、cost_buffer による保守的なコスト推定
    - スケールダウン時の再配分ロジック（fractional remainders を用いた lot 単位での追加配分）
- 戦略（src/kabusys/strategy/）
  - feature_engineering.build_features
    - research モジュールで計算した生ファクターをマージ、ユニバースフィルタ（最低株価・最低売買代金）、Z スコア正規化（±3クリップ）、DuckDB へ日付単位で UPSERT（トランザクションで原子性確保）
  - signal_generator.generate_signals
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - final_score の重み付き合成（デフォルト重みはコード内定義）
    - Bear レジーム時の BUY 抑制ロジック（AI の regime_score 集計による判定）
    - BUY/SELL シグナルの判定と signals テーブルへの日付単位置換（トランザクション）
    - weights 引数のバリデーションと再スケーリング
    - SELL 優先ポリシー（SELL 対象を BUY から除外し、BUY の rank を再付与）
- リサーチ（src/kabusys/research/）
  - factor_research
    - calc_momentum: 1/3/6M リターン、MA200 乖離を計算
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率
    - calc_value: EPS ベースの PER、ROE（raw_financials から最新レコードを取得）
  - feature_exploration
    - calc_forward_returns: 指定ホライズンの将来リターン（1/5/21 日等）を一括取得
    - calc_ic: スピアマンランク相関（IC）計算（結合、欠損除外、最小サンプル判定）
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算
    - rank: 平均ランク（同順位は平均ランク）への変換ロジック
  - zscore_normalize を含む研究系ユーティリティを公開
- バックテスト（src/kabusys/backtest/）
  - metrics.calc_metrics: DailySnapshot と TradeRecord から主要指標を計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）
  - simulator.PortfolioSimulator
    - 擬似約定処理、日次スナップショット管理、TradeRecord の生成
    - スリッページ・手数料を考慮した約定（SELL を先に処理、SELL は保有全量クローズ）
    - history/trades のための dataclass 定義（DailySnapshot, TradeRecord）

### Changed
- n/a（初回リリースのためまとまった変更履歴なし）

### Fixed
- n/a（初回リリース）

### Security
- n/a

### Known limitations / Notes
- 多くの関数は「DB 参照なし」または「DuckDB 接続を受ける」設計であり、本番の発注 API や外部サービスに依存しない純粋な計算モジュール群として実装されている。
- feature_engineering / signal_generation / position_sizing 等は実運用上の安全弁（price 欠損時の取り扱い、セクター上限、レジーム乗数等）を組み込んでいるが、いくつかのフォールバック（price の代替値、銘柄別 lot_map、トレーリングストップ等）は未実装であり、README やドキュメントでの注意が必要。
- データベース操作は日付単位の削除→挿入トランザクションで冪等性を確保しているが、外部の DB 運用ポリシー（バックアップ/排他制御等）に依存する点に注意。

Acknowledgments
---------------
- この CHANGELOG はコード内の docstring・コメント・実装内容（関数名、引数、ロジック、TODO コメント等）から推測して作成しました。実際のリリースノートと差異がある可能性があります。補足・修正の要望があれば反映します。