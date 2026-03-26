# CHANGELOG

すべての変更点は Keep a Changelog の形式に準拠して記載しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-26

初回公開リリース。日本株自動売買システム "KabuSys" のコア機能を提供します。

### 追加 (Added)
- パッケージ基点
  - パッケージメタ情報を定義（kabusys.__init__、__version__ = 0.1.0）。
  - モジュールの公開 API を __all__ で整理（data, strategy, execution, monitoring など）。

- 設定管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を自動ロードする機能を実装。
  - プロジェクトルート検出機能: .git または pyproject.toml を基準に自動的に検索。
  - .env パーサ実装: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理に対応。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラス実装: 必須変数読み取り（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）、既定値（API ベース URL、DB パス等）、入力検証（KABUSYS_ENV, LOG_LEVEL）。

- ポートフォリオ構築 (kabusys.portfolio)
  - 銘柄選定:
    - select_candidates: スコア降順でソート、同点時は signal_rank でタイブレーク、上位 N を選出。
  - 重み付け:
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算。全スコアが 0 の場合には警告を出して等金額配分にフォールバック。
  - リスク制御:
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、最大セクター比率を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3、未知レジームは警告のうえ 1.0 でフォールバック）。

  - ポジションサイジング:
    - calc_position_sizes: allocation_method（"risk_based", "equal", "score"）に基づき発注株数を計算。
    - 単元（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash に基づく）を考慮。
    - cost_buffer による手数料/スリッページ見積りを加味した保守的なスケーリング処理を実装。
    - 価格欠損時はスキップし、ログ出力で通知。

- 戦略・特徴量 (kabusys.strategy)
  - feature_engineering.build_features:
    - 研究モジュールから raw factor を取得（momentum/volatility/value）。
    - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定カラムの Z スコア正規化と ±3 クリップ。
    - DuckDB を用いた日付単位の UPSERT（トランザクション内で DELETE → INSERT）で features テーブルに書き込み（冪等性確保）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄の final_score を算出（momentum/value/volatility/liquidity/news の重み付け、既定重みは提供）。
    - Sigmoid 等の変換・欠損補完（None は中立値 0.5）を採用。
    - Bear レジーム検知時は BUY シグナルを抑制。
    - BUY シグナル閾値（デフォルト 0.60）に基づく選別。
    - エグジット判定（ストップロス -8%、final_score の閾値割れ）による SELL シグナル生成。SELL は BUY より優先して除外。
    - signals テーブルへの日付単位置換（トランザクションで原子性確保）。

- 研究ユーティリティ (kabusys.research)
  - factor_research: momentum / volatility / value の定量ファクターを実装（DuckDB を参照）。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンのランク相関（IC）を実装（最小サンプル数条件あり）。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量サマリーを実装。
  - zscore_normalize を外部に再エクスポート。

- バックテスト (kabusys.backtest)
  - simulator:
    - DailySnapshot / TradeRecord データクラスを定義。
    - PortfolioSimulator を実装: 擬似約定（SELL を先に処理 → BUY）・スリッページ/手数料の適用、平均取得単価管理、取引履歴保持。
  - metrics:
    - バックテスト評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）を計算するユーティリティを実装。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の制約・実装上の注意 (Notes / TODO)
- apply_sector_cap:
  - 価格が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性がある旨コメントあり。将来的に前日終値や取得原価でフォールバックする案あり。
- calc_position_sizes:
  - 銘柄別の単元情報（lot_size）を stocks マスタに持たせる拡張は未実装（TODO）。
- signal_generator:
  - トレーリングストップや時間決済（保有期間による自動決済）は positions テーブル内の peak_price / entry_date 等が未実装のため現在は未対応。
- feature_engineering / signal_generator / factor_research:
  - DuckDB の特定テーブル（prices_daily, raw_financials, features, signals, ai_scores, positions 等）に依存。運用時はスキーマ準備が必要。
- PortfolioSimulator.execute_orders:
  - 現在 SELL は「保有全量をクローズ」する実装（部分利確・部分損切りは非対応）。
- 設定管理:
  - Settings._require は未設定時に ValueError を送出するため、テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用するなど注意。

### 開発者向けメモ
- パッケージは設計資料（PortfolioConstruction.md, StrategyModel.md, BacktestFramework.md 等）に基づいて実装されています。詳細仕様や拡張方針は該当ドキュメントを参照してください。
- ロギングを多用しており、価格欠損や異常値の際に WARNING/DEBUG を出す実装になっています。運用時は LOG_LEVEL を適切に設定してください。

---

今後のリリースでは、以下を優先的に予定しています:
- 銘柄別 lot_size のサポート（マスタ参照による丸め制御）。
- 価格欠損時のフォールバック価格ロジック。
- 部分約定・部分利確対応、より柔軟な注文ロジック。
- Trailing stop / 時間決済等の追加エグジット条件実装。