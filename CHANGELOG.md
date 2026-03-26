# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは "Keep a Changelog" の書式に準拠しています。  
バージョンは semantic versioning に従います。

なお、本 CHANGELOG は提供されたコードベースから推測して作成した初期リリースの概要です。

---

## [Unreleased]
- （なし）

---

## [0.1.0] - 2026-03-26

初期公開リリース。

### 追加 (Added)
- パッケージ概要
  - kabusys パッケージの初期バージョンを追加。パッケージメタ情報として src/kabusys/__init__.py に __version__ = "0.1.0" を定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機構:
    - プロジェクトルートを .git または pyproject.toml を基準に探索する _find_project_root() を実装（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は protected として上書き回避。
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル／ダブルクォート内でのバックスラッシュエスケープ処理をサポート。
    - クォートなし値内のコメント処理は「# の直前が空白/タブの場合のみコメント」として扱うロジック。
  - Settings による必須設定の取得メソッド（_require）とプロパティ:
    - J-Quants: jquants_refresh_token (JQUANTS_REFRESH_TOKEN)
    - kabuステーション: kabu_api_password (KABU_API_PASSWORD), kabu_api_base_url（デフォルト http://localhost:18080/kabusapi）
    - Slack: slack_bot_token (SLACK_BOT_TOKEN), slack_channel_id (SLACK_CHANNEL_ID)
    - DB: duckdb_path（デフォルト data/kabusys.duckdb）, sqlite_path（デフォルト data/monitoring.db）
    - システム: env（KABUSYS_ENV、valid: development/paper_trading/live）, log_level（LOG_LEVEL）
    - ヘルパープロパティ: is_live, is_paper, is_dev

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重（score / sum(scores)）。全スコアが 0 の場合は等金額へフォールバックし WARNING 出力。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限を適用。既存保有のセクター比率が所定上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象としない）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数を返す（"bull"=1.0, "neutral"=0.7, "bear"=0.3）。未知レジームは 1.0 でフォールバック（WARNING）。
  - position_sizing:
    - calc_position_sizes: 発注株数算出（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元丸め（lot_size）、1銘柄上限（max_position_pct）、aggregate cap（available_cash に基づくスケーリング）、cost_buffer による保守的コスト見積りなどを実装。
    - risk_based: 許容リスク率 risk_pct と stop_loss_pct を用いたポジションサイズ算出。
    - equal/score: weight に基づく配分（max_utilization を考慮）。
    - スケーリング後は残余キャッシュを用いて fractional remainder が大きい順に lot_size 単位で追加配分するロジックを実装。
    - TODO コメント: 将来的に銘柄別 lot_size（lot_map）への拡張を想定。

- 戦略・特徴量 (src/kabusys/strategy/)
  - feature_engineering:
    - build_features: research モジュールの calc_momentum / calc_volatility / calc_value を組み合わせて特徴量を作成。ユニバースフィルタ（最低株価、20日平均売買代金）適用、Zスコア正規化（±3 クリップ）、features テーブルへ日付単位の置換（冪等 upsert）。
  - signal_generator:
    - generate_signals: features と ai_scores を統合し、component スコア（momentum/value/volatility/liquidity/news）を計算。final_score を算出して BUY/SELL シグナルを生成し、signals テーブルへ日付単位の置換。
    - ベアレジーム（AI レジームスコア平均が負）では BUY を抑制。
    - SELL 判定にはストップロス（-8%）とスコア低下（threshold 未満）を実装。保有銘柄の価格欠損時は SELL 判定をスキップ（WARNING）。
    - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防止。
    - デフォルト重みと閾値は StrategyModel.md に準拠（デフォルト weights・threshold を採用）。外部から渡された weights は妥当性検査・正規化される。

- リサーチ (src/kabusys/research/)
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB の prices_daily から計算（データ不足時は None）。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（true_range の NULL 伝播を慎重に扱う）。
    - calc_value: raw_financials から最新財務を参照して PER / ROE を計算（EPS が 0 または NULL の場合は PER=None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: Spearman ランク相関（IC）を計算。サンプル数 3 未満は None を返す。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクを採るランク関数（浮動小数の丸めで ties 検出を安定化）。
  - research パッケージは zscore_normalize を外部にエクスポート。

- バックテスト (src/kabusys/backtest/)
  - simulator:
    - PortfolioSimulator: メモリ内でポートフォリオ状態を管理し、擬似約定を行う。SELL を先、BUY を後に処理。BUY の部分約定や単元処理をサポート。TradeRecord / DailySnapshot のデータモデルを定義。
    - スリッページ（BUY:+、SELL:-）と手数料（commission_rate）モデルを想定。
  - metrics:
    - calc_metrics: DailySnapshot と TradeRecord を基にバックテスト評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）を計算。

- パッケージエクスポート整理
  - 各サブパッケージの __init__.py で主要な関数をエクスポート（strategy, portfolio, research など）。

### 変更 (Changed)
- 初期リリースのため過去バージョンからの変更は無し（ベース実装として追加のみ）。

### 既知の問題・制約 (Known issues / Notes)
- .env パーサー/ロード
  - .env 読み込みはプロジェクトルート検出に依存するため、配布後や特殊な配置では自動ロードが意図した通り動作しない可能性がある。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動ロードを行うことを推奨。
- apply_sector_cap
  - price_map に価格が欠損（0.0）だとエクスポージャーが過少見積りされ、ブロックが想定より緩くなる可能性がある（TODO: フォールバック価格の検討）。
- generate_signals
  - SELL の一部のエグジット条件（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date が必要なため将来の拡張予定あり。
  - ai_scores が未登録の場合のレジーム判定はサンプル数依存（デフォルト: 最低 3 サンプル）。サンプル不足時は Bear と見なさない。
- position_sizing
  - 将来的な拡張として銘柄別 lot_size（lot_map）をサポートする予定（現在は全銘柄共通 lot_size）。
- calc_regime_multiplier
  - 未知レジームは 1.0 でフォールバック。ログに WARNING を出力するのみ。
- DuckDB 依存
  - feature_engineering / strategy / research の多くの関数は DuckDB 接続と特定のテーブル（prices_daily, raw_financials, features, ai_scores, positions, signals）構造に依存する。テーブルスキーマ・存在を前提とするため、本番導入時は DB の準備が必要。

### 将来の改善予定 (Planned)
- position_sizing: 銘柄別単元サイズ対応（lot_map）。
- apply_sector_cap: 欠損価格に対する価格フォールバック（前日終値や取得原価など）。
- signal_generator: トレーリングストップや時間決済などの追加エグジット条件の実装。
- API 層 / execution 層との統合・テストケース整備。

### セキュリティ (Security)
- 設定値（トークンやパスワード）は環境変数で要求されるため、運用時は環境変数管理に注意してください。自動 .env ロードは便利だが、機密情報管理には適切な運用ポリシーを推奨。

---

参照: 本 CHANGELOG は提供されたコードの実装・コメントから推測して作成した要約です。実際のリリースノートとして利用する際は、テスト結果や API 仕様の確定に基づき適宜修正してください。