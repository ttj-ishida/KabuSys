CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。

0.1.0 - 2026-03-26
-----------------

Added
- 初回公開（0.1.0）。日本株自動売買ライブラリ "KabuSys" の基礎機能を実装。
- パッケージ公開情報
  - パッケージバージョン: 0.1.0
  - パッケージ説明: KabuSys - 日本株自動売買システム
  - __all__ による主要サブパッケージ公開: data, strategy, execution, monitoring

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数の自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装:
    - 空行・コメント行（#）を無視。
    - export KEY=val 形式に対応。
    - 単一/二重クォート、バックスラッシュエスケープに対応。
    - クォートなしの場合の行内コメント処理（'#' の直前がスペース/タブであればコメント扱い）。
    - 無効行は無視する堅牢な実装。
  - Settings クラスを提供し、主要な必須設定値をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb） / SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
    - ヘルパープロパティ: is_live / is_paper / is_dev

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順＋タイブレークで上位 N 件抽出
    - calc_equal_weights: 等金額配分の重み計算
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限。既存保有のセクター比率が上限を超える場合、当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックし警告を出力。
  - position_sizing:
    - calc_position_sizes: allocation_method別（risk_based / equal / score）で発注株数を計算。リスクベース、単元株丸め（lot_size）、ポジション上限・aggregate cap、手数料/スリッページバッファ(cost_buffer) を考慮したスケーリング実装を提供。

- 戦略 (kabusys.strategy)
  - feature_engineering:
    - build_features: research の生ファクターを結合・ユニバースフィルタ（最小株価・最小平均売買代金）を適用、指定カラムを Z スコア正規化し ±3 でクリップ、features テーブルへ日付単位で冪等に UPSERT。
    - 正規化対象カラムや閾値をコード内定数で定義（_MIN_PRICE=300 円, _MIN_TURNOVER=5e8, _ZSCORE_CLIP=3.0 等）。
  - signal_generator:
    - generate_signals: features と ai_scores を統合して final_score を算出し、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換（冪等）。
    - デフォルト重み、閾値、StopLoss の仕様を実装（デフォルト閾値=0.60、StopLoss=-8%）。
    - AI ニューススコアの補完（未登録は中立 0.5）、欠損コンポーネントは中立 0.5 で補完する設計。
    - Bear レジーム検知により BUY シグナルを抑制（ai_scores の regime_score を集計）。
    - SELL シグナル生成ではストップロスとスコア低下を評価。価格欠損時は SELL 判定をスキップまたは features 欠如時は score=0 として SELL。
    - weights の入力バリデーション（未知キー・非数値・負値を無視、合計が 1 に正規化）。

- 研究ユーティリティ (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m/3m/6m、ma200_dev（200営業日ウィンドウ）を計算。
    - calc_volatility: 20日 ATR（true range の NULL 伝播制御）、atr_pct、avg_turnover、volume_ratio を計算。
    - calc_value: raw_financials から直近財務を取得し PER/ROE を計算（EPS=0/欠損時は PER=None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。
    - calc_ic: スピアマンランク相関（IC）を実装（有効レコード 3 件未満で None を返す）。
    - rank / factor_summary: ランク処理（同順位は平均ランク）と基本統計量集計（count/mean/std/min/max/median）を実装。
  - zscore_normalize は data.stats から利用可能（実装は data パッケージ内）。

- バックテスト (kabusys.backtest)
  - metrics:
    - バックテスト評価指標群を実装（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）。
    - 数理的定義と入力検査（スナップショット数やゼロ割り等の安全処理）を実装。
  - simulator:
    - PortfolioSimulator: 擬似約定（SELL を先に処理、SELL は保有全量クローズ）とポートフォリオ状態管理（cash, positions, cost_basis, history, trades）を実装。
    - TradeRecord/DailySnapshot のデータ構造を提供。
    - スリッページ率（BUY:+, SELL:-）と手数料率を適用した約定ロジック（途中での部分約定サポート、lot_size を考慮）。

Changed
- （初回リリースのため履歴なし）

Fixed
- （初回リリースのため履歴なし）

Known issues / Notes
- feature_engineering / position_sizing / risk_adjustment 中に TODO コメントあり（例: price 欠損時のフォールバック価格、銘柄別 lot_size の将来対応）。
- apply_sector_cap:
  - price_map に価格が欠損（0.0）だとセクターのエクスポージャーが過少評価され、ブロックが外れる可能性がある旨の注記。
- generate_signals:
  - positions テーブルに peak_price / entry_date 等がないため、トレーリングストップや時間決済は未実装（将来的に拡張予定）。
- calc_regime_multiplier:
  - 未知のレジーム文字列は 1.0 でフォールバックし警告を出力。
- calc_position_sizes:
  - lot_size の現在はグローバル固定（将来的に銘柄別 lot_map を受け取る拡張を想定）。
- バックテスト・シミュレータは実トレード API を呼ばない純粋なメモリ実装。実運用前に execution 層や実約定モデルとの整合性を要確認。

開発者向けメモ
- 多くのモジュールは DuckDB 接続を受け取り prices_daily / raw_financials / features / ai_scores / positions / signals 等のテーブルを参照する設計。
- 多くの処理で「日付単位の置換（DELETE then INSERT）」を行い冪等性と原子性を確保（トランザクション使用）。
- ログ出力を充実させており、データ欠損時やフォールバック時に警告を出力する挙動がある。

ライセンス / その他
- 本リリースではライセンス表記・配布手順はソースツリーに従ってください（CHANGELOG には含まず）。

----- 

（以降リリースでは "Added/Changed/Fixed/Security" のセクションを追記してください）