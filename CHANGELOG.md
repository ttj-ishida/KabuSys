# Changelog

すべての注記は Keep a Changelog の形式に従います。  
このプロジェクトの初期リリースにおける変更点を、コードベースから推測して日本語でまとめています。

注: バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に準拠しています。

## [0.1.0] - 2026-03-22

### Added
- パッケージ基盤を追加
  - パッケージ名: kabusys、エクスポート: data, strategy, execution, monitoring（src/kabusys/__init__.py）。
- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml）を検出して .env / .env.local を自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - 必須キー取得時に未設定なら明示的に例外を投げる _require()。
  - 設定例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL。
  - env 値の検証（KABUSYS_ENV の許容値・LOG_LEVEL の許容値）と利便性プロパティ（is_live / is_paper / is_dev）。
- .env パーサーの実装（src/kabusys/config.py）
  - export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメント処理（クォート無しの場合にスペース直前の # をコメントと判定）をサポート。
  - OS 環境変数保護（既存の環境変数を破壊しないデフォルト挙動）と override フラグを備えた読み込み関数。
- 戦略（strategy）モジュール
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - Research 側で算出した raw ファクターを結合、ユニバースフィルタ（最低株価・平均売買代金）を適用後、Z スコア正規化・±3 でクリップして features テーブルへ UPSERT（トランザクションで日付単位置換）する build_features(conn, target_date) を提供。
    - ルックアヘッド防止のため target_date 時点のデータのみ使用する設計。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付け合算により final_score を算出する generate_signals(conn, target_date, ...) を提供。
    - 重みのフォールバック・検証・リスケーリングロジックを実装（デフォルトの重みは StrategyModel.md の想定値に合わせる）。
    - Bear レジーム判定（AI の regime_score 平均が負の場合に BUY を抑制）、および保有ポジションに対するエグジット条件（ストップロス、スコア低下）を実装。
    - signals テーブルへの日付単位の置換（冪等性）を保証。
- Research モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum(conn, target_date): mom_1m/3m/6m、ma200_dev（200日MA乖離）を計算。
    - calc_volatility(conn, target_date): 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、volume_ratio を計算。
    - calc_value(conn, target_date): raw_financials から最新財務データを取得し PER/ROE を計算（EPS が 0 や欠損時は None）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns(conn, target_date, horizons): 将来リターン（翌日/翌週/翌月等）を計算。
    - calc_ic(factor_records, forward_records, ...): Spearman ランク相関（IC）を計算するユーティリティ。
    - factor_summary(records, columns): ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - rank(values): 同順位は平均ランクとするランク化ユーティリティ（丸めで tie 判定の安定化）。
  - research パッケージの __all__ で主要関数を公開。
- バックテストフレームワーク（src/kabusys/backtest）
  - ポートフォリオシミュレータ（src/kabusys/backtest/simulator.py）
    - PortfolioSimulator クラス: メモリ上でのポジション管理、BUY/SELL の擬似約定（指定のスリッページ・手数料モデル）、約定記録 TradeRecord、日次スナップショット DailySnapshot を提供。
    - SELL を先に処理することで資金確保を行う仕様。BUY は手数料込みで購入可能な最大株数に調整。
    - mark_to_market で終値評価、保有銘柄に終値がない場合は 0 として警告ログ。
  - メトリクス（src/kabusys/backtest/metrics.py）
    - calc_metrics(history, trades) が BacktestMetrics（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）を返す。
  - バックテストエンジン（src/kabusys/backtest/engine.py）
    - run_backtest(conn, start_date, end_date, ...) により、本番 DB からインメモリ DuckDB へ必要データをコピーして日次ループでシミュレーションを実行するパイプラインを実装。
    - _build_backtest_conn: 本番 DB から date 範囲でテーブルをコピー（prices_daily, features, ai_scores, market_regime, market_calendar）。
    - 日次処理の流れ: 前日シグナル約定 → positions を書き戻し → 時価評価を記録 → generate_signals 呼び出し → ポジションサイジングと発注（BUY シグナルの割当計算）を実施。
    - positions テーブルへの冪等書き戻し、signals 読み取りユーティリティ等を提供。
- ロギング・エラーハンドリング
  - 各モジュールで適切に logger を使用し、WARN/INFO/DEBUG のログ出力ポイントが多数実装。
  - トランザクション処理（BEGIN/COMMIT/ROLLBACK）と rollback 失敗時の警告処理を実装（features/generate_signals 等）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- .env 解析の堅牢化
  - クォート内でのバックスラッシュエスケープと対応する閉じクォート検索を実装し、インラインコメントや特殊文字の正しい解釈を改善。
  - export KEY=val 形式のサポート、コメント判定ルールの明確化。
- DB 操作・トランザクションの堅牢化
  - features / signals 挿入時に日付単位で削除→挿入を行い、例外時に確実にロールバックを試みる実装。

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- 環境変数読み込みで既存 OS 環境変数を保護する protected オプションを採用。自動読み込みは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

補足（利用上の注意）
- Research / factor 計算・バックテストは DuckDB の prices_daily / raw_financials 等のテーブルを前提としているため、実行前にスキーマ初期化・データ投入が必要です（src/kabusys/data.schema 等に依存）。
- 研究コード・戦略ロジックは「ルックアヘッド防止」を意識して実装されていますが、データ準備や時間軸の取り扱いによって結果が変わるため、実運用前に十分な検証を行ってください。
- ai_scores / positions / market_regime 等一部テーブルのカラム設計に依存したロジックが含まれるため、既存データとの互換性に注意してください。