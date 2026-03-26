# CHANGELOG

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

---

## [0.1.0] - 2026-03-26

初回公開リリース。

概要: 日本株自動売買フレームワーク「kabusys」の基盤機能を実装しました。  
主に環境設定、銘柄選定・配分・リスク調整、特徴量生成・シグナル生成、リサーチ用ファクター計算、バックテスト（シミュレータ／メトリクス）を含む純粋関数群と DuckDB ベースのデータ処理を提供します。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化 (src/kabusys/__init__.py)、バージョン "0.1.0" を設定。
  - サブモジュール公開インターフェースを定義（data, strategy, execution, monitoring 等を想定）。

- 環境設定 / .env ローダー (src/kabusys/config.py)
  - Settings クラスを追加し、環境変数 (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等) をプロパティで取得。
  - .env / .env.local 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から検出）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサーの強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントルール、無効行スキップ。
  - OS 環境変数を保護する protected オプション（.env.local は override=true だが既存 OS 環境は保護）。

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - portfolio_builder.py:
    - select_candidates(buy_signals, max_positions)：スコア降順＋signal_rank タイブレークで候補選定。
    - calc_equal_weights(calc_score_weights)：等金額・スコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - position_sizing.py:
    - calc_position_sizes：risk_based / equal / score に対応した株数算出、単元株丸め、per-position 上限・aggregate cap（available_cash）適用、cost_buffer を利用した保守的コスト見積もり、スケーリングと残差処理による追加配分ロジックを実装。
  - risk_adjustment.py:
    - apply_sector_cap：セクター別エクスポージャー計算と新規候補除外（"unknown" セクターは対象外）。
    - calc_regime_multiplier：市場レジームに基づく乗数（bull/neutral/bear → 1.0/0.7/0.3、未知レジームは 1.0 にフォールバック）。

- 戦略（特徴量生成・シグナル生成） (src/kabusys/strategy/)
  - feature_engineering.build_features:
    - research 側で計算した生ファクターを取り込み、ユニバースフィルタ（株価・流動性）、Z スコア正規化（zscore_normalize 利用）、±3 クリップを行い DuckDB の features テーブルへ日付単位で置換（トランザクション + バルク挿入で冪等性を確保）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付けして final_score を算出。
    - レジーム（AI の regime_score 集計）により Bear 相場判定し BUY を抑制。
    - BUY は閾値（デフォルト 0.6）超で生成、SELL はストップロス・スコア低下条件で生成。
    - SELL 優先で BUY から除外、signals テーブルへ日付単位で置換（トランザクション実装）。
    - ユーザ指定 weights の検証と正規化処理を実装。

- リサーチ用ファクター計算 (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum / calc_volatility / calc_value を実装（DuckDB のウィンドウ関数を活用）。
    - 各関数は date, code キーの dict リストを返す設計。
  - feature_exploration.py:
    - calc_forward_returns：指定ホライズン（デフォルト [1,5,21] 営業日）で将来リターンを一括取得。
    - calc_ic：スピアマンのランク相関（IC）を実装（有効レコードが 3 件未満で None を返す）。
    - factor_summary / rank：基本統計量計算とランク変換ユーティリティ。
  - research パッケージレベルで zscore_normalize と主要ファクターをエクスポート。

- バックテスト (src/kabusys/backtest/)
  - simulator.py:
    - PortfolioSimulator：擬似約定（SELL を先に、BUY を後に処理）、スリッページ・手数料モデル、TradeRecord / DailySnapshot データ構造、保有全量クローズの挙動を実装。
    - トレード記録に realized_pnl を含める（SELL 時のみ）。
  - metrics.py:
    - calc_metrics / BacktestMetrics：CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算するユーティリティ関数を実装。

- DuckDB を用いたバッチ SQL 処理
  - features / ai_scores / prices_daily / raw_financials などのテーブルを前提とした、効率的な SQL（ウィンドウ関数・LEAD/LAG/AVG/COUNT）での集計処理を採用。

- ロギングとエラーハンドリング
  - 各モジュールで logging を使用した情報出力、警告、デバッグメッセージを実装（例: 価格欠損時のスキップやトランザクションの ROLLBACK ログ等）。
  - config の値検証（KABUSYS_ENV の許容値、LOG_LEVEL の検証）。必須環境変数未設定時は ValueError を送出。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- .env 読み込みの堅牢性向上：
  - ファイル読み込み失敗時に警告で継続する実装（テスト時の堅牢性向上）。
  - クォート内のエスケープやインラインコメントの取り扱いを正しく処理。

### 既知の制限 / TODO（重要）
- position_sizing calc_position_sizes:
  - lot_size は現状グローバル固定で銘柄別単元未サポート（将来的に銘柄別 lot_map で拡張予定）。
  - price 欠損時は 0.0 を使うためエクスポージャーが過小評価される可能性あり（注記あり）。
- シミュレータの売却ロジック:
  - SELL は保有全量をクローズする（部分利確・部分損切りは未対応）。
- 売却ルールの未実装項目:
  - トレーリングストップ（peak_price / entry_date が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- feature_engineering / signal_generator:
  - AI ニューススコア周りは ai_scores テーブル依存。未登録銘柄は中立補完（0.5）。
- その他:
  - 一部のフォールバック値（例: レジーム未知時 multiplier=1.0）や保守的なデフォルトが設定されている点に注意。
  - execution モジュールはパッケージに存在する構造を確立しているが、外部 API 連携（kabuステーション実行等）の具体実装は別途。

### セキュリティ (Security)
- 環境変数の必須チェックを導入し、秘密情報（トークン等）が未設定の場合は明示的にエラーを出すことで誤動作を防止。

---

（注）実装の多くはモジュール内 docstring にある設計仕様（PortfolioConstruction.md / StrategyModel.md / BacktestFramework.md 等）に準拠しており、仕様ドキュメントが存在することを前提としています。今後のリリースでは execution 層の実際のブローカー接続、部分約定対応、銘柄別取引単位の導入、追加の売却ルール実装などを予定しています。