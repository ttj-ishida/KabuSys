# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。Semantic Versioning に準拠します。

## [0.1.0] - 2026-03-26

初回リリース。本リポジトリのコア機能（環境設定、ポートフォリオ構築、戦略の特徴量・シグナル生成、リサーチユーティリティ、バックテストシミュレータ等）を提供します。

### 追加 (Added)
- パッケージ初期化
  - パッケージ名: kabusys、バージョン: 0.1.0
  - 公開 API: data, strategy, execution, monitoring を __all__ に登録。

- 環境設定モジュール (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード実装。
  - プロジェクトルート探索: .git または pyproject.toml を用いて __file__ から親ディレクトリを探索する安全なルート検出。
  - .env パーサ:
    - コメント行・空行の無視、`export KEY=val` 形式対応。
    - シングル/ダブルクォート内のエスケープ処理に対応（バックスラッシュ処理）。
    - クォートなしの場合、`#` がスペース/タブで区切られているときのみインラインコメントとして扱う。
  - .env 読み込みの優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は protected として上書き不可。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用）。
  - Settings クラスを提供:
    - J-Quants / kabu API / Slack / データベースパスなどの取得プロパティ。
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等の既定値。
    - 入力検証: KABUSYS_ENV (development/paper_trading/live) と LOG_LEVEL の値チェック。
    - ヘルパープロパティ: is_live / is_paper / is_dev。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順ソート、同点時は signal_rank をタイブレーク。
    - calc_equal_weights: 等分配。
    - calc_score_weights: スコア比率で配分、全スコアが 0 の場合に等分配へフォールバック（WARNING ログ）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中を抑えるため、既存保有比率が上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear マップ、未知レジームは 1.0 にフォールバックして WARNING）。
    - sell_codes 引数で当日売却予定銘柄をエクスポージャー計算から除外可能。
    - TODO: price 欠損時のフォールバックロジックについて注記あり。
  - position_sizing:
    - calc_position_sizes: allocation_method に応じた株数計算を実装（"risk_based", "equal", "score"）。
    - risk_based: 許容リスク率と stop_loss からベース株数を計算。
    - equal/score: 重みに基づく配分、max_utilization による per-position 上限考慮。
    - lot_size による単元丸め（現在グローバルな lot_size パラメータ）。
    - _max_per_stock による 1 銘柄上限（portfolio_value ベース）。
    - aggregate cap: 全銘柄合計投資額が available_cash を超える場合のスケーリングと、端数（lot 単位）を残余キャッシュで分配する実装。cost_buffer を使った保守的見積り（スリッページ・手数料考慮）。
    - 価格欠損時は当該銘柄をスキップ。

- 戦略: 特徴量計算とシグナル生成 (kabusys.strategy)
  - feature_engineering.build_features:
    - research モジュール（calc_momentum / calc_volatility / calc_value）から生ファクターを取得しマージ。
    - ユニバースフィルタ: 最低株価 300 円、20 日平均売買代金 5 億円を適用。
    - 指定カラムの Z スコア正規化・±3 クリップ。
    - DuckDB への日付単位置換（DELETE + bulk INSERT）で冪等な upsert を実行。
  - signal_generator.generate_signals:
    - features / ai_scores / positions を参照して final_score を計算（momentum/value/volatility/liquidity/news の重み合成）。
    - コンポーネントスコアは sigmoid や補完（欠損は中立 0.5）で処理。
    - AI スコア未登録時は中立補完、レジームスコアを集計して Bear 判定（サンプル数閾値あり）→ Bear の場合 BUY を抑制。
    - SELL シグナル生成: ストップロス（-8%）および final_score の閾値未満によるエグジットを実装。価格欠損時は SELL 判定をスキップして WARNING。
    - weights 引数はデフォルト重みへフォールバック、無効なキー/値を除外し正規化。
    - signals テーブルへの日付単位置換で冪等に書き込み。

- リサーチユーティリティ (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと MA200 偏差（200行未満は None）。
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率。
    - calc_value: latest raw_financials（target_date 以前）と当日終値から PER/ROE を計算。
  - feature_exploration:
    - calc_forward_returns: LEAD を使った複数ホライズン同時取得。horizons のバリデーション。
    - calc_ic: factor と将来リターンの Spearman ランク相関（ties の平均ランク処理含む）、有効レコードが 3 未満の場合は None。
    - factor_summary: count/mean/std/min/max/median を算出（None を除外）。
    - rank: 同順位は平均ランク。round(v, 12) による ties 検出安定化。
  - research パッケージから主要関数をエクスポート。

- バックテスト (kabusys.backtest)
  - metrics.calc_metrics: DailySnapshot と TradeRecord から各種評価指標（CAGR、Sharpe、MaxDrawdown、Win rate、Payoff ratio、total_trades）を計算。
  - simulator.PortfolioSimulator:
    - メモリ内でのポートフォリオ管理・擬似約定を実装。
    - 日次スナップショット（DailySnapshot）と約定記録（TradeRecord）を保持。
    - execute_orders:
      - SELL を先に処理して資金を確保、SELL は保有全量クローズ（部分利確非対応）。
      - BUY は指定株数で約定。slippage_rate と commission_rate を考慮して約定価格・手数料を計算。
      - trading_day, lot_size パラメータ対応。
    - Backtest 用のモデル（スリッページ・手数料）に沿った実装。

- 内部ユーティリティ
  - kabusys.data.stats.zscore_normalize が使用される設計（research / strategy と連携）。

### 変更 (Changed)
- 初期リリースのため変更履歴はありません（ベースライン実装）。

### 修正 (Fixed)
- 初期リリースのため修正履歴はありません。

### 既知の制約・注意点 (Known issues / Notes)
- risk_adjustment.apply_sector_cap: price_map に 0.0/欠損があるとエクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO がある。
- position_sizing では現状単一の lot_size を使用。将来的には銘柄別 lot_map への拡張検討。
- signal_generator の一部エグジットルール（トレーリングストップや時間決済）は未実装で、positions テーブルに peak_price / entry_date が必要。
- generate_signals の Bear 判定は ai_scores の regime_score サンプル数が閾値未満の場合は Bear とみなさない（誤判定防止の設計）。
- PortfolioSimulator の SELL は全量クローズのみ（部分エグジット非対応）。

### 互換性の破壊 (Breaking Changes)
- 初回リリースのため互換性破壊の記載なし。

### セキュリティ (Security)
- 特になし。

---

今後のリリースでは以下の改善を予定しています（例示）:
- position_sizing の銘柄別 lot_size 対応。
- risk_adjustment の price フォールバック強化（前日終値・取得原価）。
- signal_generator のトレーリングストップ・時間決済の実装。
- execution 層と実際の発注 API 連携実装（現在 execution パッケージはプレースホルダ）。