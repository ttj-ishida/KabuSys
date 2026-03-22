# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]


## [0.1.0] - 2026-03-22
初回リリース。日本株自動売買システムのコア機能を実装しました。

### Added
- パッケージ初期化
  - kabusys.__init__ にバージョン番号 (0.1.0) と公開モジュール一覧を追加。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数の読み込み機能を実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - .env と .env.local の読み込み優先順位制御（OS環境変数保護機構を導入）。
  - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得ヘルパー（未設定時は ValueError）。
  - Settings クラスを導入し、J-Quants / kabu API / Slack / DBパス / 環境（development/paper_trading/live）/ログレベルの取得とバリデーションを提供。

- 戦略 - 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date) を実装:
    - research モジュールの生ファクターを取得（calc_momentum, calc_volatility, calc_value）。
    - ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 指定列に対する Z スコア正規化（外れ値は ±3 でクリップ）。
    - features テーブルへの日付単位での置換（トランザクションとバルク挿入で冪等性を確保）。
  - 欠損データ・非有限値に対する安全処理とログ出力を実装。

- 戦略 - シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold, weights) を実装:
    - features と ai_scores を統合して各銘柄のコンポーネントスコアを計算（momentum/value/volatility/liquidity/news）。
    - Sigmoid 変換、欠損コンポーネントは中立 (0.5) 補完。
    - 重みのマージ / スケーリング（不正な重みは安全に無視し、合計が 1.0 に正規化）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合に BUY を抑制）。
    - BUY/SELL シグナルの生成ロジック（STOP_LOSS, score_drop 等）を実装。
    - signals テーブルへ日付単位で置換（トランザクション、ROLLBACK ハンドリング）。
    - generate_signals は発注層（execution）に依存しない純粋なシグナル生成。

- リサーチ機能 (kabusys.research)
  - ファクター計算 (factor_research):
    - calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials テーブル参照）。
    - 各関数は (date, code) キーの dict リストを返す。
    - MA200, ATR20, 20日平均売買代金、出来高比率などを算出。
  - 特徴量評価 (feature_exploration):
    - calc_forward_returns(conn, target_date, horizons) を実装（複数ホライズンの将来リターンを同時に取得する最適化SQLを含む）。
    - calc_ic(factor_records, forward_records, factor_col, return_col)（スピアマンランク相関）を実装。
    - factor_summary(records, columns)（count/mean/std/min/max/median）を実装。
    - rank(values)（同順位は平均ランク）を実装。
  - 外部ライブラリに依存せず、DuckDB と標準ライブラリのみで実装。

- バックテストフレームワーク (kabusys.backtest)
  - シミュレータ (simulator):
    - PortfolioSimulator を実装（メモリ内でポートフォリオ状態管理）。
    - 約定ロジック: スリッページ、手数料考慮、SELL を先に処理、BUY は資金不足を考慮して株数を再計算。
    - mark_to_market により DailySnapshot を記録（終値欠損時は 0 評価して警告出力）。
    - TradeRecord / DailySnapshot のデータクラスを提供。
  - メトリクス (metrics):
    - calc_metrics を実装し、CAGR / Sharpe / MaxDrawdown / WinRate / PayoffRatio / total_trades を計算。
    - 内部関数で各指標を分離して実装。
  - エンジン (engine):
    - run_backtest(conn, start_date, end_date, ...) を実装。
    - 本番 DB からインメモリ DuckDB へ必要テーブルを日付フィルタ付きでコピーする _build_backtest_conn。
    - 日次ループ: 約定（前日シグナル→当日始値）、positions の書き戻し、時価評価、generate_signals 呼び出し、ポジションサイジングを行う一連処理を実装。
    - positions テーブルへ冪等に書き戻すユーティリティを実装。
    - 日付取得は market_calendar / calendar 管理を利用（get_trading_days 呼び出し）。

- パッケージのエクスポートを整理（strategy, research, backtest の __init__ にエクスポート関数を追加）。

### Changed
- （初版のため履歴なし）

### Fixed
- DB トランザクション内での例外発生時に ROLLBACK を試み、失敗時は警告ログを出すようにしてロールバック失敗の診断を容易にしました（各所で実装）。

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- 環境変数の自動ロード時、既存の OS 環境変数を上書きしない保護機能を実装（protected set）。

### Known issues / Notes
- _generate_sell_signals 内で言及されている一部のエグジット条件は未実装:
  - トレーリングストップ（peak_price に依存）および時間決済（entry_date に依存）はまだ実装されていません。positions テーブルに peak_price / entry_date 等の追加情報が必要です。
- calc_value では PBR / 配当利回りは未実装（将来的に追加予定）。
- backtest のデータコピー処理では、コピーに失敗したテーブルをスキップしてログに警告を出す設計になっています（データ整合性に注意）。
- .env 自動ロードはプロジェクトルートが特定できない場合はスキップされます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化可能です。
- 外部依存を最小化する設計（pandas 等を使わずに実装）だが、そのために若干パフォーマンスチューニングの余地が残っています。

---

今後のリリースでは、以下の点を予定しています:
- 未実装のエグジット条件（トレーリングストップ / 時間決済）の実装。
- 追加ファクター（PBR / 配当利回り）・リサーチの拡張。
- execution 層（kabu/ブローカー API 連携）の実装とテスト。
- ドキュメント・例（usage examples / API docs）の充実。