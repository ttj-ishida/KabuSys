# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルはリポジトリ内のコードから推測して作成したものであり、実際のコミット履歴ではありません。

## [Unreleased]

### Added
- パッケージ初期構成（バージョン 0.1.0 相当の機能群を追加）
  - パッケージメタ
    - kabusys パッケージの基本エントリ（src/kabusys/__init__.py、__version__ = "0.1.0"）。
  - 設定/環境変数管理（src/kabusys/config.py）
    - .env ファイルまたは OS 環境変数から設定値を読み込む自動ローダーを実装。プロジェクトルートを .git または pyproject.toml から探索するため、CWD に依存しない。
    - .env ファイルのパース実装（コメント、export プレフィックス、クォート/エスケープ処理、インラインコメント判定等に対応）。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供し、アプリケーションで利用する主要な設定項目（J-Quants / kabuステーション API、Slack、DB パス、実行環境・ログレベル判定など）をプロパティとして取得可能。
    - env 値や log level のバリデーションを実装（許容値外で ValueError を送出）。
  - ポートフォリオ構築（src/kabusys/portfolio/*）
    - 銘柄選定・重み計算（portfolio_builder.py）
      - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択。
      - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装（スコアが全て 0 の場合は等配分へフォールバックし WARNING）。
    - リスク調整（risk_adjustment.py）
      - apply_sector_cap: 既存保有のセクター比率を計算し、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（未知のレジームはフォールバック）。
      - ロギングによるデバッグ情報出力。
    - ポジションサイズ算出（position_sizing.py）
      - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に基づく発注株数決定、単元（lot_size）丸め、per-position 上限と aggregate cap（利用可能現金）適用、cost_buffer による保守的見積りとスケールダウン手続きを実装。
      - aggregate スケールダウン時に端数処理（lot 単位での再配分）を行い再現性のあるソート処理を実装。
  - 戦略（src/kabusys/strategy/*）
    - 特徴量エンジニアリング（feature_engineering.py）
      - research モジュールで計算した生ファクターを取り込み、ユニバースフィルタ（最低株価・最低流動性）適用、選定カラムの Z スコア正規化、±3 でのクリップ、DuckDB への日付単位の UPSERT（冪等）を実装。
      - build_features(conn, target_date) が公開 API。
    - シグナル生成（signal_generator.py）
      - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースの各コンポーネントスコアを算出、重み付け合算して final_score を計算。
      - Bear レジーム検知時は BUY シグナルを抑制するロジックを実装（レジーム判定は ai_scores の regime_score 平均に基づく）。
      - SELL シグナル（ストップロス、スコア低下）生成。features が無い保有銘柄は score=0 と見なして SELL 判定。
      - 日付単位で signals テーブルを置換するトランザクション処理（冪等性）を実装。
  - 研究ツール（src/kabusys/research/*）
    - ファクター計算（factor_research.py）
      - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を参照し各種ファクター（mom_1m/3m/6m, ma200_dev, atr_pct, avg_turnover, per, roe 等）を返却。
    - 特徴量探索（feature_exploration.py）
      - calc_forward_returns: 与えたホライズン（例: 1/5/21 営業日）で将来リターンを計算。
      - calc_ic: Spearman のランク相関（IC）計算を実装。サンプル不足時は None を返す。
      - factor_summary / rank: 基本統計量やランク付けユーティリティを提供。
    - research パッケージ公開 API を整備（zscore_normalize の再エクスポート等）。
  - バックテスト（src/kabusys/backtest/*）
    - PortfolioSimulator（simulator.py）
      - 日次スナップショット（DailySnapshot）、約定記録（TradeRecord）を定義。
      - execute_orders: SELL を先に処理し全量クローズ、その後 BUY（スリッページ・手数料モデルを適用）を行う簡易シミュレータを実装。
      - メモリ内状態（cash / positions / cost_basis / history / trades）で動作し、DB 参照を持たない設計。
    - メトリクス（metrics.py）
      - CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total trades を算出するユーティリティを実装。
      - 入力は DailySnapshot と TradeRecord のリストのみ。
  - パッケージエクスポート
    - strategy, portfolio, research, backtest の主要関数を __init__ で公開（モジュール間の利用を簡潔に）。

### Changed
- なし（初回相当の追加）

### Fixed
- なし（初回相当の追加）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

## 0.1.0 - 2026-03-26 (Initial inferred release)

- 上記「Added」項目を初回リリースとして含む。

## Known issues / Notes / TODO（コード内コメントより推測）
- config._find_project_root がルートを見つけられない場合、自動ロードをスキップする仕様。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用する想定。
- .env パーサはかなり堅牢だが、複雑なシェル式（$VAR 展開や複数行クォート等）には対応していない。
- risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損している（0.0）の場合、エクスポージャーが過少見積りとなり本来ブロックされるべき銘柄が除外されない可能性がある。将来的に前日終値や取得原価をフォールバックする拡張を検討する旨の TODO。
- position_sizing:
  - lot_size は現在一括で渡す API（全銘柄共通）。将来的に銘柄別 lot_map に対応する TODO が存在。
- signal_generator._generate_sell_signals:
  - トレーリングストップや時間決済（保有 60 営業日超など）は未実装（positions テーブルに peak_price / entry_date を持たせる必要あり）。
- feature_engineering / strategy 関連は DuckDB に依存（prices_daily, raw_financials, features, ai_scores, positions, signals テーブルの存在が前提）。
- PortfolioSimulator の BUY 処理は部分約定や複雑なオーダーブッキングをサポートしていない（SELL は全量クローズ）。将来的に部分利確等を検討する余地あり。
- ロギングは各モジュールで適切に出力しているが、ログの初期設定（ハンドラ・フォーマット）は外部で行う必要がある。

もし実際のリリース日や追加の変更履歴（コミットメッセージ等）があれば、それに合わせて日付やセクションを調整します。必要であれば英語版や詳細なリリースノート（機能ごとの使用例や API ドキュメント）も作成します。