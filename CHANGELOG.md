# CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

なお、本CHANGELOGはリポジトリ内のソースコード（src/kabusys 以下）から機能・実装内容を推測して作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-26

### Added
- パッケージ初期リリース。
- パッケージメタ:
  - kabusys.__version__ = "0.1.0"
  - パッケージの公開 API を __all__ で定義（data, strategy, execution, monitoring）。
- 環境設定管理（kabusys.config）:
  - プロジェクトルート検出機能（.git または pyproject.toml を起点に探索）。
  - .env / .env.local の自動読み込み（OS 環境変数を保護する保護リスト機能、.env.local は .env を上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - .env パーサ実装（export プレフィクス対応、シングル/ダブルクォートのエスケープ処理、インラインコメント処理）。
  - 必須環境変数取得用の _require() と Settings クラス:
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL のバリデーション。
    - duckdb/sqlite のデフォルトパス取得（expanduser 対応）。
- ポートフォリオ構築（kabusys.portfolio）:
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順＋タイブレークで上位 N 件取得。
    - calc_equal_weights: 等配分重みの計算。
    - calc_score_weights: スコア比率に応じた重み計算（全スコアが 0 の場合は等配分へフォールバック、警告を出力）。
  - risk_adjustment:
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、セクター上限を超える場合は当該セクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルト値: bull=1.0, neutral=0.7, bear=0.3、未知レジームは 1.0 でフォールバックし警告）。
  - position_sizing:
    - calc_position_sizes: 株数決定ロジック（allocation_method: risk_based / equal / score をサポート）。
    - risk_based: 許容リスク率・損切り率に基づく株数算出、単元（lot_size）で丸め。
    - equal/score: 重み・ポートフォリオ比率・max_utilization を考慮した株数算出。
    - per-stock 上限（max_position_pct）や aggregate cap（available_cash）を考慮し、cost_buffer により手数料・スリッページを保守的に見積もる。スケールダウン時には端数調整ロジックを実装。
    - 未設定価格（price が None/<=0）の銘柄をスキップするログ出力あり。
    - 将来的な拡張点として銘柄別 lot_size を想定した設計注記あり。
- 戦略（kabusys.strategy）:
  - feature_engineering.build_features:
    - research モジュール（calc_momentum, calc_volatility, calc_value）から得た生ファクターをマージ。
    - ユニバースフィルタ（最低株価、20日平均売買代金）適用。
    - 指定カラムの Z スコア正規化（外れ値を ±3 にクリップ）。
    - features テーブルへの日付単位 UPSERT（トランザクションで冪等性を確保）。
    - DuckDB を用いる想定（prices_daily / raw_financials 参照）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - sigmoid による Z スコア → [0,1] 変換、欠損コンポーネントは中立 0.5 で補完。
    - デフォルトのファクター重み（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）と閾値（0.60）。
    - weights の検証・フォールバック（未知キーや無効値はスキップ、合計が 1 でなければ正規化）。
    - AI ベースのレジーム集計により Bear 相場判定（サンプル閾値あり）。Bear 時は BUY シグナル抑制。
    - SELL（エグジット）判定: ストップロス（終値/avg_price - 1 < -8%）と final_score < threshold。保有銘柄の価格欠損時は SELL 判定をスキップして警告。
    - signals テーブルへの日付単位置換（トランザクションで冪等）。
- リサーチ（kabusys.research）:
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと ma200_dev（200日移動平均乖離）を計算。データ不足は None。
    - calc_volatility: 20日 ATR（true range を厳密に扱う）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。必要行数が不足する場合は None。
    - calc_value: raw_financials から直近財務を取得し PER / ROE を計算（EPS=0 や欠損時は PER を None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算（有効レコード数 < 3 の場合は None）。
    - rank: 同順位の平均ランクを返す安定実装（round で比較の丸めを行い ties を扱う）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
- バックテスト（kabusys.backtest）:
  - simulator:
    - DailySnapshot / TradeRecord の dataclass。
    - PortfolioSimulator: メモリ内でのポートフォリオ状態管理と擬似約定ロジック。
    - execute_orders: SELL を先に処理して全量クローズ、BUY を後処理。スリッページ（BUY:+、SELL:-）・手数料率を適用。lot_size のサポート。約定記録（TradeRecord）を生成し history に保存する設計。
  - metrics:
    - BacktestMetrics dataclass と calc_metrics 集約関数。
    - 指標計算実装: CAGR（暦日ベース）、Sharpe（無リスク=0、年次化 252 営業日）、最大ドローダウン、勝率、ペイオフ比、総トレード数など。
    - 安全な入力検査（データ不足時は 0.0 を返す等）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- 環境変数自動読み込み時に OS 環境変数を保護する仕組みを導入（.env の上書き防止）。.env.local は明示的に上書き可能だが OS 環境変数は保護される。

---

注記 / 今後の拡張候補（ソース内の TODO・設計コメントからの抜粋）
- position_sizing: 将来的に銘柄別 lot_size（stocks マスターからの lot_map）をサポートする設計が示唆されている。
- risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる問題へのフォールバック実装（前日終値や取得原価の利用）を検討。
- signal_generator/_generate_sell_signals: トレーリングストップや時間決済（保有 60 営業日超過）は未実装で、positions テーブルに peak_price / entry_date 情報が必要。
- feature_engineering および signal_generator は DuckDB を前提としており、DB スキーマ（prices_daily, raw_financials, features, ai_scores, positions, signals 等）の整合性が必要。

以上。