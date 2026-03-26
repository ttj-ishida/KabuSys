# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

※日付は本リリース作成日です。

## [0.1.0] - 2026-03-26

### 追加
- 初期リリース。日本株自動売買システムのコアライブラリを追加。
  - パッケージ情報
    - パッケージ名: kabusys
    - バージョン: 0.1.0
    - エクスポート: data, strategy, execution, monitoring（パッケージルート）
  - 環境設定・自動 .env ロード（kabusys.config）
    - プロジェクトルートを .git または pyproject.toml を基準に自動検出して .env / .env.local を読み込む。
    - OS 環境変数は保護され、.env.local が .env を上書きする（override 動作）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export 形式・クォート・インラインコメント・エスケープに対応。
    - Settings クラスで主要設定をプロパティとして提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH）。
    - KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL を検証して不正値は ValueError を送出。
  - ポートフォリオ構築（kabusys.portfolio）
    - portfolio_builder:
      - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）でソートし上位 N を選択。
      - calc_equal_weights: 等金額配分を返す。
      - calc_score_weights: スコア比率に基づく重みを計算。全スコアが 0 の場合は等金額にフォールバック（WARNING ログ）。
    - risk_adjustment:
      - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、指定比率（デフォルト 30%）を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（"bull":1.0, "neutral":0.7, "bear":0.3）。未知のレジームは 1.0 にフォールバック（WARNING）。
    - position_sizing:
      - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応した株数計算。
        - risk_based: 許容リスク率（risk_pct）と stop_loss_pct から目標株数を算出。
        - equal/score: weight（=1正規化前提）に基づき portfolio_value と max_utilization から算出。
        - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）によるスケールダウン、cost_buffer を使った保守的見積りを実装。
  - 戦略（kabusys.strategy）
    - feature_engineering.build_features:
      - research モジュールで計算した生ファクター（momentum / volatility / value）を取得。
      - 株価・流動性によるユニバースフィルタ（デフォルト: 株価 >= 300 円、20 日平均売買代金 >= 5 億円）。
      - 数値ファクターを Z スコア正規化し ±3 でクリップ。
      - DuckDB に対して日付単位で置換（DELETE + bulk INSERT）することで冪等性と原子性を確保。
    - signal_generator.generate_signals:
      - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントから final_score を計算（デフォルト重みあり）。
      - AI スコア（ai_score）をニューススコアとして統合。未登録は中立補完。
      - レジーム判定（ai_scores の regime_score 平均）により Bear の場合は BUY シグナルを抑制。
      - BUY は閾値（デフォルト 0.60）超の銘柄を生成。SELL はストップロス（-8%）とスコア低下によるエグジット判定を実施。
      - SELL 優先ポリシー: SELL 対象は BUY から除外、ランクを再付与。
      - weights の検証・フォールバック（未知キー・非数値は無視、合計が 1 に正規化）。
      - 日付単位で signals テーブルを置換（トランザクション処理）。
  - 研究ユーティリティ（kabusys.research）
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（200 行未満は None）。
      - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、volume_ratio。
      - calc_value: raw_financials の最新財務データを用いた PER / ROE（EPS が 0 または欠損なら PER は None）。
    - feature_exploration:
      - calc_forward_returns: target_date の終値から指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一括取得。
      - calc_ic: factor と将来リターンのスピアマン ρ（ランク相関）を計算。サンプルが 3 未満なら None。
      - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）を返す。
      - rank: 同順位は平均ランクを返すランク付けユーティリティ（丸めで ties を安定化）。
    - research パッケージは外部依存（pandas 等）なし、DuckDB のみ参照する設計。
  - バックテスト（kabusys.backtest）
    - metrics:
      - calc_metrics: DailySnapshot と TradeRecord から各種評価指標を計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
      - 年次化や定義についてドキュメント化（営業日 252 日や暦日ベースの年率換算等）。
    - simulator:
      - PortfolioSimulator: メモリ上のキャッシュ・ポジション・平均取得単価を管理し、擬似約定を処理。
      - execute_orders: SELL を先に、BUY を後に処理。SELL は保有全量をクローズ（部分利確・部分損切りは未対応）。
      - TradeRecord / DailySnapshot データ構造を定義（commission, realized_pnl 等）。

### 仕様・設計上の注意（既知の制限・挙動）
- apply_sector_cap
  - "unknown" セクター（sector_map に存在しない銘柄）はセクター上限の対象外として扱われる。
  - price_map に価格が欠損（0.0）だとエクスポージャーが過少見積りになる可能性があり、将来的にフォールバック価格の検討が必要。
- calc_regime_multiplier
  - 未知のレジーム値は 1.0（Bull 相当）でフォールバックする（WARNING ログ）。
  - Bear レジーム時は戦略側（generate_signals）で BUY シグナルが生成されない設計。multiplier の 0.3 は中間的な追加セーフガード。
- signal_generator のエグジット条件
  - 実装済み: ストップロス（-8%）、final_score が threshold 未満。
  - 未実装（将来対応予定）: トレーリングストップ（peak_price 必要）、時間決済（保有 60 営業日超）。
- position_sizing
  - lot_size は現在グローバル共通の整数（デフォルト 100 を想定）。将来的に銘柄別 lot_map を受け取る拡張を計画。
- feature_engineering
  - Z スコア正規化は kabusys.data.stats.zscore_normalize を使用。normalized 値は ±3 にクリップされる。
- research.calc_forward_returns
  - ホライズンは営業日ベース（連続レコード数）。パフォーマンスのためにスキャン範囲は max_horizon の 2 倍のカレンダー日で限定。
- バックテスト・シミュレータ
  - SELL は保有全量をクローズするため、部分的なクローズや複雑な実行ロジックは実システムの挙動と異なる点に注意。
- 環境変数関連
  - 必須環境変数を Settings のプロパティで取得する際、未設定だと ValueError を送出する（明示的なエラーメッセージあり）。

### 変更点（リリース初版のため該当なし）
- なし

### 修正（リリース初版のため該当なし）
- なし

### 非推奨（リリース初版のため該当なし）
- なし

### 削除（リリース初版のため該当なし）
- なし

### セキュリティ（リリース初版のため該当なし）
- なし

---

既知の TODO / 将来対応案（参考）
- position_sizing: 銘柄別 lot_size 対応（stocks マスタからの取得）。
- apply_sector_cap: price 欠損時のフォールバック（前日終値や取得原価の利用）。
- signal_generator: トレーリングストップ・時間決済の実装（positions テーブルの拡張が前提）。
- simulator: 部分利確・部分損切りやより現実に近い約定ロジックの導入。

ご不明点や追加でCHANGELOGに記載したい事項があればお知らせください。