# Changelog

すべての注目すべき変更点をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。セマンティックバージョニングを採用しています。

- リリースノートは主にコードベースから推測して作成しています（実装済みの機能・設計意図・注意点を中心に記載）。
- 各リリースは後方互換性や既知の制約・TODO を含めて簡潔に説明します。

## [Unreleased]

（次回以降の変更点をここに記載します）

## [0.1.0] - 2026-03-26

初回公開リリース。日本株の自動売買システムのコアライブラリを提供します。主要なサブパッケージは data, strategy, portfolio, research, backtest, execution, monitoring など（パッケージ __all__ に基づく）。

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys v0.1.0）。
  - パッケージ公開情報: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定自動読み込み機能を追加。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索する実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env パースは export プレフィックス、クォート、エスケープ、インラインコメントに対応。
    - OS 環境変数を保護するための protected キー概念を実装（.env で既存 OS 変数を上書きしない挙動）。
  - Settings クラスを提供し、主要設定値をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を必須として取得（未設定時は ValueError）。
    - KABUSYS_ENV (development / paper_trading / live) と LOG_LEVEL の検証ロジックを実装。
    - データベースパスのデフォルト（duckdb: data/kabusys.duckdb, sqlite: data/monitoring.db）を設定。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順、同点時は signal_rank 昇順でソートして上位 N を選出。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を実装。全スコアが 0 の場合は等配分へフォールバックして警告ログを出力。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジックを実装（既存ポジションのセクター時価評価を参照し、閾値超過セクターの新規候補を除外）。"unknown" セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告の上 1.0 にフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく株数計算を実装。
    - risk_based: 許容リスク（risk_pct）と損切り率（stop_loss_pct）から理論株数を算出。
    - equal/score: ポートフォリオ額・重みから割当を計算。lot_size（単元）丸め、1銘柄上限・aggregate cap、cost_buffer を用いた保守的コスト見積もりとスケーリング処理を実装。
    - aggregate cap 超過時はスケーリングし、remainder に基づき単元単位で追加配分するロジックを実装。

- 戦略（kabusys.strategy）
  - feature_engineering:
    - research モジュールの生ファクター（momentum / volatility / value）を取得し、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 指定カラムを z-score 正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - features テーブルへ日付単位で置換（トランザクションにより atomic な UPSERT）。DuckDB を使用する想定。
  - signal_generator:
    - features と ai_scores を統合して最終スコア（final_score）を計算。コンポーネントスコアは momentum/value/volatility/liquidity/news を算出。
    - デフォルト重みを定義し、ユーザ提供 weights を検証・補完・正規化する実装。
    - Bear レジーム判定（ai_scores の regime_score を集計）による BUY シグナル抑制（Bear の場合は BUY を生成しない）。
    - BUY シグナルは閾値 (default 0.60) 以上の銘柄でランク付け。SELL シグナルはストップロス（-8%）およびスコア低下（threshold 未満）で判定。SELL 優先ポリシーを適用し、SELL 対象を BUY から除外。
    - signals テーブルへ日付単位で置換（トランザクションにより原子性を確保）。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None）を計算。
    - calc_volatility: 20日 ATR / atr_pct、20日平均売買代金、volume_ratio を計算。true range 計算時に high/low/prev_close が欠損すると true_range を NULL にする設計。
    - calc_value: raw_financials から最新財務データを取得し PER/ROE を計算（EPS が 0・欠損時は PER=None）。
    - 各関数は DuckDB の SQL クエリで効率的に集計する設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: Spearman ランク相関（IC）を実装（有効レコードが 3 未満なら None を返す）。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算。
    - rank: 平均ランク（同順位は平均ランク）を返すユーティリティを実装（浮動小数点の丸めを考慮）。

- バックテスト（kabusys.backtest）
  - simulator:
    - PortfolioSimulator クラスを実装。メモリ内での cash, positions, cost_basis, history, trades を管理。
    - execute_orders: SELL を先、BUY を後に処理。SELL は保有全量クローズ（部分クローズ未対応）。スリッページ率・手数料率を受け取り約定価格・手数料計算を行う（TradeRecord を生成）。
    - TradeRecord / DailySnapshot のデータクラスを定義。
  - metrics:
    - バックテスト評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）を計算する util を実装。

### Changed
- （初回リリースのため「Changed」項目はなし。設計上のフォールバックや警告ログを多数含むため、将来の変更時に注記を予定。）

### Fixed
- （初回公開のため特定のバグ修正履歴はなし。ただし実装中に扱った多くの障害回避ロジック（例: 価格欠損時の判定スキップ、トランザクションのロールバック処理、未知入力のフォールバック）が含まれることを明示。）

### Deprecated
- なし

### Removed
- なし

### Security
- 環境変数の読み込みで OS 環境変数が意図せず上書きされないよう protected 処理を追加（.env の読み込みは既存 OS 変数を上書きしないのがデフォルト）。

### Notes / Known issues / TODO
- .env の読み込みはプロジェクトルート検出に依存するため、配布後や特定の配置で自動検出できない場合がある（その場合は自動ロードをスキップ）。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用可。
- position_sizing の lot_size は現状グローバル定数扱い（将来は銘柄別 lot_map に拡張予定という TODO がコメントに記載）。
- apply_sector_cap は price が欠損（0.0）の場合にエクスポージャーを過少見積もる可能性があると注記あり。将来的に価格フォールバックの導入を検討。
- signal_generator の未実装箇所:
  - トレーリングストップ・時間決済（positions テーブルに peak_price / entry_date が必要との記載）。
- calc_regime_multiplier は未知レジームで 1.0 にフォールバックする（警告ログを出力）。Bear 相場の追加セーフガードとして multiplier=0.3 を採用しているが、実際に Bear では generate_signals が BUY を生成しない設計である点に注意。
- backtest.simulator の BUY/SELL の約定詳細や手数料モデルのパラメータは BacktestFramework.md に準拠する想定。実運用に際しては実際の取引ルール・手数料体系に合わせた調整が必要。

---

（追記）この CHANGELOG はコードベースからの推測に基づいて作成しています。実際のリリースノート作成時は、コミット履歴・issue・リリース管理情報を参照のうえ適宜補完してください。