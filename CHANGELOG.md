# Changelog

すべての重要な変更を時系列で記録します。フォーマットは「Keep a Changelog」に準拠します。

すべての非バグフィックス・改善・追加はこのファイルに記載してください。

## [0.1.0] - 2026-03-26
初回リリース。日本株自動売買システム「KabuSys」のコアモジュール群を追加しました。主な追加点・挙動は以下の通りです。

### 追加
- パッケージ基盤
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
  - パッケージエクスポート: data, strategy, execution, monitoring を公開。

- 設定管理
  - 環境変数・設定読み込みモジュールを追加（src/kabusys/config.py）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）を実装。
    - .env と .env.local の自動読み込みを実装（OS 環境変数優先、.env.local は上書き可能）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用）。
    - .env パーサは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行コメント処理などをサポート。
    - 保護（protected）キー群を用いた上書き制御（OS 環境変数の保護）。
    - Settings クラスで主要設定をプロパティで取得:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須取得（未設定時は ValueError を送出）。
      - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV にデフォルトとバリデーションを実装。
      - is_live / is_paper / is_dev のユーティリティプロパティを追加。

- ポートフォリオ構築（純粋関数）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: score 降順、同点は signal_rank 昇順で上位 N を返す。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分。全スコアが 0.0 の場合は等分配にフォールバックし WARNING を出力。
  - リスク調整（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター別既存保有比率が閾値を超える場合、同セクターの新規候補を除外。unknown セクターは除外対象としない。sell_codes を指定すると当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームはフォールバックで 1.0（警告ログ）。
  - 株数決定（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes:
      - allocation_method に "risk_based" / "equal" / "score" をサポート。
      - risk_based: risk_pct と stop_loss_pct に基づいて株数を算出。
      - equal/score: weights と portfolio_value を用いて per-position / aggregate 上限を適用。
      - lot_size による丸め（単元株対応）。
      - max_position_pct（1銘柄上限）、max_utilization（総投下上限）を反映。
      - cost_buffer を考慮した保守的な約定コスト見積りと aggregate cap のスケールダウン、残差配分ロジックを実装。

- 戦略: 特徴量・シグナル生成
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research モジュール（calc_momentum, calc_value, calc_volatility）から生ファクターを取得し、ユニバースフィルタ（最低株価、20日平均売買代金）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ（外れ値抑制）。
    - DuckDB を使い日付単位で置換（DELETE + BULK INSERT）するトランザクション処理で冪等性を確保。
    - デフォルトのフィルタ閾値: _MIN_PRICE=300 円、_MIN_TURNOVER=5e8 円、_ZSCORE_CLIP=3.0 など。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して final_score を計算（コンポーネント: momentum, value, volatility, liquidity, news）。
    - コンポーネント計算での補完ポリシー（欠損は中立 0.5）。
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10。weights 引数で補完・正規化を行う。
    - BUY 閾値のデフォルトは 0.60。Bear レジーム判定時は BUY を抑制（regime は ai_scores の regime_score 平均で判定）。
    - SELL（エグジット）判定: ストップロス（-8%）および final_score の閾値未満。features が存在しない保有銘柄は score=0.0 として SELL 判定。
    - signals テーブルへの書き込みは日付単位の置換で冪等性を確保。
    - 不正な weights をスキップし警告ログ出力。

- リサーチ（研究用ユーティリティ）
  - ファクター計算群（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m/3m/6m、ma200_dev を計算（200日未満は None）。
    - calc_volatility: 20日 ATR、atr_pct、avg_turnover、volume_ratio を計算（データ不足で None）。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を算出（EPS=0 は None）。
    - 期間・ウィンドウに関する定数を明確化（例: MA_LONG_DAYS=200, ATR_DAYS=20 等）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 翌日/翌週/翌月など複数ホライズンの将来リターンを1クエリで計算。
    - calc_ic: スピアマンのランク相関（IC）を実装（有効レコードが3件未満で None を返す）。
    - factor_summary / rank: 基本統計量、ランク計算（同順位は平均ランク、round による ties 対策）を提供。
  - research パッケージの __all__ を設定。

- バックテスト（メトリクス・シミュレータ）
  - メトリクス（src/kabusys/backtest/metrics.py）
    - BacktestMetrics dataclass を導入（cagr, sharpe_ratio, max_drawdown, win_rate, payoff_ratio, total_trades）。
    - history（DailySnapshot）および trades（TradeRecord）から上記指標を算出する関数群を実装。
    - CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio の計算ロジックを実装（境界条件の取り扱い含む）。
  - ポートフォリオシミュレータ（src/kabusys/backtest/simulator.py）
    - DailySnapshot / TradeRecord dataclass を定義。
    - PortfolioSimulator: メモリ内でのポートフォリオ管理・擬似約定を実装。
    - execute_orders: SELL を先に処理し BUY を後で処理（資金確保のため）。SELL は保有全量クローズ（部分利確は未対応）。
    - スリッページ率（BUY は +、SELL は -）と手数料率を反映した約定ロジック、lot_size に基づく部分約定サポート。
    - 履歴（history）と約定記録（trades）を保持し、後続のメトリクス計算に利用可能。

### 変更
- 初回リリースのため該当なし。

### 修正（バグ修正）
- 初回リリースのため該当なし。ただし以下の堅牢化を含む実装上の配慮あり:
  - .env パースでクォート内のバックスラッシュエスケープ対応や、インラインコメント処理を実装して想定外の .env 形式に耐性を持たせた。
  - DB 書き換え処理（features / signals）はトランザクション（BEGIN/COMMIT/ROLLBACK）で実装し、障害時に ROLLBACK を試行して警告ログを出す。

### 非推奨
- なし

### セキュリティ
- 環境変数は OS の環境変数を保護する仕組み（protected set）で扱い、.env ファイルによる上書きを制御可能。

---

注記:
- これはコードベース（2026-03-26 時点）の内容から推測して作成した CHANGELOG です。実際のリリースノートとして用いる際は、追加の変更点や後続コミットに基づき更新してください。