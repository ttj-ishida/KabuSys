Keep a Changelog
すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

[Unreleased]

[0.1.0] - 2026-03-26
Added
- パッケージ基本
  - kabusys パッケージ初期リリース。__version__ を "0.1.0" に設定。
  - パッケージの公開 API を __all__ で整理（data / strategy / execution / monitoring 等）。
- 設定管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（読み込み順: OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途を想定）。
  - プロジェクトルート検出: .git または pyproject.toml を起点に探索（CWD 非依存）。
  - .env 行パーサを実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理（クォート有無で挙動差分）。
  - 環境変数読み込み時に既存 OS 環境変数を保護する protected 機構を導入。
  - Settings クラスを追加。主なプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須取得（未設定時は ValueError）。
    - KABU_API_BASE_URL / DUCKDB_PATH / SQLITE_PATH のデフォルト値を提供。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証。
    - is_live / is_paper / is_dev のユーティリティプロパティ。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を返す。スコア同点時は signal_rank 昇順でタイブレーク。
    - calc_equal_weights: 等金額配分（各銘柄 1/N）。
    - calc_score_weights: スコア比率で配分。全銘柄スコアが 0 の場合は等金額にフォールバックし WARNING を出力。
  - risk_adjustment:
    - apply_sector_cap: セクターごとの既存保有比率が max_sector_pct を超える場合、同セクターの新規候補を除外（unknown セクターは除外対象外）。sell_codes により当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に基づく投下資金乗数を返す（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして警告を出力。
  - position_sizing:
    - calc_position_sizes: allocation_method に応じた発注株数計算を実装（"risk_based" / "equal" / "score" をサポート）。
    - risk_based: risk_pct と stop_loss_pct からベース株数を算出し、単元株（lot_size）で丸め。
    - equal/score: weight に基づく配分を portfolio_value・max_utilization で算出し単元丸め。
    - per-position 上限（max_position_pct）・aggregate cap（available_cash）を考慮。cost_buffer による保守的なコスト見積もりを導入。
    - aggregate cap 超過時は全銘柄をスケールダウンし、lot_size 単位の残差配分アルゴリズムで追加配分を行う（再現性のため安定ソート実施）。
- ストラテジー（kabusys.strategy）
  - feature_engineering.build_features:
    - research モジュールの生ファクター（momentum / volatility / value）を統合し、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 選択した数値ファクターを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - DuckDB を用いて features テーブルへ日付単位の置換（トランザクション＋バルク挿入で冪等性を確保）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算して final_score を算出。
    - 重みのマージ・検証機構を実装（不正なキーや値は無視、合計が 1 になるようリスケーリング）。
    - AI の regime_score を集計して Bear レジーム判定（サンプル数最小制約あり）。Bear の場合は BUY シグナルを抑制。
    - BUY は threshold（デフォルト 0.60）超で生成、SELL はストップロス（-8%）とスコア低下で判定。保有ポジションの SELL は BUY より優先し、signals テーブルへ日付単位で置換。
    - features が空や保有銘柄が features にない場合は警告ログを出力して挙動を明示。
- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率を計算（ウィンドウ不足時は None）。
    - calc_volatility: 20 日 ATR（true_range 処理で high/low/prev_close の欠損を考慮）、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS 欠損/0 の場合 PER は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得、範囲を効率的に限定。
    - calc_ic: factor と将来リターンを code で結合して Spearman（ランク相関）を計算。有効レコード数が 3 未満なら None を返す。
    - factor_summary / rank: 基本統計量と平均ランク同順位処理を提供。ランク計算は round(..., 12) で丸めて ties を安定検出。
  - research パッケージは外部重い依存を避け、DuckDB と標準ライブラリで実装。
- バックテスト（kabusys.backtest）
  - simulator:
    - DailySnapshot / TradeRecord データクラスを定義。
    - PortfolioSimulator 実装: メモリ内で状態管理（cash, positions, cost_basis, history, trades）。
    - execute_orders: SELL を先、BUY を後で処理。SELL は保有全量をクローズ（部分利確非対応）。スリッページ率は BUY が正、SELL が負の符号規約で使用。commission_rate による手数料計算。lot_size パラメータ対応。
  - metrics:
    - calc_metrics と内部関数群を追加: CAGR, Sharpe Ratio（無リスク金利=0、252 日で年次化）、Max Drawdown、Win Rate、Payoff Ratio、total_trades を計算。
    - 定義・境界条件（データ不足時の 0.0 戻し）を明示。
- 内部設計・ドキュメント
  - 各主要機能は純粋関数または DB 参照を明確に分離（ポートフォリオロジックはメモリ計算、strategy/research は DuckDB を受け取る等）。
  - 多くの箇所でログ警告を追加し、異常系やフォールバック動作を明示。

Known issues / TODO
- portfolio.position_sizing:
  - 銘柄ごとの単元株（lot_size）を銘柄マスタで持つよう拡張する TODO（現在は全銘柄共通の lot_size パラメータ）。
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に価格欠損（0.0） がある場合、エクスポージャーが過少評価される可能性あり。前日終値や取得原価を用いるフォールバック実装を検討中（TODO コメントあり）。
- strategy.signal_generator:
  - トレーリングストップや時間決済（保有 60 営業日超）等、一部のエグジット条件は未実装（positions に peak_price / entry_date が必要）。
- env パーサ:
  - コメント / クォート周りの細かな挙動は実装上の方針があり、既知のルールに従う（詳細は実装コメント参照）。
- general:
  - 一部の挙動は警告ログでフォールバックする実装になっているため、本番運用前にログ確認・テストを推奨。

開発者向けメモ
- DuckDB を入出力に用いる設計（features / prices_daily / raw_financials / ai_scores / positions / signals テーブル想定）。
- パッケージは副作用を最小限にする方針（設定読み込みは自動だが無効化可能、DB 参照は関数引数で受け取る）。

--------------------------------------------------------------------------------
（注）この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時は差分・コミットログ・マージ履歴を参照して適宜補正してください。