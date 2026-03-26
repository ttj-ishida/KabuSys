# Changelog

すべての破壊的変更は明示的に記載します。フォーマットは "Keep a Changelog" に準拠しています。

※この CHANGELOG は提示されたコードベースの内容から推測して作成した初期リリースの変更履歴です。

## [0.1.0] - 2026-03-26

### 追加 (Added)
- 初期パッケージ本体を追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 環境設定モジュールを追加（src/kabusys/config.py）。
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート判定は .git または pyproject.toml）。
  - export KEY=val、クォート文字列、インラインコメント等を考慮した .env パースロジックを実装。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数取得ヘルパー `_require` と Settings クラスを提供。以下の設定プロパティを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトあり）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパス有り）
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL の検証
    - is_live / is_paper / is_dev のユーティリティプロパティ

- ポートフォリオ構築モジュールを追加（src/kabusys/portfolio/）。
  - portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順ソートと上位 N 選定。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア加重配分（全スコア 0 の場合は等金額にフォールバックし WARNING ログ）。
  - risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（当日売却予定銘柄除外対応、"unknown" セクターは無視）。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear マッピングとフォールバック警告）。
  - position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数算出、lot 単位丸め、per-stock 上限・aggregate cap、cost_buffer（手数料・スリッページ見積り）対応。価格欠損時のスキップやログ出力を実装。

- 戦略（Strategy）モジュールを追加（src/kabusys/strategy/）。
  - feature_engineering.py:
    - build_features: research の factor 計算結果を取り込み、ユニバースフィルタ（最低株価・平均売買代金）、Z スコア正規化（±3 クリップ）、DuckDB への日付単位 UPSERT（トランザクション）を実装。
  - signal_generator.py:
    - generate_signals: features と ai_scores を統合してコンポーネントスコアを計算（シグモイド変換等）、最終スコアで BUY/SELL シグナルを算出。Bear レジーム時の BUY 抑制、SELL 優先での BUY 除外、signals テーブルへの置換挿入（トランザクション）を実装。
    - エラー／欠損データに対するフォールバック（AI スコア未登録時は中立値、features 未登録保有銘柄は score=0 として SELL 判定）や weights の妥当性検査・正規化を実装。

- リサーチ（Research）モジュールを追加（src/kabusys/research/）。
  - factor_research.py:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev の計算（過去データ不足は None）。
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、volume_ratio を計算（true_range の NULL 伝播に注意）。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS 欠損で PER=None）。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一括取得。
    - calc_ic: スピアマンのランク相関（IC）計算（有効サンプル 3 未満は None）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）計算。
    - rank: 同順位は平均ランクで処理（round による ties 対策）。

- バックテスト（Backtest）モジュールを追加（src/kabusys/backtest/）。
  - metrics.py:
    - BacktestMetrics データクラスと calc_metrics。CAGR、Sharpe、Max Drawdown、勝率、Payoff Ratio、総トレード数の算出ロジックを実装。
  - simulator.py:
    - PortfolioSimulator クラス、DailySnapshot/TradeRecord データクラス。
    - execute_orders: SELL を先に、BUY を後に処理する擬似約定ロジック。スリッページ率・手数料率を考慮し、SELL は保有全量クローズ（部分利確未対応）。履歴と約定記録を保持。

- モジュールのエクスポート（__all__）を各パッケージで定義（strategy/research/portfolio 等）。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### 既知の制限（Notes / Known issues）
- セクターエクスポージャー算出時に price_map に 0.0 があると過少見積りになるため TODO として前日終値や取得原価等のフォールバックを検討中（risk_adjustment.apply_sector_cap）。
- position_sizing: 将来的に銘柄ごとの lot_size をサポートする計画あり（現在は共通 lot_size 引数）。
- signal_generator._generate_sell_signals:
  - トレーリングストップ、時間決済（保有日数ベース）は未実装（positions テーブルに peak_price / entry_date 情報が必要）。
- feature_engineering は DuckDB のテーブル構造（prices_daily / raw_financials / features）に依存。実行前にスキーマ準備が必要。
- Simulator の BUY 処理では部分買い・部分利確の高度な注文ロジックは未対応。

### セキュリティ (Security)
- （初期リリースのため該当なし）

---

このリリースは機能の追加（戦略・リサーチ・ポートフォリオ構築・バックテスト・環境設定周り）に重点を置いた初期実装です。上記はコード内コメントや docstring、ログメッセージから推測した設計方針・仕様です。追加の変更履歴やバグ修正は後続リリースで追記してください。