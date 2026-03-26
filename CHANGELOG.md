Keep a Changelog 準拠 — CHANGELOG.md
=================================

すべての notable な変更はこのファイルに記録します。
フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-03-26
--------------------

Added
- 初回公開: KabuSys 日本株自動売買システム v0.1.0 を追加。
  - パッケージ構成（主要モジュール）
    - kabusys.config: 環境変数 / .env 管理
    - kabusys.portfolio: ポートフォリオ構築（選定、重み付け、ポジションサイズ、リスク調整）
    - kabusys.strategy: 特徴量生成（feature_engineering）とシグナル生成（signal_generator）
    - kabusys.research: ファクター計算・解析ユーティリティ（momentum/volatility/value、探索機能）
    - kabusys.backtest: バックテスト用シミュレータおよび評価指標
    - kabusys.execution / monitoring 等のプレースホルダ（パッケージ公開用）
- 環境変数読み込み（kabusys.config）
  - プロジェクトルート検出: .git または pyproject.toml を起点に自動探索（__file__ ベースで CWD に依存しない）。
  - .env / .env.local の自動読み込み（優先順位: OS 環境 > .env.local > .env）。既存 OS 環境を保護する挙動（protected set）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env ファイルの堅牢なパーサを実装（export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメント処理）。
  - Settings クラス: J-Quants / kabu API / Slack / DB パス等のプロパティを提供。KABUSYS_ENV と LOG_LEVEL のバリデーションを実装（許容値チェック）。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: スコア降順で BUY 候補を選択（タイブレークは signal_rank）。
    - calc_equal_weights, calc_score_weights: 等金額およびスコア加重配分（全スコア 0 の場合は等金額にフォールバックし WARN を出力）。
  - position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた株数計算を実装。
    - per-position cap / aggregate cap（available_cash）適用、lot_size 単位で丸め、cost_buffer を考慮した保守的見積りとスケーリング（残差処理で lot 単位の割当を再配分）。
    - risk_based モードで stop_loss_pct / risk_pct に基づくサイズ算出。
  - risk_adjustment
    - apply_sector_cap: 既存保有のセクター比率が閾値を超えている場合に同セクターの新規候補を除外。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバック（WARN）。
- 特徴量生成（kabusys.strategy.feature_engineering）
  - build_features: research 側の calc_momentum/calc_volatility/calc_value を統合し、
    - ユニバースフィルタ（株価、平均売買代金）を適用、
    - 数値ファクターを Z スコア正規化（kabusys.data.stats.zscore_normalize）、
    - ±3 でクリップ、
    - 日付単位で features テーブルへ冪等な UPSERT（トランザクション処理）を実行。
- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals:
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントの None は中立値 0.5 で補完。
    - デフォルト重みを持ち、ユーザー重みは検証・マージ・正規化して受け入れ。
    - Bear レジーム判定により BUY シグナルを抑制（ai_scores の regime_score 平均が負かつサンプル数閾値以上）。
    - BUY（threshold 基準）／SELL（stop_loss または スコア低下）の判定を行い signals テーブルへ日付単位の置換で書き込み（トランザクション）。
    - SELL 優先ポリシー: SELL 対象は BUY から除外しランクを再付与。
- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum/calc_volatility/calc_value: prices_daily / raw_financials を参照しファクター群を計算（MA200、ATR20、出来高比率、PER 等）。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンを効率的に1クエリで取得。
    - calc_ic: ランク相関（Spearman ρ）を実装（有効レコードが 3 未満なら None を返す）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）。
    - rank: 平均ランク（同順位は平均ランク）実装。浮動小数の丸めで ties を安定化。
- バックテスト（kabusys.backtest）
  - metrics.calc_metrics: DailySnapshot と TradeRecord から複数の評価指標を集約（CAGR、Sharpe、MaxDD、勝率、Payoff Ratio、総トレード数）。
  - simulator.PortfolioSimulator:
    - DailySnapshot / TradeRecord データクラス。
    - execute_orders: SELL を先に処理してから BUY（売却は全量クローズ）。スリッページ・手数料モデルを考慮した約定処理（部分的実装）。trade レコード生成と履歴管理を提供。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- （初期リリースのため該当なし）

Notes / Known limitations / TODO
- .env 価格フォールバック: apply_sector_cap 内で price_map に欠損（0.0）があるとエクスポージャーを過少見積りしてしまう旨の注記あり。将来的に前日終値や取得原価でフォールバックすることを検討する予定。
- position_sizing:
  - 現状 lot_size は全銘柄共通で渡す設計。将来的に銘柄別 lot_map を受け取る拡張を予定（TODO コメントあり）。
- strategy.signal_generator:
  - 未実装のエグジット条件（トレーリングストップ、時間決済）はコメントで明示（positions テーブルに peak_price / entry_date が必要）。
- simulator.PortfolioSimulator:
  - 現行実装は売却を全量でクローズ（部分利確・部分損切りは未対応）。
  - _execute_buy 実装がソース途中で切れている（追加実装が必要）。
- DB 前提: 多くの関数は DuckDB の特定テーブル（prices_daily, raw_financials, features, ai_scores, positions, signals 等）を前提とする。実行には適切なスキーマとデータ準備が必要。
- 外部依存回避: research/feature_exploration は pandas 等に依存せず標準ライブラリ + duckdb で動作する設計。
- ロギング: 多くの関数は詳細なログ / 警告を出す（デバッグ追跡用）。

開発者向けメモ
- パッケージバージョンは kabusys.__version__ = "0.1.0" に設定済み。
- 将来的な 0.x → 1.0 への移行時には API の安定化、部分約定・手数料モデルの拡充、銘柄別単元対応、エンドツーエンド execution 層との結合テストを推奨。

（以上）