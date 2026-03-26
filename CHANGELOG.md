# Changelog

すべての重要な変更履歴をここに記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

## [0.1.0] - 初回リリース
最初のリリース。日本株自動売買システムのコア機能群を実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。公開 API: data, strategy, execution, monitoring。
  - パッケージバージョン: 0.1.0。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数の自動読み込み機能を実装（優先順位: OS 環境変数 > .env.local > .env）。
  - プロジェクトルートを .git または pyproject.toml から探索して自動ロード（カレントワーキングディレクトリ非依存）。
  - .env パーサ実装（export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメントの扱い、無効行スキップ）。
  - 読み込み時に OS 環境変数を保護する protected 機構を導入。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得ヘルパ（_require）と Settings クラス:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト設定。
    - KABUSYS_ENV（development / paper_trading / live の検証）・LOG_LEVEL（DEBUG/INFO/... の検証）・is_live / is_paper / is_dev の補助プロパティ。

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - 候補選定・重み計算（portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選択（同点タイブレーク: signal_rank 昇順）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバックし warning 出力）。
  - リスク調整（risk_adjustment.py）
    - apply_sector_cap: セクター別保有比率が上限を超える場合、新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルト: bull=1.0, neutral=0.7, bear=0.3、未知レジームは 1.0 にフォールバックと警告）。
    - sell_codes を受けて当日売却予定銘柄をエクスポージャー計算から除外。
  - 株数決定 (position_sizing.py)
    - calc_position_sizes: allocation_method ごとに発注株数計算を実装（risk_based / equal / score）。
    - risk_based: risk_pct / stop_loss_pct に基づくシャア計算。等方式は weight と max_utilization を考慮。
    - 単元丸め（lot_size）、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）によるスケールダウン実装。スケールダウン時に残差を lot 単位で分配するロジックを搭載。
    - cost_buffer によりスリッページ・手数料分を保守的に見積もる。

- 戦略 (src/kabusys/strategy/)
  - 特徴量生成（feature_engineering.py）
    - research モジュールの生ファクターを統合し、ユニバースフィルタ（最低株価・最低平均売買代金）適用、Z スコア正規化、±3 でのクリップ、features テーブルへの日付単位 UPSERT（トランザクションで原子性を担保）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する純粋関数。
  - シグナル生成（signal_generator.py）
    - features と ai_scores を統合して最終スコア final_score を算出（momentum/value/volatility/liquidity/news の重み付き和、デフォルト重みを実装）。
    - シグモイド・正規化ユーティリティ、欠損コンポーネントの中立補完（0.5）等の安定化処理。
    - Bear レジーム検出時は BUY シグナル抑制。
    - SELL シグナルはストップロス（終値 vs avg_price）とスコア低下で判定。features 未登録の保有銘柄は score=0 として SELL 判定。
    - signals テーブルへ日付単位の置換（トランザクションで原子性を担保）。ROLLBACK の失敗は警告ログ出力。

- リサーチ（src/kabusys/research/）
  - ファクター計算（factor_research.py）
    - calc_momentum: 1m/3m/6m リターン、200 日 MA 乖離率を実装（データ不足時は None）。
    - calc_volatility: 20 日 ATR、atr_pct、avg_turnover、volume_ratio を実装。true_range の NULL 伝播を制御。
    - calc_value: raw_financials から最新財務を結合して PER/ROE を算出。
  - 特徴量探索ユーティリティ（feature_exploration.py）
    - calc_forward_returns: 複数ホライズンの将来リターンを 1 クエリで取得。horizons の検証（正の整数、<=252）を実装。
    - calc_ic: スピアマンのランク相関（ties を平均ランクとして扱う）を実装（有効サンプル < 3 の場合は None）。
    - rank / factor_summary: ランク変換と統計サマリ（count/mean/std/min/max/median）。
  - zscore_normalize を data.stats から再エクスポート。

- バックテスト（src/kabusys/backtest/）
  - ポートフォリオシミュレータ（simulator.py）
    - PortfolioSimulator: メモリ内で約定処理・ポジション管理・履歴保持を実装。
    - DailySnapshot / TradeRecord dataclass を定義。
    - execute_orders: SELL を先行処理してから BUY（SELL は保有全量クローズ。部分利確は未対応）、スリッページと手数料率を適用。
  - メトリクス計算（metrics.py）
    - CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算するユーティリティを実装。各計算は入力のスナップショット／トレードリストのみを参照。

- モジュールエクスポート
  - strategy, research, portfolio の主要関数を __init__ で公開。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 注記 / 既知の制約 (Notes / Known limitations)
- 設定周り
  - .env の読み込みでプロジェクトルートが見つからない場合は自動ロードをスキップする設計。
- position_sizing
  - lot_size は現状グローバル共通の単位（デフォルト 100）を想定。将来的に銘柄別単位への拡張を予定（TODO コメントあり）。
- risk_adjustment
  - apply_sector_cap では price_map に price が欠損（0.0）の場合、エクスポージャーが過少推定される可能性がある。将来的に前日終値や取得原価でのフォールバック検討（TODO コメント）。
- strategy / signal_generator
  - Bear レジームでは generate_signals の実装上 BUY シグナルが抑制される（仕様に基づく）。
  - 一部のエグジット条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
- research
  - calc_forward_returns はホライズンの上限を 252 営業日として検証。
- エラーハンドリング
  - DuckDB トランザクション時に例外発生した場合は ROLLBACK を試行し、さらに ROLLBACK に失敗した場合は警告ログを出す実装。

### セキュリティ (Security)
- （初回リリースのため該当なし）

---

今後の予定（例）
- 銘柄別 lot_size のサポート、price フォールバックロジック、トレーリングストップ等のエグジット条件追加、execution レイヤーの具体実装（kabu API 連携）などを計画。

変更・追加点のうち詳細が必要な箇所があれば指定してください。