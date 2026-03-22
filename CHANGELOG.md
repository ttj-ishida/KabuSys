CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。形式は「Keep a Changelog」に準拠します。  
リリースは逆順（最新 → 古い）で記載します。

Unreleased
----------

なし。

0.1.0 - 2026-03-22
------------------

初回公開（Initial release）。日本株自動売買システム「KabuSys」のコア機能を実装した最初のバージョンです。主な追加点・仕様は以下のとおりです。

Added
- パッケージ基盤
  - パッケージ初期化: version = 0.1.0、公開 API を __all__ で定義（data, strategy, execution, monitoring）。
- 環境設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサーは以下をサポート／考慮:
    - 空行・コメント行（先頭 #）を無視
    - export KEY=val 形式の対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
    - 非クォート値中の inline コメント判定（直前が空白/タブの場合のみ）
  - .env 読み込みは OS 環境変数を保護（protected set）し、override フラグで .env.local を優先上書き。
  - 必須環境変数チェッカー _require を提供（不足時は ValueError）。
  - 設定オブジェクト Settings を提供（プロパティ経由でアクセス）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須値取得
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等のデフォルト値サポート
    - KABUSYS_ENV（development/paper_trading/live の制約）、LOG_LEVEL（DEBUG/INFO/...）の検証メカニズム
    - is_live / is_paper / is_dev のユーティリティプロパティ
- 研究用モジュール（kabusys.research）
  - ファクター計算（factor_research）:
    - モメンタム（1M/3M/6M）、200日移動平均乖離率
    - ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金、出来高比率）
    - バリュー（PER, ROE）: raw_financials / prices_daily を組み合わせて算出
    - 各関数は DuckDB 接続と target_date を受け取り dict のリストを返す
  - 特徴量探索（feature_exploration）:
    - 将来リターン計算（calc_forward_returns、デフォルトホライズン [1,5,21]）
    - IC（Information Coefficient）計算（calc_ic、Spearman の ρ に相当）
    - ファクター統計サマリー（factor_summary）および tie-aware のランク関数 rank
  - research パッケージの公開 API を整理（calc_momentum 等の再エクスポート）
  - 研究モジュールは標準ライブラリ中心で外部依存を最小化（pandas等に依存しない設計）
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research で計算した生ファクターをマージ・ユニバースフィルタ適用・Zスコア正規化して features テーブルへ UPSERT（対象日を削除して挿入する日付単位の置換で冪等性を確保）
  - ユニバースフィルタ:
    - 最低株価 >= 300 円、20日平均売買代金 >= 5億円
  - 正規化対象カラムや ±3 のクリップなど標準化処理を実装
  - DuckDB トランザクションで atomic に挿入（例外時はロールバック、ロールバック失敗は警告ログ）
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して銘柄ごとのコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付き合算で final_score を算出
  - デフォルト重みと閾値:
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
    - BUY 閾値: 0.60
  - AI スコア処理:
    - ai_score は sigmoid 変換、未登録銘柄は中立値（0.5）で補完
    - regime_score の平均で Bear 判定（サンプル数不足時は Bear と見なさない）
  - weights の受け入れは厳格に検証（未知キーや非数値は無視、合計が 1.0 でなければ再スケール）
  - BUY は閾値超過かつ Bear でなければ生成。SELL は保有ポジションに対するストップロス（-8%）やスコア低下で生成
  - SELL が BUY より優先される（SELL 対象は BUY リストから除外し、ランクを再付与）
  - signals テーブルへの日付単位置換（トランザクションで原子性を保証）
  - 未実装で意図的に除外しているエグジット条件をドキュメント化（トレーリングストップ、時間決済など）
- バックテストフレームワーク（kabusys.backtest）
  - ポートフォリオシミュレータ（simulator）:
    - 初期現金, positions, cost_basis, history, trades を管理
    - 約定ロジック:
      - スリッページ・手数料を適用（BUY は始値 * (1 + slippage)、SELL は始値 * (1 - slippage)）
      - BUY は alloc（割当金額）から株数を算出し、手数料込みで取得可能な株数に再計算
      - SELL は保有全量をクローズ（部分利確・部分損切りは未対応）
      - 取引記録（TradeRecord）を作成して trades に保存（SELL では realized_pnl を計算）
    - mark_to_market で終値評価し DailySnapshot を記録（終値欠損時は 0 評価、警告ログ）
  - メトリクス（metrics）:
    - CAGR, Sharpe Ratio（無リスク=0）, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算するユーティリティ
  - バックテストエンジン（engine.run_backtest）:
    - 本番 DuckDB から必要なテーブルを期間で抽出し、init_schema(":memory:") で作成したインメモリ接続へコピー（signals/positions を汚さない）
    - market_calendar は全件コピー
    - 日次ループで:
      1. 前日シグナルを当日始値で約定（simulator.execute_orders）
      2. simulator の positions を positions テーブルへ書き戻し（generate_signals の SELL 判定に必要）
      3. 終値で評価・スナップショット記録
      4. generate_signals を呼び出して当日シグナルを生成
      5. signals テーブルから BUY/SELL を読み出し、ポジションサイジングを実行
    - デフォルトパラメータ: initial_cash=10_000_000 JPY, slippage_rate=0.001 (0.1%), commission_rate=0.00055 (0.055%), max_position_pct=0.20
  - バックテスト用のヘルパー:
    - 日付範囲でのテーブルコピー時に失敗したテーブルは警告を出してスキップ（耐障害性）

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- 環境変数の取り扱いにおいて OS 環境を保護する仕組み（protected set）を導入

Notes / Limitations
- 一部仕様は意図的に未実装（ドキュメント化済み）:
  - generate_signals のトレーリングストップや時間決済は未実装（positions テーブルに peak_price / entry_date 等の拡張が必要）
  - PortfolioSimulator は部分利確・部分損切りをサポートしていない（SELL は保有全量クローズ）
- 研究モジュールは外部ライブラリ（pandas 等）に依存しない実装を目指しているため、パフォーマンスや利便性向上のために将来外部ライブラリ導入を検討可能
- DuckDB に依存（DuckDB のバージョン互換や接続管理に注意）
- トランザクション中の例外発生時にロールバックに失敗した場合は警告ログを出し例外を再送出する実装（DB の整合性運用では注意）

Breaking Changes
- 初回リリースのため該当なし

開発者向け補足
- package の __all__ には data, strategy, execution, monitoring が列挙されていますが、execution / monitoring の具象実装はこのバージョンでは最小化されています（今後実装予定）。
- テストや CI から自動で .env をロードさせたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

以上。README や設計ドキュメント（StrategyModel.md / BacktestFramework.md 等）と合わせてご参照ください。