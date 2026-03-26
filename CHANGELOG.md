# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルはコードベース（src/kabusys 以下）の実装内容から推測して作成しています。

現在のバージョンは 0.1.0 です（src/kabusys/__init__.py の __version__ に基づく）。

[Unreleased]
- なし

[0.1.0] - 2026-03-26
Added
- パッケージ初期実装: kabusys 名前空間パッケージを追加。
  - src/kabusys/__init__.py にてバージョン "0.1.0"、公開サブパッケージを設定（data, strategy, execution, monitoring）。

- 環境変数 / 設定管理モジュールを追加（kabusys.config）。
  - .env/.env.local の自動ロード機能（プロジェクトルートを .git または pyproject.toml から探索して読み込み）。
  - .env パーサ実装: export 形式、クォート、バックスラッシュエスケープ、インラインコメントの扱いなどをサポート。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供:
    - 必須項目の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - デフォルト値付き設定: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV。
    - env/log_level のバリデーション（許容値セットをチェック）。
    - ユーティリティプロパティ: is_live / is_paper / is_dev。

- ポートフォリオ構築関連モジュールを追加（kabusys.portfolio）。
  - portfolio_builder:
    - select_candidates: score 降順、同点時は signal_rank 昇順で最大件数を選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（全スコアが 0 の場合は等分へフォールバック、警告ログ）。
  - risk_adjustment:
    - apply_sector_cap: 同一セクターの既存エクスポージャーが上限を超える場合に当該セクターの新規候補を除外。sell_codes による当日売却予定銘柄の除外対応。unknown セクターはセクター上限の対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告を出して 1.0 にフォールバック。
  - position_sizing:
    - calc_position_sizes: 複数配分方式に対応（risk_based / equal / score）。
      - risk_based: 許容リスク率・損切り率に基づいてターゲット株数を計算し単元（lot_size）で丸める。
      - equal/score: weight に基づき per-position と aggregate の上限を考慮して株数算出。
      - aggregate cap スケーリング: available_cash を超える場合のスケールダウン、fractional remainder を考慮した lot_size 単位での再配分アルゴリズムを実装。
      - max_position_pct, max_utilization, cost_buffer（スリッページ・手数料の保守見積り）をサポート。
      - 単元丸め、価格欠損時のスキップなどの挙動を明示。

- ストラテジー関連モジュールを追加（kabusys.strategy）。
  - feature_engineering:
    - build_features: research モジュール（calc_momentum / calc_volatility / calc_value）から得た生ファクターを統合、ユニバースフィルタ（最低株価・最低平均売買代金）を適用、Z スコア正規化（±3 にクリップ）、DuckDB の features テーブルへ日付単位の置換（トランザクションで原子性確保）。
    - ユニバース基準: 最低株価 300 円、20日平均売買代金 5 億円。正規化対象カラムやクリップ値は定数で管理。
  - signal_generator:
    - generate_signals: features と ai_scores を統合して final_score を計算。component（momentum/value/volatility/liquidity/news）の計算関数を実装（シグモイド変換、欠損値は中立 0.5 で補完）。
    - Bear レジーム検知: ai_scores の regime_score 平均が負なら Bear（ただし最小サンプル数 3 を要求）、Bear の場合 BUY を抑制。
    - BUY: threshold（デフォルト 0.60）超で BUY シグナル生成、スコア降順でランク付け。
    - SELL（エグジット）判定: ストップロス（終値/avg_price -1 < -8%）および final_score の閾値割れを実装。保有銘柄の価格欠損時は SELL 判定をスキップする安全策を用意。
    - signals テーブルへの日付単位置換（トランザクションで原子性確保）。
    - weights の入力検証（未知キー無視、負値/非数値/NaN/Inf を無視、合計が 1 でない場合は再スケール）。

- Research（研究）モジュールを追加（kabusys.research）。
  - factor_research:
    - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を参照してモメンタム、ATR/流動性、PER/ROE 等を計算。ウィンドウ要件（MA200/ATR20）未満のものは None を返す。
    - calc_value は target_date 以前の最新財務データを用いる（ROW_NUMBER により最新レコードを選択）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算、horizons のバリデーション。
    - calc_ic: ファクターと将来リターンの Spearman（ランク相関）を計算。サンプル数 3 未満なら None。
    - factor_summary: count/mean/std/min/max/median を算出する軽量統計ユーティリティ。
    - rank: 同順位は平均ランクで処理（丸めによる ties 対応）。

- バックテスト関連モジュールを追加（kabusys.backtest）。
  - metrics:
    - BacktestMetrics dataclass と各種評価指標の計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - 標本不足や異常値への堅牢性を考慮した実装（ゼロ除算回避等）。
  - simulator:
    - PortfolioSimulator: メモリ内ポートフォリオ状態管理、擬似約定ロジック。
      - DailySnapshot / TradeRecord dataclass を定義。
      - execute_orders: SELL を先に実行し（保有全量をクローズするポリシー）、その後 BUY を実行。スリッページ sign（BUY +、SELL -）、手数料率の扱い、lot_size による丸めをサポート。

- パッケージの公開 API を整理（各モジュール __init__ の __all__ / import を通じてエクスポート）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated / Removed / Security
- 初回リリースのため該当なし。

Notes / Known limitations
- apply_sector_cap 内で price_map に価格が欠損（0.0）だとエクスポージャーが過少見積もられる旨の TODO がある。将来的に前日終値や取得原価でフォールバックすることが検討されている。
- position_sizing は現状で全銘柄共通の lot_size を前提にしている。将来的に銘柄別 lot_map を受け付ける拡張が予定されている（TODO コメントあり）。
- signal_generator のエグジット条件は基本的なストップロス・スコア低下を実装済み。トレーリングストップや時間決済（保有日数ベース）は未実装（positions テーブルに peak_price / entry_date が必要との注記あり）。
- calc_value では PBR・配当利回りは現バージョンでは未実装。
- research.feature_exploration は外部依存（pandas 等）を使わない設計だが、大規模データでの性能は DuckDB のクエリ設計に依存する。
- execution パッケージは空の初期化ファイル（stub）になっており、実際の発注 API 連携実装は含まれていない。
- 提供コードスニペットの末尾で _execute_buy の一部が切れている（表示上の省略）。実際の実装では BUY の単元丸め・資金チェック等が行われる想定。

Migration / Usage notes
- .env 自動ロードはデフォルトで有効。テストや CI で自動ロードを防ぐには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数が未設定の場合 Settings のプロパティアクセスで ValueError が発生します（早期検出を推奨）。
- DuckDB を用いる設計のため、features / prices_daily / raw_financials / ai_scores / positions / signals 等のスキーマ整備が前提です（各モジュールはこれらテーブルを参照／書き込みします）。

もし CHANGELOG に項目の追加やリリース日・バージョン体系の修正を希望する場合、あるいはリリースノートの英訳やより詳細な「変更点ごとのコード参照（関数名やファイルパス）」を追加したい場合は指示してください。