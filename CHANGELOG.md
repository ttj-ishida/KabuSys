# CHANGELOG

この CHANGELOG は「Keep a Changelog」形式に準拠しています。  
リリースは semantic versioning を想定しています。

全般的な注記
- このリポジトリは日本株の自動売買フレームワーク（KabuSys）の初期実装です。
- 多くのモジュールは DuckDB を用いた研究・バッチ処理（features / signals の生成）や、メモリ内で完結するバックテスト／シミュレーションロジックを提供します。
- 実装は「PortfolioConstruction.md」「StrategyModel.md」「BacktestFramework.md」等の設計文書に基づいています（コード内コメント参照）。

Unreleased
- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-03-26
Added
- パッケージ基本情報
  - src/kabusys/__init__.py によるパッケージエクスポート（data, strategy, execution, monitoring）とバージョン定義（0.1.0）。

- 環境設定 / ロード機能
  - src/kabusys/config.py
    - プロジェクトルート検出: .git または pyproject.toml を基準に自動でルートを特定する機能を実装。
    - .env ファイル自動読み込み: OS環境変数 > .env.local > .env の優先順位で読み込む。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 高機能な .env パーサ実装（export プレフィックス、シングル/ダブルクオート内のエスケープ対応、インラインコメントの扱い）。
    - Settings クラスでアプリ設定をプロパティとして提供（J-Quants / kabu ステーション / Slack / DB パス / 環境 / ログレベル 等）。
    - 必須環境変数未設定時に明示的なエラーを出す _require 関数。

- ポートフォリオ構築（候補選定・重み算出）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: スコア降順＋タイブレークで BUY 候補を選択。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等分配にフォールバックし WARNING を出力）。

- リスク調整（セクター制限・レジーム乗数）
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクターエクスポージャに応じて新規候補を除外するロジックを実装（sell の予定銘柄は除外可能）。"unknown" セクターは上限適用外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す。未知レジームは警告を出して 1.0 でフォールバック。

- ポジションサイジング（株数決定）
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した発注株数計算を実装。
    - risk_based: 許容リスク率（risk_pct）と stop_loss_pct を用いて目標株数を算出。
    - equal/score: 重み（weights）に基づく配分と per-position / aggregate の上限を考慮。
    - lot_size に基づく単元丸め処理、aggregate cap のスケーリング（cost_buffer による保守的見積り）と端数配分ロジックを搭載。

- 特徴量エンジニアリング（バッチ処理）
  - src/kabusys/strategy/feature_engineering.py
    - build_features: research モジュールの生ファクター（momentum/volatility/value）を統合し、ユニバースフィルタ（最低株価・最低売買代金）と Z スコア正規化（±3 クリップ）を適用して features テーブルへ UPSERT（冪等）する処理を実装。
    - DuckDB を用いた日付単位の原子的な置換（トランザクション + バルク挿入）。

- シグナル生成
  - src/kabusys/strategy/signal_generator.py
    - generate_signals: features と ai_scores を統合して最終スコアを計算し、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）計算、シグモイド変換、欠損補完ロジック（None → 中立 0.5）。
    - AI ニューススコア統合（ai_scores テーブルから取得、未登録時は補完）。
    - Bear レジーム検知（ai_scores の regime_score 集計）により BUY シグナルを抑制。
    - エグジット条件（ストップロス、スコア低下）による SELL 生成。SELL 優先ポリシー（SELL 対象は BUY から除外して再ランク付け）。

- 研究用ユーティリティ
  - src/kabusys/research/factor_research.py
    - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials からモメンタム・ボラティリティ・バリュー系ファクターを算出。
    - 各関数は (date, code) キーの辞書リストを返す設計。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターンを DuckDB で一括取得。
    - calc_ic: スピアマンの IC（ランク相関）計算。サンプル不足時は None を返す。
    - factor_summary, rank: ファクター統計・ランク化ユーティリティ。
  - src/kabusys/research/__init__.py で主要 API をエクスポート。

- バックテスト関連
  - src/kabusys/backtest/metrics.py
    - BacktestMetrics dataclass と calc_metrics 実装（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
  - src/kabusys/backtest/simulator.py
    - PortfolioSimulator: メモリ内ポートフォリオ管理、擬似約定ロジック（SELL を先に処理、BUY は指定株数約定）、TradeRecord / DailySnapshot データ構造。
    - スリッページ・手数料モデルのパラメータ受け入れ（slippage_rate, commission_rate）。
    - 約定時の単元（lot_size）処理（日本株の単元考慮を想定）。

Changed
- （初回リリースのため変更履歴は無し）

Fixed
- （初回リリースのため修正履歴は無し）

Known limitations / Notes / TODO
- apply_sector_cap: price が欠損（0.0）だとエクスポージャーが過小見積もられ、本来ブロックすべき銘柄が通ってしまう可能性がある。将来的に前日終値や取得原価でのフォールバックを検討。
- _generate_sell_signals:
  - トレーリングストップや時間決済（保有期間に基づく）など、いくつかのエグジット条件は未実装（positions テーブルに peak_price / entry_date 等が必要）。
  - features に存在しない保有銘柄は final_score=0 と見なし SELL 判定対象になる（警告をログに出力）。
- position_sizing.calc_position_sizes:
  - 現時点で lot_size は全銘柄共通の引数。将来的には銘柄別 lot_map を受ける拡張を計画。
- feature_engineering / signal_generator / factor_research:
  - DuckDB のテーブル構成（prices_daily, raw_financials, features, ai_scores, positions, signals 等）に依存するため、実行前にスキーマ準備が必要。
- config._find_project_root() は __file__ を基点に上位ディレクトリを探索する設計で、パッケージ配布後も動作することを想定。ただし特殊な配置環境ではプロジェクトルートが見つからない場合がある（その場合自動 .env ロードはスキップされる）。
- AI スコア（ai_scores）の詳細な算出・学習部分は本リリースには含まれていない（テーブルからの読み込み・統合のみ実装）。

セキュリティ
- 機密情報（API トークン等）は Settings を通して環境変数から取得する設計。.env ファイルの読み込みは標準出力やログにトークンを出力しないよう設計されているが、運用時は .env の取り扱いに注意してください。

開発者向けメモ
- テスト時に自動 .env ロードを避けたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログ出力や警告は該当モジュールの logger を使用しており、デバッグ時はログレベルを DEBUG に設定すると詳細が得られます。
- 各モジュールはできるだけ副作用を避ける（DB 参照は明示された関数の引数として受け取る）設計になっています。

--- 

今後のリリースで予定している主要な改善点（例）
- 銘柄別単元情報導入（lot_map）と position_sizing の拡張
- price 欠損時のフォールバックロジック改善（前日終値・取得原価など）
- トレーリングストップ / 時間決済などの追加エグジット条件実装
- AI スコア生成パイプラインの追加（モデル学習・更新の統合）
- 単体テスト・統合テストの整備と CI ワークフローの追加

（以上）