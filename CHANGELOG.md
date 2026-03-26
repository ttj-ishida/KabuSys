# Changelog

すべての重要な変更は「Keep a Changelog」仕様に準拠して記載しています。ソフトウェアのバージョンは semantic versioning に従います。

## [0.1.0] - 2026-03-26
初回リリース（ベースライン機能を実装）

### 追加 (Added)
- パッケージ基盤
  - パッケージ `kabusys` の初期バージョンを追加。__version__ = 0.1.0。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に定義。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサの実装:
    - export KEY=val 形式対応、クォート文字列のバックスラッシュエスケープ対応、インラインコメント処理、
    - 無効行・コメント行の無視。
  - 環境変数取得用ユーティリティ _require と各種プロパティを追加（J-Quants、kabu API、Slack、DB パス、env/log_level フラグ、is_live / is_paper / is_dev）。
  - 環境値検証: KABUSYS_ENV, LOG_LEVEL の有効値チェック。

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定: select_candidates — スコア降順＋signal_rankによるタイブレークで上位 N 選出。
  - 重み計算:
    - calc_equal_weights — 等金額配分。
    - calc_score_weights — スコア加重配分（全スコアが 0 の場合は等金額にフォールバックし警告を出力）。
  - セクターリスク制御・レジーム乗数（kabusys.portfolio.risk_adjustment）:
    - apply_sector_cap — 既存保有のセクター比率が上限を超える場合、当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier — market regime（bull/neutral/bear）に応じた投下資金乗数（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバックし警告を出力。
  - ポジションサイジング（kabusys.portfolio.position_sizing）:
    - calc_position_sizes — allocation_method に応じて発注株数計算 ("risk_based", "equal", "score")。
    - risk_based: 許容リスク率（risk_pct）と stop_loss_pct を用いた株数算出。
    - equal/score: weight に基づく配分、lot_size（単元）で丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）によるスケーリング、cost_buffer による保守的見積もり。
    - aggregate スケールダウン時は残差を lot 単位で再配分（再現性を保つ安定ソート）。
    - TODO を残す設計メモ: 将来的な銘柄別 lot_size への拡張。

- 戦略（kabusys.strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - build_features: research の生ファクターを取得（calc_momentum, calc_volatility, calc_value）、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）、Z スコア正規化、±3 でクリップ、DuckDB に対する日付単位の置換（冪等）を実装。
  - シグナル生成（kabusys.strategy.signal_generator）
    - generate_signals: features, ai_scores, positions を参照してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、最終スコア final_score を算出。
    - デフォルト重みや閾値: weights のデフォルトを実装（momentum 0.40 等）、デフォルト閾値 _DEFAULT_THRESHOLD=0.60。
    - AI スコアは未登録時に中立（0.5）で補完。
    - Bear レジーム検知時は BUY シグナルを抑制（レジーム判定は ai_scores の regime_score 平均を使用; 最低サンプル数チェックあり）。
    - 売りシグナル（エグジット）判定を実装（ストップロス -8%、final_score が閾値未満）。
    - signals テーブルへの日付単位の置換（冪等性）。SELL は BUY より優先し、SELL 対象は BUY から除外してランク再付与。
    - 未実装機能としてトレーリングストップや時間決済などを明記。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials のみ参照）。
    - momentum: 1M/3M/6M リターン、200 日移動平均乖離率（データ不足時は None）。
    - volatility: 20 日 ATR の算出、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
    - value: target_date 以前の最新財務データと株価を組み合わせて PER/ROE を算出（EPS が 0 または欠損時は None）。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns — 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得。
    - calc_ic — Spearman のランク相関（IC）を実装（有効データが 3 件未満は None を返す）。
    - factor_summary — 各ファクターの基本統計量（count/mean/std/min/max/median）。
    - rank — 同順位は平均ランクとするランク付けユーティリティ。
  - 実装方針: DuckDB と標準ライブラリのみを用いる、pandas 等に非依存。

- バックテスト（kabusys.backtest）
  - シミュレータ（kabusys.backtest.simulator）
    - PortfolioSimulator: メモリ上でのポートフォリオ状態管理、SELL を先に約定してから BUY を実行、部分利確や部分損切りは未対応、TradeRecord/DailySnapshot のデータ構造を提供。
    - 約定ロジックはスリッページ（BUY:+, SELL:-）と手数料率を考慮。lot_size パラメータで単元を扱える設計（デフォルト 1）。
  - メトリクス（kabusys.backtest.metrics）
    - calc_metrics を実装: CAGR、Sharpe、Max Drawdown、Win Rate、Payoff Ratio、total_trades を計算。
    - 各計算で安全策（データ不足時の 0.0 フォールバック、分母ゼロチェック等）を実装。

- 共通ユーティリティ参照
  - 複数モジュールで kabusys.data.stats.zscore_normalize を利用する設計（実体は data モジュールに実装されている想定）。

### 変更 (Changed)
- N/A（初回リリースのため過去からの変更なし）

### 修正 (Fixed)
- N/A（初回リリースのため修正履歴なし）

### 非推奨 (Deprecated)
- N/A

### 削除 (Removed)
- N/A

### セキュリティ (Security)
- N/A

### 既知の制約・未実装点（注記）
- position_sizing: 銘柄ごとの単元（lot_size）のマスター連携は未実装（全銘柄共通 lot_size を想定）。将来的な拡張をコメントとして残しています。
- signal_generator: トレーリングストップや時間決済などの一部エグジットルールは未実装（positions テーブルに peak_price / entry_date 等が必要）。
- apply_sector_cap: 価格データ欠落時にエクスポージャーが過少見積りされる可能性あり。将来的に前日終値や取得原価でのフォールバックを検討。
- research モジュールは DuckDB と標準ライブラリで実装する設計のため、pandas 等の外部依存を含みません（その分、SQL ベースの集約を多用）。

---
この CHANGELOG はコードベースの実装内容から推測して作成した初版の変更履歴です。将来のリリースでは機能追加・修正・破壊的変更などをここに追記してください。