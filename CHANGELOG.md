# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
このファイルはコードベースから推測して作成した初回リリース向けの変更履歴です。

注: バージョン番号はパッケージ定義 (kabusys.__version__) に基づきます。

## [Unreleased]


## [0.1.0] - 2026-03-26

### Added
- 初回リリース: KabuSys — 日本株自動売買システムのコアライブラリを追加。
  - パッケージバージョン: 0.1.0

- 環境・設定管理
  - 自動 .env 読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env / .env.local の読み込み順序: OS 環境 > .env.local (上書き) > .env（既存変数は上書きしない）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - 強制取得ヘルパー _require を実装し、必須環境変数未設定時に ValueError を送出。
  - 主要な設定プロパティを持つ Settings クラスを追加（settings インスタンスをエクスポート）。
    - 必須環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - 任意設定例: KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi), DUCKDB_PATH (data/kabusys.duckdb), SQLITE_PATH (data/monitoring.db)
    - KABUSYS_ENV の検証（development / paper_trading / live のみ許容）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- ポートフォリオ構築 (kabusys.portfolio)
  - 候補選定:
    - select_candidates(buy_signals, max_positions): score 降順、同点は signal_rank の昇順で上位 N を返す。
  - 重み計算:
    - calc_equal_weights(candidates): 等金額配分 (1/N) を返す。
    - calc_score_weights(candidates): スコア比率で正規化。スコア合計が 0 の場合は等配分へフォールバックし WARNING を出力。
  - リスク制御:
    - apply_sector_cap(...): 既存保有のセクター露出が閾値を超える場合に同セクターの新規候補を除外。
      - unknown セクターは制限対象外。
      - sell_codes を渡すと当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier(regime): 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバック（警告ログ）。
  - ポジションサイジング:
    - calc_position_sizes(...): allocation_method に応じた発注株数計算を実装（"risk_based" / "equal" / "score"）。
      - 単元 (lot_size) に基づく丸め、1 銘柄上限 (max_position_pct)、合計利用可能現金 (available_cash) に対する aggregate cap、cost_buffer による保守的見積もり、スケーリングと端数配分アルゴリズムを実装。
      - price 欠損や価格 <= 0 のケースでログ出力してスキップ。

- 戦略モジュール (kabusys.strategy)
  - 特徴量エンジニアリング:
    - build_features(conn, target_date): research 側のファクター関数から生ファクターを取得、ユニバースフィルタ（最低株価・最低売買代金）、Z スコア正規化（対象カラムを ±3 でクリップ）、features テーブルへの日付単位の置換（トランザクション）を実装。
    - 期待される参照テーブル: prices_daily, raw_financials
  - シグナル生成:
    - generate_signals(conn, target_date, threshold=0.6, weights=None): features と ai_scores を統合して final_score を算出し BUY / SELL シグナルを生成して signals テーブルへ書き込む（トランザクションで日付単位置換）。
      - デフォルト重みは StrategyModel.md に基づく (momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10)。ユーザ渡しの weights は既知キーのみ受け付け、合計が 1.0 に再スケール。
      - AI スコア未登録時はニューススコアを中立 (0.5) で補完。
      - Bear レジーム判定（ai_scores.regime_score の平均が負で充分なサンプル数がある場合）では BUY シグナルを抑制。
      - SELL 条件としてストップロスとスコア低下を実装。SELL 優先で BUY から除外。
      - features 空時は BUY 生成なし、SELL 判定のみ実施。

- リサーチモジュール (kabusys.research)
  - ファクター計算:
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m、ma200_dev を計算。
    - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio を計算。
    - calc_value(conn, target_date): per, roe を raw_financials と prices_daily から計算。
  - 探索・評価ユーティリティ:
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 指定ホライズンの将来リターンを一括取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン IC（ランク相関）を計算。サンプル 3 未満で None。
    - factor_summary(records, columns): count/mean/std/min/max/median を返す。
    - rank(values): 同順位は平均ランクで扱うランク関数。
  - いずれも DuckDB 接続を受け、prices_daily / raw_financials テーブルのみ参照する設計。

- バックテスト (kabusys.backtest)
  - メトリクス:
    - BacktestMetrics dataclass と calc_metrics(history, trades) を追加（CAGR、Sharpe、MaxDrawdown、WinRate、PayoffRatio、TotalTrades）。
  - シミュレータ:
    - PortfolioSimulator: メモリ内でポートフォリオ状態を保持し擬似約定を行う。SELL を先に、BUY を後に処理。SELL は保有全量をクローズ（部分買い／売りの挙動は限定）。
    - TradeRecord / DailySnapshot のデータモデルを提供。
    - スリッページ率・手数料率を反映した約定処理（BUY は +slippage、SELL は -slippage を想定）。
    - lot_size による部分約定制御をサポート。

- パッケージ公開インターフェース
  - top-level __all__ などで主要モジュールをエクスポート（strategy.build_features, strategy.generate_signals, portfolio.* 関数など）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数の取り扱いに注意: .env ファイルを自動読み込みするため、シークレット管理には運用上の配慮が必要（.env.local の優先度等を理解の上で使用してください）。

### Known issues / TODO / 実装上の注意
- apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過小見積もりされ、想定外にブロックされない可能性がある。将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO コメントあり。
- calc_position_sizes:
  - 単元株 (lot_size) は現状グローバル共通値で処理。将来的に銘柄毎の lot_map に拡張する TODO がある。
- generate_signals:
  - SELL の追加条件（トレーリングストップ・時間決済）は未実装（StrategyModel に記載の通り、positions テーブルに peak_price / entry_date が必要）。
  - features が存在しない保有銘柄は final_score=0 と見なして SELL 判定される点に注意（警告ログを出力）。
- config .env パーサ:
  - シェル風の export プレフィックスやクォート・エスケープ、インラインコメントルールに対応するパーサ実装あり。特殊ケースでは期待通りにパースできない可能性があるため .env の書式は .env.example に従うこと。
- テスト/堅牢性:
  - DuckDB を用いた SQL 依存部分はテーブル構造（prices_daily, raw_financials, features, ai_scores, positions, signals 等）に依存するため、実行前にスキーマ準備が必要。
- ロギング:
  - 内部で警告・デバッグログを出す実装が多数あるため、本番運用時は Settings.log_level を適切に設定すること。

---

（この CHANGELOG はコードベースの内容から自動的に推測して作成しています。実際の仕様書・設計書と差異がある可能性があります。必要に応じて実装者による追記・修正をお願いします。）