Keep a Changelog
----------------
すべての重要な変更点をこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣習に従います。
ソース管理の履歴ではセマンティックバージョニングを使用します。

[Unreleased]
- なし

[0.1.0] - 2026-03-26
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買フレームワークの基本機能を実装。
- パッケージ基礎
  - kabusys パッケージと __version__ = "0.1.0" を追加。
  - 公開モジュール: data, strategy, execution, monitoring をエクスポート。

- 設定・環境変数読み込み (kabusys.config)
  - .env/.env.local の自動ロード機能を実装（プロジェクトルート: .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサ: export プレフィックス、単一/二重引用符、バックスラッシュエスケープ、行内コメント判定等をサポート。
  - Settings クラスを提供し、必須環境変数を明示的に取得（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）。
  - 値検証: KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の妥当性チェックを実装。

- ポートフォリオ構築 (kabusys.portfolio)
  - 銘柄選定: select_candidates（スコア降順、同点時 signal_rank によるタイブレーク）。
  - 配分ウェイト計算: calc_equal_weights（等金額）、calc_score_weights（スコア加重、全スコアが 0 の場合は等配分にフォールバック）。
  - リスク調整: apply_sector_cap（セクター集中上限による候補除外）、calc_regime_multiplier（市場レジームに応じた投下資金乗数）。
  - 株数算出: calc_position_sizes
    - allocation_method="risk_based" / "equal" / "score" に対応。
    - リスクベースの計算（risk_pct / stop_loss_pct）、ポジション上限（max_position_pct）、全体利用上限（max_utilization）、単元（lot_size）丸め、手数料/スリッページ見積り（cost_buffer）を考慮した aggregate cap スケーリング実装。
    - price が利用できない銘柄のスキップ、余剰キャッシュを fractional remainder に基づき lot_size 単位で配分するロジック。

- 戦略（feature / signal）
  - 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
    - research モジュールから生ファクターを取得（calc_momentum / calc_volatility / calc_value）。
    - ユニバースフィルタ（最低株価・最低平均売買代金）を実装。
    - 数値ファクターの Z スコア正規化（zscore_normalize を利用）と ±3 でのクリップ。
    - DuckDB を用いた日付単位の冪等な features テーブルの置換（BEGIN/COMMIT/ROLLBACK）。
  - シグナル生成 (kabusys.strategy.signal_generator)
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - final_score の加重合算（デフォルト重みを提供）と閾値に基づく BUY シグナル生成（デフォルト threshold=0.60）。
    - AI の regime_score 集計による Bear レジーム判定（サンプル閾値あり）と、Bear 時の BUY 抑制。
    - エグジット判定（ストップロス、スコア低下）による SELL シグナル生成。SELL は優先処理され、BUY から除外。
    - signals テーブルへの日付単位での置換書き込み（トランザクション処理・ロールバック対応）。
    - 重みの検証・正規化ロジック（不正な値は警告してスキップ、合計が 1.0 になるよう補正）。

- リサーチユーティリティ (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: 1/3/6 ヶ月相当リターン、MA200 乖離率の算出（データ不足時は None）。
    - calc_volatility: ATR20、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: 最新の財務データ（raw_financials）と株価から PER/ROE を計算。
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを一括取得。
    - calc_ic: スピアマンのランク相関（IC）計算。3 サンプル未満は計算不能で None を返す。
    - factor_summary: count/mean/std/min/max/median の統計サマリ。
    - rank: 同順位は平均ランクで扱うランク付けユーティリティ（浮動小数点丸めによる ties 対策あり）。
  - zscore_normalize はデータモジュール側に委譲（kabusys.data.stats 参照）。

- バックテスト (kabusys.backtest)
  - シミュレータ (simulator)
    - PortfolioSimulator：メモリ内の cash/positions/cost_basis 管理、約定処理（SELL を先に、BUY を後に処理）。
    - 約定モデル：スリッページ（BUY:+、SELL:-）、手数料率を考慮。TradeRecord/DailySnapshot のデータ構造を提供。
    - 部分約定や単元（lot_size）対応の土台実装。
  - 評価指標 (metrics)
    - バックテスト指標計算 (CAGR、Sharpe、Max Drawdown、Win Rate、Payoff Ratio、総トレード数) を実装。

- ロギング・堅牢性
  - 各所で logging を利用して状況や警告を記録。
  - DuckDB によるトランザクション処理で COMMIT/ROLLBACK を明示的に管理。
  - ファイル読み込みや価格欠損などに対して警告を出し安全にスキップする実装。

Fixed
- 初版リリースに伴う実装上の既知問題対応（詳細は「Notes / Known limitations」参照）。

Notes / Known limitations / TODO
- position_sizing の lot_size は現在グローバル定数として扱われ、将来的に銘柄別 lot_map への拡張予定（TODO をコメントで記載）。
- apply_sector_cap:
  - "unknown" セクターはセクター上限制限の対象外（除外しない）として実装。
  - price_map に price が欠損（0.0）がある場合、エクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討している旨をコメントで明示。
- _generate_sell_signals:
  - トレーリングストップや時間決済（保有日数ベース）は未実装（positions テーブルに peak_price / entry_date 等の拡張が必要）。
- calc_score_weights:
  - 全銘柄のスコア合計が 0 の場合は等金額配分へフォールバックし、WARNING を出力する挙動。
- generate_signals:
  - ai_scores が不足している場合の扱い（news スコアは中立 0.5 で補完）。
  - Bear 判定はサンプル閾値を持ち、閾値未満なら Bear とみなさない設計。
- 環境変数自動ロード:
  - プロジェクトルートの検出に失敗した場合は自動ロードをスキップする仕様。
- 一部の処理は外部モジュール（kabusys.data.stats の zscore_normalize 等）に依存しており、該当実装の存在を前提とする。
- 単体テスト・エンドツーエンドテストに関するコードは本差分に含まれていない（テスト用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD を提供）。

開発者向け備考
- 公開 API（重要な関数）
  - kabusys.config.settings: 各種環境設定へのアクセサ
  - kabusys.portfolio: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
  - kabusys.strategy: build_features, generate_signals
  - kabusys.research: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
  - kabusys.backtest: PortfolioSimulator, DailySnapshot, TradeRecord, calc_metrics
- DuckDB を利用する処理は conn（DuckDB 接続）を引数に取り、外部で接続管理を行う設計。

ライセンス・その他
- 本リリースはコードベースから推測して CHANGELOG を作成したものであり、実際のリリースノートや日付はソース管理履歴に基づいて調整してください。