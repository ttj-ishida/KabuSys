CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従います。  

フォーマット例:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 廃止予定
- Removed: 削除
- Security: セキュリティ関連

[0.1.0] - 2026-03-26
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
- コアモジュールを実装
  - kabusys.config
    - .env ファイルおよび環境変数読み込み機能を実装。
    - プロジェクトルート検出（.git または pyproject.toml を基準）により CWD に依存しない自動 .env ロードを実装。
    - export プレフィックス、シングル／ダブルクォート内のエスケープ、インラインコメントなどに対応した .env パーサを実装。
    - OS 環境変数を保護する protected 上書きロジックと、.env.local による上書きサポートを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - 必須環境変数取得時の検証（_require）と値検証（KABUSYS_ENV / LOG_LEVEL の有効値チェック）を実装。
    - 既定値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL など
  - kabusys.portfolio
    - portfolio_builder
      - select_candidates: BUY シグナルをスコア降順にソート、タイブレークは signal_rank を昇順で処理。
      - calc_equal_weights: 等分配の重み計算。
      - calc_score_weights: スコア比率で重み化。全スコアが 0.0 の場合は等分配にフォールバック（WARNING ログ）。
    - risk_adjustment
      - apply_sector_cap: セクター毎の既存エクスポージャーを評価し、最大セクター比率を超過しているセクターの新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（デフォルト値を定義、未知レジームは警告の上 1.0 でフォールバック）。
    - position_sizing
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
      - リスクベース計算（risk_pct, stop_loss_pct）、単元株（lot_size）丸め、ポジション上限（max_position_pct）、投下資金上限（max_utilization）、手数料・スリッページ見積り（cost_buffer）を考慮した aggregate cap スケーリングを実装。
      - aggregate スケールダウン時は端数（lot 単位）を残差に基づいて追加配分するロジックを実装し、再現性のため安定ソートを行う。
  - kabusys.strategy
    - feature_engineering
      - research モジュールから取得した生ファクターを結合してユニバースフィルタ（最低株価・最低売買代金）を適用。
      - 指定カラムについて Z スコア正規化（zscore_normalize を利用）、±3 でクリップし features テーブルへ日付単位の置換（トランザクション + バルク挿入）を行う（冪等）。
      - DuckDB を用いた日付以前の最新価格取得ロジックを実装。
    - signal_generator
      - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算、重み付き合算により final_score を算出。
      - デフォルトの重みと閾値（default weights, default threshold）を実装し、ユーザー指定 weights の検証と正規化処理を実装（不正値はログでスキップ）。
      - AI スコアを用いる際の補完ロジック（未登録時の中立補完）を実装。
      - Bear レジーム判定（AI の regime_score 平均）を実装し、Bear 時は BUY シグナルを抑制。
      - SELL シグナル生成（ストップロス、スコア低下）を実装。features に存在しない保有銘柄は final_score=0 と扱い SELL 対象にする旨の警告を出力。
      - signals テーブルへの日付単位置換（トランザクション処理）で冪等性を確保。
  - kabusys.research
    - factor_research
      - calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials テーブルのみ参照）。
      - 各ファクターの計算でデータ不足時は None を返す方針を採用。
    - feature_exploration
      - calc_forward_returns: 将来リターンを複数ホライズンで一括取得。horizons の検証（正の整数かつ <= 252）を実装。
      - calc_ic: スピアマンランク相関（IC）を実装。3 サンプル未満の場合は None。
      - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量サマリを実装。rank は丸めによる ties 検出漏れを防ぐため round(..., 12) を使用。
  - kabusys.backtest
    - metrics
      - バックテスト評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）を計算するユーティリティを実装。
    - simulator
      - PortfolioSimulator を実装。メモリ内でキャッシュ・ポジション・約定履歴を保持。
      - execute_orders: SELL を先に、BUY を後に処理。SELL は全量クローズ（部分利確は未対応）。スリッページ・手数料モデルを考慮した約定ロジックを実装。
      - TradeRecord / DailySnapshot の dataclass を定義。
  - パッケージ公開インターフェイス
    - kabusys.__init__.py で __version__ = "0.1.0" とし、主要サブパッケージを __all__ に含める。

Changed
- n/a（初回リリースのため変更履歴はなし）

Fixed
- n/a（初回リリースのため修正履歴はなし）

Known limitations / Notes（既知の制約・TODO）
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布後や特殊な配置で検出できない場合は自動ロードをスキップする。必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用し手動で環境変数を設定すること。
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）が含まれるとエクスポージャーが過少見積りされ、本来ブロックすべきセクターが除外されない可能性がある（TODO: 前日終値や取得原価でのフォールバックを検討）。
  - "unknown" セクターはセクター上限のチェック対象外になる（設計仕様）。
- strategy.signal_generator:
  - 一部のエグジット条件（トレーリングストップ、時間決済）は未実装。これらは positions テーブルに peak_price / entry_date の情報が必要となるため将来的な拡張ポイント。
- position_sizing:
  - lot_size は現在グローバル共通で扱う設計。将来的には銘柄別 lot_map を受け取る設計に拡張予定（TODO 記載）。
- backtest.simulator.execute_orders:
  - SELL は現状「全量クローズ」のみをサポート（部分利確・部分損切りは未対応）。
- 一部の機能は research の結果や DB テーブル（prices_daily, raw_financials, features, ai_scores, positions, signals 等）を前提とする。テスト時は該当テーブルと適切なスキーマ・データが必要。

Security
- n/a（既知のセキュリティ問題なし）

Appendix: 実装上のログ／警告の挙動
- 不正な設定値やデータ欠損に対しては logger.warning / logger.debug で詳細を出力する実装。例:
  - 全銘柄のスコアが 0 の場合、calc_score_weights は WARNING を出して等金額配分にフォールバック。
  - generate_signals は weights の不正な値をスキップし、合計が 1.0 に正規化されない場合はデフォルトにフォールバック或いは再スケーリング。
  - features が空のときは BUY シグナルは発生せず SELL 判定のみ実施し警告を出す。

今後の予定（案）
- 銘柄ごとの lot_size サポート
- price フォールバック（前日終値等）の導入
- トレーリングストップや時間決済などの追加エグジットロジック
- execution 層（kabu API 等）との統合用モジュール実装

--- 
（本 CHANGELOG はコードの内容から推測して作成しています。細かな動作や公開 API の正式な変更点はリポジトリのコミット履歴／リリースノートを合わせてご確認ください。）