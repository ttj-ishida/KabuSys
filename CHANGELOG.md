# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の方針に従って記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-26
初回リリース。日本株向け自動売買フレームワークのコア機能を提供します。以下のモジュールと主な機能を実装しています。

### 追加（Added）
- 基本パッケージ構成
  - パッケージエントリポイントを追加（kabusys.__version__ = 0.1.0）。
  - サブパッケージを公開: data, strategy, execution, monitoring（__all__ 定義）。

- 環境設定（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション。
  - .env パーサーの実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理）。
  - OS 環境変数を保護する protected keys の概念（.env.local による上書きと排他制御）。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live 検証）および LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev 補助プロパティ
  - 必須キー未設定時は ValueError を投げる _require 実装。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順、同点は signal_rank 昇順で選出。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコアを正規化した重み（全スコアが 0 の場合は等配分にフォールバックして WARNING）。
  - risk_adjustment:
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、最大セクター比率超過時に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数（デフォルト 1.0/0.7/0.3、未知レジームは警告の上 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method に応じた株数算出（"risk_based"/"equal"/"score"）。
    - リスクベース算出、単元（lot_size）丸め、per-position／aggregate の上限、cost_buffer を加味した保守的見積り、投資合計が available_cash を超える場合のスケールダウンと残差を考慮した再配分アルゴリズムを実装。
    - 価格欠損や lot_size 非対応のケースに対するログ出力。

- 戦略（src/kabusys/strategy/*）
  - feature_engineering:
    - calc_momentum / calc_volatility / calc_value（research モジュールを利用）からの生ファクターを統合。
    - ユニバースフィルタ（最低株価・最低平均売買代金）適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）し ±3 でクリップ。
    - DuckDB を使った features テーブルへの日付単位の冪等 UPSERT（BEGIN/COMMIT/ROLLBACK 管理）。
  - signal_generator:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - sigmoid による正規化、欠損コンポーネントは中立 0.5 で補完。
    - final_score に対する閾値（デフォルト 0.60）で BUY シグナルを生成。Bear レジーム時は BUY を抑制。
    - 保有ポジションに対するエグジット（stop-loss / score_drop）を判断して SELL シグナルを生成。
    - weights の入力検証・デフォルトフォールバック・合計正規化を実装。
    - signals テーブルへの日付単位の置換（冪等）を実装。
    - 各種ログ（WARN/INFO/DEBUG）出力を充実させて不整合時の追跡を容易に。

- 研究用モジュール（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を DuckDB ウィンドウ関数で計算。
    - calc_volatility: 20日 ATR（true range の NULL 管理を含む）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近の財務データを取得して PER / ROE を算出（EPS=0 は None）。
    - SQL ベースで過去データスキャンの範囲バッファを考慮した実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来終値リターンを一括 SQL で取得。
    - calc_ic: Spearman のランク相関（Information Coefficient）を実装（データ不足時は None）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクで扱うランク関数（round による同値判定で数値丸め誤差を吸収）。

- バックテスト（src/kabusys/backtest/*）
  - simulator:
    - DailySnapshot / TradeRecord の dataclass 定義。
    - PortfolioSimulator: 簡易約定ロジック（SELL 先行、BUY 後処理）、スリッページ・手数料反映、履歴・約定記録の保持。部分約定／単元制御用の lot_size パラメータあり。
  - metrics:
    - 各種バックテスト指標を計算する calc_metrics 実装（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - 内部での各指標の詳細実装（年次化や営業日換算、例外時の 0 フォールバックなど）。

### 変更（Changed）
- 初回リリースのため特になし（このバージョンで新規実装多数）。

### 修正（Fixed）
- 初回リリースのため特になし（実装時点での既知の挙動はログや docstring に注記）。

### 注意点 / 実装上の制約（Notes）
- DuckDB を前提とした SQL 実装のため、prices_daily / raw_financials / features / ai_scores / positions / signals 等のスキーマ・存在が前提となります。詳細は各モジュールの docstring を参照してください。
- execution パッケージはパッケージツリーにプレースホルダが存在しますが、外部発注 API 統合や実口座接続の実装は本バージョンでは含まれていません（発注層は将来の実装を想定）。
- 一部のロジックは簡易化されており（例: SELL は現状「全量クローズ」のみ）、将来的に部分利確・トレーリングストップ等の拡張が想定されています（docstring に TODO 記載）。
- env ファイルパーサの挙動は実用レベルに配慮していますが、極端に複雑なシェル展開や変数展開はサポートしていません。
- calc_regime_multiplier の multiplier は保護的な値に設定されていますが、Bear レジーム時の BUY シグナル抑制は signal_generator 側のロジックが一次的に担います。

### ドキュメント（Documentation）
- 各モジュールに詳細な docstring を付与しました（動作想定、参照テーブル、アルゴリズムの根拠、TODO・将来拡張点など）。

---

開発・利用にあたって不明点や追加してほしい機能があればお知らせください。必要であればリリースノートの英語版やセクション分けをさらに詳細化して提供します。