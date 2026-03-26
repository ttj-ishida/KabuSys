Keep a Changelog 準拠の形式で、リポジトリ内のコード内容から推測した変更履歴を日本語で作成しました。
（注意: 実際のコミット履歴ではなく、コードの実装内容から推測して記載しています）

CHANGELOG.md
============

全般
-----
- この CHANGELOG はコードベースの実装内容から推測して作成しています。
- フォーマットは「Keep a Changelog」に準拠しています。

[0.1.0] - 2026-03-26
--------------------

Added
-----
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0, __all__ エクスポート）。
  - モジュール構成（data, strategy, execution, monitoring を公開対象に設定）。

- 環境設定 / ロード
  - 環境変数/設定読み込みモジュールを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env 自動読み込みをサポート。
    - .env と .env.local の優先順位処理（OS 環境変数を保護する protected 機構）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD を使った自動ロード無効化対応。
    - .env パーサーは export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメント処理に対応。
  - Settings クラスを実装（プロパティ経由で必須設定を取得）。
    - J-Quants / kabu ステーション / Slack / DB パスなどの設定プロパティ。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）。
    - duckdb/sqlite のデフォルトパス設定。

- ポートフォリオ構築（Portfolio）
  - 銘柄候補選定: select_candidates — スコア降順、同点時は signal_rank でタイブレーク。
  - 配分重み:
    - calc_equal_weights — 等金額配分。
    - calc_score_weights — スコア加重配分（全スコアが 0 の場合は等配分にフォールバックし WARNING を出力）。
  - リスク調整:
    - apply_sector_cap — セクター集中制限を適用（既存保有の時価を用いて、上限超過セクターから新規候補を除外）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier — 市場レジーム (bull/neutral/bear) に応じた投下資金乗数（未定義レジームは 1.0 でフォールバックし警告を出力）。
  - ポジションサイジング:
    - calc_position_sizes — allocation_method ("risk_based" / "equal" / "score") に基づく発注株数計算。
      - risk_based: 許容リスク率・損切り率から目標株数計算。
      - equal/score: 重みと max_utilization に基づく配分。
      - 単元株丸め（lot_size）、1銘柄上限（max_position_pct）、aggregate cap（available_cash）検査。
      - cost_buffer を用いた保守的なコスト見積もり。スケールダウン時は lot_size 単位で残差を大きい順に追加配分して再現性を確保。
      - 価格欠損時は該当銘柄をスキップし debug ログを出力。

- 戦略（Strategy）
  - 特徴量作成: build_features
    - research モジュールの生ファクター（momentum / volatility / value）を統合。
    - ユニバースフィルタ（最低株価・最低平均売買代金）適用。
    - 数値因子の Z スコア正規化（zscore_normalize を利用）と ±3 でのクリップ。
    - DuckDB 上で date 単位の置換（DELETE + INSERT）をトランザクションで行い冪等性を確保。ROLLBACK のハンドリングあり。
  - シグナル生成: generate_signals
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - AI スコアがない場合は中立（0.5）で補完。各コンポーネントの欠損は中立で補完。
    - weights の検証（未知キー無視、非数値/負値スキップ）と正規化を実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY を抑制。
    - BUY シグナル閾値（デフォルト 0.60）に基づく発行。
    - SELL シグナル生成（ストップロス、スコア低下）。価格欠損時は SELL 判定をスキップして警告。
    - signals テーブルへの日次置換はトランザクションで実施。

- 研究（Research）
  - ファクター計算: calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）
    - momentum: 1M/3M/6M、MA200 乖離（200 行未満は None）。
    - volatility: ATR(20) / close の相対 ATR、20日平均売買代金、出来高比率。
    - value: 最新財務データ（report_date <= target_date）を使った PER / ROE 計算。
  - 特徴量探索:
    - calc_forward_returns — 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic — Spearman ランク相関（ランクは同順位平均ランク、少数サンプル時の保護あり）。
    - factor_summary — 各カラムの基本統計量（count/mean/std/min/max/median）。
    - rank — 値リストを同順位平均でランク化（round で丸めて ties 検出の安定性を確保）。
  - research パッケージの公開 API を整備。

- バックテスト（Backtest）
  - メトリクス: BacktestMetrics dataclass と calc_metrics 実装。
    - CAGR, Sharpe (年次化、無リスク=0), Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算。
  - シミュレータ: PortfolioSimulator
    - DailySnapshot / TradeRecord dataclass。
    - execute_orders: SELL を先に処理（保有全量クローズ）、その後 BUY（部分利確非対応）。スリッページ・手数料モデル対応。
    - lot_size 対応、トレーディングデイの指定、価格がない/株数が 0 の場合のスキップ挙動。

Changed
-------
- 初期リリース（0.1.0）における初期実装。後続リリースでの細かな改善を予定。

Fixed
-----
- .env パーサーを堅牢化
  - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（クォートなしでは直前が空白/タブの '#' をコメント扱い）に対応。
  - .env ファイル読み込み失敗時に警告を出し安全に継続。

Security
--------
- .env 自動読み込み時に OS 環境変数を上書きしない保護機構（protected keys）を実装。
- KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト時など自動ロードを無効化可能。

Notes / Caveats
---------------
- apply_sector_cap: "unknown" セクターはセクター上限制御の対象外（設計上の意図）。
- calc_score_weights: 全銘柄スコアが 0 の場合は等金額配分へフォールバックしログ出力。
- calc_regime_multiplier: 未知レジーム時は警告ログの上で 1.0 にフォールバック。
- generate_signals: Bear レジーム時は BUY シグナルを抑制（設計仕様に基づく）。また、positions テーブルに peak_price / entry_date 等がないためトレーリングストップや時間決済は未実装。
- calc_position_sizes: open_prices 欠損や price <= 0 の場合は銘柄をスキップ。将来的に前日終値や取得原価をフォールバック値として利用する余地あり（TODO 記載あり）。
- DB 書き込み（features / signals）は日付単位の置換をトランザクションで行い、失敗時は ROLLBACK を試みる実装。

今後の改善候補（コード内コメントより推測）
------------------------------------
- 銘柄別の lot_size をサポートするため stocks マスタ導入と銘柄別 lot_map の受け入れ。
- position_sizing の価格フォールバック（前日終値・取得原価等）。
- generate_signals の未実装エグジット条件（トレーリングストップ/時間決済）の実装。
- feature_engineering や signal_generator の性能・並列化改善。

署名
----
この CHANGELOG はリポジトリ内のソースコードから機能・挙動を解釈して作成しています。実際のリリースノートはコミット履歴・リリース当時の差分に基づいて作成してください。