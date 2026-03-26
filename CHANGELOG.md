CHANGELOG
=========
(このプロジェクトは Keep a Changelog の慣習に従って変更履歴を管理します。)

[Unreleased]
------------

なし

[0.1.0] - 2026-03-26
--------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" の基本モジュール群を追加。
- パッケージ初期化:
  - kabusys パッケージのバージョンを 0.1.0 として定義。
  - パブリック API として data, strategy, execution, monitoring をエクスポート。

- 設定管理 (kabusys.config):
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）を追加し、CWD に依存しない自動ロードを実現。
  - .env のパースは以下をサポート／考慮:
    - 空行・コメント行のスキップ、export キーワードの許容、
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、
    - クォートなし値の行内コメント処理（直前がスペース/タブの `#` をコメントとみなす）。
  - 自動ロードの無効化フラグ (KABUSYS_DISABLE_AUTO_ENV_LOAD) を用意。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベル等の取得メソッドを公開。必須変数未設定時に ValueError を送出する _require を実装。

- ポートフォリオ構築 (kabusys.portfolio):
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（同点時は signal_rank 昇順）でソートし上位 N 件を選定。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額配分にフォールバックし WARNING を出す）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中を制限するフィルタ。既存保有のセクターエクスポージャを計算し上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた資金乗数（1.0 / 0.7 / 0.3）を返す。未知レジームは警告のうえ 1.0 にフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算。リスクベースの基本ロジック、per-position 上限、aggregate cap のスケーリング、lot_size（現状共通単元）での丸め、cost_buffer による保守的コスト見積りなどをサポート。

- 戦略 (kabusys.strategy):
  - feature_engineering:
    - research 側で算出した生ファクターを取り込み、ユニバースフィルタ（最低株価/平均売買代金）を適用後、Z スコア正規化（±3 クリップ）して features テーブルへ冪等的に書き込む。
    - DuckDB を利用し prices_daily / raw_financials を参照。
  - signal_generator:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付き合算で final_score を算出。
    - Bear レジーム判定により BUY シグナルの抑制を行うロジックを実装（AI の regime_score を集計）。
    - BUY/SELL シグナルのルールを実装（threshold ベースの BUY、ストップロス・スコア低下による SELL）。
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入）で冪等性を確保。
    - user 指定の weights の妥当性検証（既知キーのみ、有効数値のみ、合計のリスケーリング）を実装。

- リサーチ (kabusys.research):
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を用いて各種ファクター（mom_1m/3m/6m, ma200_dev, atr_20/atr_pct, avg_turnover, volume_ratio, per/roe 等）を計算。
    - データ不足時の None ハンドリング（ウィンドウ行数チェック等）。
  - feature_exploration:
    - calc_forward_returns: 各ホライズン（デフォルト: 1,5,21 営業日）に対する将来リターンを一括で取得する SQL 実装。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算を提供（有効レコード数が 3 未満の場合は None）。
    - factor_summary / rank: 基本統計量計算とランク付けユーティリティを提供。
  - zscore_normalize を data.stats から re-export（public API に含めた）。

- バックテスト (kabusys.backtest):
  - simulator:
    - PortfolioSimulator: 擬似約定・ポートフォリオ管理クラス。SELL を先に処理してから BUY を処理する仕様、部分クローズ非対応（SELL は保有全量をクローズ）。
    - TradeRecord / DailySnapshot のデータ構造を定義。
    - スリッページ・手数料モデルを引数で受ける形での約定計算（実装途中の細部あり）。
  - metrics:
    - バックテスト評価指標の計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）を提供する calc_metrics。

Changed
- 初版につき変更履歴なし（初回追加のみ）。

Fixed
- 初版につき修正履歴なし。

Deprecated
- なし

Removed
- なし

Security
- なし（ただし設定管理は環境変数を扱うため、機密情報は .env/.env.local 管理と OS 環境保護推奨）。

Notes / Known issues & TODOs
- 設定読み込み:
  - .env の読み込みはプロジェクトルートが特定できない場合スキップされる。テスト等で自動ロードを無効にするための KABUSYS_DISABLE_AUTO_ENV_LOAD が用意されている。
- risk_adjustment.apply_sector_cap:
  - price_map に price が欠損（0.0）だとエクスポージャーが過少評価され、ブロックが外れる可能性がある。将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO コメントあり。
- position_sizing:
  - 単元株（lot_size）は現在全銘柄共通のパラメータであり、将来的に銘柄別 lot_map を受け取る拡張が想定されている（TODO）。
- signal_generator:
  - Bear レジーム時は generate_signals が BUY シグナルを抑制する設計。Bear 検知は ai_scores の regime_score に依存し、サンプル数が不足する場合は Bear 判定は行わない（誤判定防止）。
  - 未実装の SELL 条件（トレーリングストップ・時間決済）は comments として明記されている。これらは positions テーブルに peak_price / entry_date の拡張が必要。
- backtest.simulator:
  - BUY の実行ロジックの末尾に続きの実装が存在（コード断片あり）。部分約定や単元丸めに関する扱いについては使用前に確認が必要。
- DuckDB を用いる設計のため、本リリースでは DuckDB スキーマ（prices_daily, raw_financials, features, ai_scores, positions, signals など）の準備が前提。

Migration / Usage notes
- Settings により必須の環境変数が定義されている（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。未設定時は ValueError が投げられるため、.env.example 等を参考に設定を用意してください。
- strategy / research / portfolio の関数は基本的に DuckDB 接続か純粋関数を受け取り、外部 API 呼び出しや DB 書き込みの副作用を最小化している。テストや運用時は DuckDB のテーブル準備が必要です。

参考
- この CHANGELOG はコード内の docstring と TODO コメント、関数名・振る舞いから推測して作成しています。実際の変更履歴として使う場合は開発履歴（コミットログ）に基づいた追補・訂正を推奨します。