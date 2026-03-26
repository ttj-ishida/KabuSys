# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  
安定版リリース以外の変更は将来の Unreleased セクションに記載します。

なお、本 CHANGELOG はコードベースの内容から推測して作成しています。

## [0.1.0] - 2026-03-26

初回リリース。日本株自動売買システム "KabuSys" の基礎機能を実装しました。主な追加点・仕様は以下の通りです。

### 追加 (Added)
- パッケージメタ情報
  - kabusys パッケージのバージョンを "0.1.0" に設定 (src/kabusys/__init__.py)。
  - パッケージ公開 API として data, strategy, execution, monitoring を __all__ で定義。

- 環境変数／設定管理 (src/kabusys/config.py)
  - .env/.env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索して行う（配布後も動作する設計）。
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env のパース処理を実装（コメント処理、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープを考慮）。
  - 読み込み時の上書き制御 (override) と OS 環境変数の保護機能 (protected) を実装。
  - Settings クラスを提供し、主要な必須設定値をプロパティ経由で取得可能に。
    - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB のデフォルトパス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - 環境/ログレベル検証: KABUSYS_ENV は development/paper_trading/live、LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容。

- ポートフォリオ構築関連 (src/kabusys/portfolio/)
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順（同点時は signal_rank 昇順）でソートして上位 N を返す。
    - calc_equal_weights: 等金額配分の重みを計算（各銘柄 1/N）。
    - calc_score_weights: スコア加重配分を計算。全銘柄のスコアが 0 の場合は等金額配分にフォールバックし警告を出す。
  - risk_adjustment
    - apply_sector_cap: セクター集中上限チェックを実装。既存保有のセクター別時価を計算し、比率が max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは上限適用対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）を提供。未知レジームは 1.0 にフォールバックし警告を出す。
  - position_sizing
    - calc_position_sizes: 重み・候補・ポートフォリオ情報を受け取り銘柄別発注株数を決定。
      - allocation_method: "risk_based", "equal", "score" をサポート。
      - risk_based: 許容リスク率、損切り率からベース株数を計算し単元（lot_size）で丸める。
      - equal/score: 重みから各銘柄の配分を計算。per-position 上限 (max_position_pct)、aggregate cap（available_cash）を考慮。
      - aggregate cap の場合のスケーリングロジックを実装（スケールダウン → lot_size 単位で残差を大きい順に追加配分）。
      - cost_buffer を使った保守的な約定コスト見積り（スリッページ・手数料を想定）に対応。
      - 将来的な拡張点として銘柄別 lot_size 対応の TODO を記載。

- 戦略（Strategy）関連 (src/kabusys/strategy/)
  - feature_engineering
    - build_features: 研究モジュールから取得した生ファクターを統合し正規化 (Z スコア)、±3 でクリップして features テーブルへ UPSERT（トランザクションで日付単位置換し冪等性を確保）。
    - ユニバースフィルタ: 株価 >= 300 円、20 日平均売買代金 >= 5 億円を適用。
    - DuckDB を用いた価格取得やテーブル操作を実装。
  - signal_generator
    - generate_signals: features と ai_scores を統合して final_score を計算し BUY / SELL シグナルを生成して signals テーブルへ書き込む（冪等）。
      - デフォルトのファクター重みを実装（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）。ユーザ指定の weights は検証・補完・正規化される。
      - AI ニューススコアをシグモイドで [0,1] に変換。未登録は中立 (0.5) 補完。
      - Bear レジーム判定: ai_scores の regime_score の平均が負（十分なサンプル数がある場合）だと Bear と判定し BUY を抑制。
      - SELL シグナル（エグジット）判定:
        - ストップロス: (close / avg_price - 1) < -8% → stop_loss
        - final_score < threshold → score_drop
        - 価格欠損時は SELL 判定をスキップ（警告）
        - features に存在しない保有銘柄は final_score=0 として SELL 対象にする（警告）
      - signals テーブルへの書き込みはトランザクションで日付単位置換して原子性を保証。

- リサーチ（Research）関連 (src/kabusys/research/)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（ウィンドウ不足時は None）。
    - calc_volatility: 20 日 ATR（true_range の取り扱いに注意）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を計算（EPS が 0/欠損時は PER=None）。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一クエリで取得。
    - calc_ic: スピアマン（ランク）相関を計算。サンプル数 3 未満では None。
    - factor_summary: count/mean/std/min/max/median を計算（None 値は除外）。
    - rank: 同順位がある場合は平均ランクで扱う（浮動小数の丸めで ties 検出の安定化を実装）。
  - research パッケージレベルで主要関数と zscore_normalize をエクスポート。

- バックテスト（Backtest）関連 (src/kabusys/backtest/)
  - simulator
    - PortfolioSimulator: 擬似約定とポートフォリオ状態管理を実装（メモリ内）。SELL を先に処理してから BUY を処理する方針。SELL は保有全量をクローズ（部分利確非対応）。
    - DailySnapshot / TradeRecord のデータクラスを定義（TradeRecord.realized_pnl は SELL 時のみ設定）。
    - 約定でのスリッページ率と手数料率を考慮する設計。
  - metrics
    - バックテスト評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）を計算するユーティリティを実装。入力は DailySnapshot と TradeRecord のリストのみ。

- モジュールエクスポート整理
  - portfolio, strategy, research パッケージで主要 API を __all__ にて明示的に公開。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### 注意事項 / 設計メモ
- config._parse_env_line はクォート内のバックスラッシュエスケープを考慮しますが、完全なシェル互換を目指すものではありません。複雑な .env の記述がある場合は動作を確認してください。
- position_sizing の _max_per_stock は price が 0 以下の場合 0 を返します。price 欠損時はスキップされるため、価格データの確保が重要です。
- apply_sector_cap は sector_map にない銘柄を "unknown" 扱いにし、"unknown" セクターにはセクター上限を適用しません（将来的な変更の余地あり）。
- signal_generator は Bear 相場時に BUY を抑制する設計。ただし generate_signals の戻り値は BUY+SELL の合計シグナル数であり、実際のポジション構築は別レイヤ（position sizing / execution）で行う想定です。
- バックテストの約定モデル・手数料モデルは BacktestFramework.md に準拠する想定の実装。ただし実運用前に実際のコスト構成で検証が必要です。
- 各モジュールに TODO / 拡張点のコメントがあります（例: 銘柄毎の lot_size、前日終値や取得原価による価格フォールバック、トレーリングストップ、時間決済など）。

---

将来的な変更（バグ修正、機能追加、仕様変更）は Unreleased セクションに追記していきます。