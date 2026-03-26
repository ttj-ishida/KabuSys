CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを採用します。
初回リリース: 0.1.0

0.1.0 - 2026-03-26
------------------

Added
- パッケージ初版を追加（kabusys v0.1.0）。
  - パッケージエントリポイント:
    - src/kabusys/__init__.py にてバージョン管理と主要サブパッケージをエクスポート（data, strategy, execution, monitoring）。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロード無効化可能。
  - .env ファイルのパース実装:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理。
  - 環境変数必須チェック用ヘルパー _require。
  - Settings クラスで主要設定をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV の検証（development / paper_trading / live）と派生プロパティ is_live / is_paper / is_dev
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- ポートフォリオ構築関連（src/kabusys/portfolio/*）
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を選択。タイブレークは signal_rank を使用。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比率に基づく配分。全スコアが 0 の場合は等配分にフォールバック（WARNING ログ）。
  - risk_adjustment.py
    - apply_sector_cap: 現有ポジションのセクター比率が上限を超える場合、そのセクターの新規候補を除外（"unknown" セクターは無視）。
      - sell_codes 引数で当日売却予定銘柄を露出計算から除外可能。
      - 既知の制約: price が欠損（0.0）の場合露出が過少見積になる可能性（将来的にフォールバック価格の検討）。
    - calc_regime_multiplier: 市場レジーム（"bull" / "neutral" / "bear"）に応じた投下資金乗数（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバック（WARNING）。
  - position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数を計算（allocation_method: "risk_based" / "equal" / "score" をサポート）。
      - risk_based: 許容リスク率 (risk_pct) と stop_loss_pct に基づく株数算出。
      - equal/score: weight に基づく割当て、per-position 上限 (max_position_pct)、および aggregate cap によるスケーリング。
      - lot_size 単位での丸め処理、cost_buffer を用いた保守的コスト見積とスケール調整ロジック（fractional remainder による再配分）。
      - 将来的拡張点: 銘柄別の lot_size マップの導入を予定。

- 戦略関連（src/kabusys/strategy/*）
  - feature_engineering.py
    - build_features: research の生ファクター（calc_momentum / calc_volatility / calc_value）を統合し、
      ユニバースフィルタ（最低株価・最低売買代金）、Zスコア正規化（zscore_normalize を使用）、±3 でクリップ、features テーブルへ日付単位で UPSERT（トランザクション処理による原子性保証）。
    - ユニバース条件: 株価 >= 300 円、20日平均売買代金 >= 5億円。
  - signal_generator.py
    - generate_signals: features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
      - 標準重みの定義（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）を持ち、ユーザ指定 weights を検証・正規化。
      - component のシグモイド変換・欠損補完（欠損コンポーネントは中立値 0.5 を使用）。
      - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合）で BUY シグナルを抑制。
      - BUY 判定閾値（デフォルト 0.60）、SELL 判定（ストップロス -8% または final_score の閾値未満）。
      - SELL 優先ポリシー（SELL 対象は BUY から除外）、signals テーブルへ日付単位で置換して書き込み（トランザクション）。
      - ロギングと例外時のトランザクションロールバック処理を実装。

- リサーチ・統計（src/kabusys/research/*）
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None）を計算。
    - calc_volatility: 20日 ATR、atr_pct（ATR/close）、20日平均売買代金、出来高比率を計算（true_range の NULL 伝播に注意）。
    - calc_value: raw_financials から最新の財務データを取得し PER（EPS が 0/欠損なら None）と ROE を計算。
  - feature_exploration.py
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一回のクエリで取得。horizons の検証あり（<=252）。
    - calc_ic: ファクターと将来リターンのスピアマン ρ（ランク相関）を計算。有効レコードが 3 未満なら None。
    - factor_summary: 各ファクター列の基本統計（count/mean/std/min/max/median）を返す。
    - rank: 同順位を平均ランクで扱うランク付けユーティリティ（丸めによる ties 対応）。
  - research パッケージは zscore_normalize を data.stats から参照して統合。

- バックテスト（src/kabusys/backtest/*）
  - metrics.py
    - BacktestMetrics データクラスと calc_metrics 実装（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - 内部関数で各指標計算（年次化、営業日252日換算、勝率/ペイオフ比計算等）。
  - simulator.py
    - PortfolioSimulator: メモリ内でのポートフォリオ状態管理・擬似約定。
      - DailySnapshot / TradeRecord のデータクラス。
      - execute_orders: SELL を先に処理し全量クローズ、BUY を後処理。スリッページ（BUY:+, SELL:-）と手数料モデルを適用。
      - 部分約定・lot_size 管理、履歴と約定記録の保持。

Notes / Limitations
- 多くの関数は「純粋関数」または DB 接続を受け取る形で設計されており、副作用を最小化（execution 層・外部 API への直接依存なし）。
- 一部のフォールバックや拡張は TODO コメントあり:
  - risk_adjustment.apply_sector_cap: price 欠損時のフォールバック価格（前日終値や取得原価など）を将来検討。
  - position_sizing: 現状は単一 lot_size パラメータ。将来的に銘柄別 lot_map を受け取る構造を想定。
  - 一部の機能（例: トレーリングストップ、時間決済）は未実装（コメントで明記）。
- data.stats.zscore_normalize 等、参照しているユーティリティはコードベース内に存在（エクスポート参照）するが、本差分では詳細実装ファイルは表示されていません。
- 自動 .env 読み込みはプロジェクトルート特定に依存するため、パッケージ配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

Removed
- なし

Changed
- なし

Fixed
- なし

その他
- 本リリースは初版のため、API/仕様の安定化に伴い将来的に breaking change が発生する可能性があります。使用にあたってはソース内ドキュメント（PortfolioConstruction.md, StrategyModel.md, BacktestFramework.md 等の参照を想定）を併せて参照してください。