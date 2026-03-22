CHANGELOG
=========

すべての変更は Keep a Changelog のガイドラインに準拠して記載しています。
バージョン番号はパッケージ内の __version__（0.1.0）に合わせています。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-22
-------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」のコア機能を追加。
  - パッケージ構成（kabusys）と公開 API を追加。
    - kabusys.__all__ に data / strategy / execution / monitoring を定義。
  - 環境設定管理（kabusys.config）
    - .env / .env.local ファイル自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env の行パースは export プレフィックス、クォート、エスケープ、インラインコメント等に対応。
    - OS 環境変数を保護する読み込みロジック（.env.local は .env を上書き）。
    - 必須環境変数取得用の _require と Settings クラスを提供。主な設定:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（development / paper_trading / live のバリデーション）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
  - 戦略関連（kabusys.strategy）
    - feature_engineering.build_features(conn, target_date)
      - research モジュールで計算した生ファクターをマージしてユニバースフィルタ（最低株価・平均売買代金）を適用。
      - 指定カラムを Z スコア正規化し ±3 でクリップ。
      - DuckDB の features テーブルへ日付単位での置換（冪等、トランザクションで原子性を確保）。
      - 欠損・異常値に対する安全なハンドリングとログ出力。
    - signal_generator.generate_signals(conn, target_date, threshold=0.60, weights=None)
      - features と ai_scores を統合して momentum/value/volatility/liquidity/news のコンポーネントスコアを算出。
      - シグモイド変換、欠損列の中立補完（0.5）や重み正規化ロジックを実装。
      - Bear レジーム検知（ai_scores の regime_score の平均が負）時は BUY シグナルを抑制。
      - BUY / SELL 判定ロジック（閾値、ストップロス等）と signals テーブルへの日付単位置換（トランザクション）。
      - 不正な weights を警告して無視する検証を実装。
  - Research（kabusys.research）
    - factor_research モジュール
      - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials テーブルを参照。
      - モメンタム（1M/3M/6M、MA200乖離）、ATR（20日）、avg_turnover、volume_ratio、PER/ROE 等を算出。
      - データ不足時は None を返す設計。
    - feature_exploration モジュール
      - calc_forward_returns(conn, target_date, horizons=[1,5,21])：将来リターンを一括クエリで取得。
      - calc_ic(factor_records, forward_records, factor_col, return_col)：Spearman（ランク相関）による IC 計算（ties を平均ランクで扱う）。
      - factor_summary(records, columns)：count/mean/std/min/max/median を計算。
      - rank(values)：同順位は平均ランク扱い（丸めを用いて ties 検出）。
    - zscore_normalize は kabusys.data.stats から利用（本体は data パッケージに委譲）。
  - バックテストフレームワーク（kabusys.backtest）
    - simulator.PortfolioSimulator
      - メモリ内でポートフォリオ状態を管理（cash / positions / cost_basis / history / trades）。
      - execute_orders：SELL を先行処理、BUY は残金と alloc に基づき約定。BUY は手数料込みで再計算、部分買い分割は行わない（整数株数）。
      - スリッページ（open_price × (1 ± slippage_rate)）と手数料考慮、約定記録 TradeRecord を生成。
      - mark_to_market：終値で時価評価、欠損終値は 0 として WARN ログ。
    - metrics.calc_metrics / BacktestMetrics
      - CAGR、Sharpe、MaxDrawdown、WinRate、PayoffRatio、total_trades を計算。
      - 内部関数はデータ不足・ゼロ除算に強い実装。
    - engine.run_backtest(conn, start_date, end_date, ...)
      - 本番 DuckDB から必要データをインメモリへコピーしてバックテストを実行（signals/positions を汚さない）。
      - 日次ループ：前日シグナルを当日始値で約定 → positions を書き戻し → 終値で時価評価 → generate_signals（当日分） を呼び出し翌日注文を作成。
      - _build_backtest_conn, _fetch_open_prices, _fetch_close_prices, _write_positions, _read_day_signals 等のユーティリティを実装。
      - 戦略の再現性と DB 原子性のためトランザクション／コピー処理を利用。
  - パッケージ __init__ や各サブモジュールで __all__ を整備し、公開 API を明確化。

Changed
- N/A（初回リリースのため履歴上はなし）

Fixed
- N/A（初回リリースのため履歴上はなし）

Security
- 環境変数の必須チェック・保護（protected 環境変数セット）により、意図しない上書きを防止。
- .env の読み込み失敗時は warnings で通知し処理を継続（例外で起動が止まらない設計）。

Notes / 設計・運用上の重要点
- すべての DB 書き込み（features / signals / positions）は「日付単位の置換（DELETE→INSERT）」かつトランザクションで原子性を保証する実装。
- ルックアヘッドバイアス防止のため、すべての計算は target_date 時点のデータのみを参照する設計方針を明記。
- 欠損データに対しては中立補完（0.5）や None を許容する設計で、極端なデータ欠損でも処理が継続するように実装。
- バックテストでは本番 DB を直接変更しないためのインメモリコピー機構を実装。
- 一部機能（例：トレーリングストップ、時間決済など）は実装の注記があり今後の拡張余地を残す。

既知の制約・今後の改善案（コード中に明記）
- positions テーブルの拡張（peak_price / entry_date 等）がないため、トレーリングストップ等は未実装。
- execution 層（実際の発注 API との接続）や monitoring の実体はこのリリースでは未実装またはスケルトン。
- ai_scores の統合は中立補完を行うが、AI スコアの前処理・品質管理は外部に依存する想定。
- PBR や配当利回りなどのバリューファクターは未実装（将来的な追加対象）。

署名
- 初回公開バージョン 0.1.0 — 基本的な研究・シグナル生成・バックテスト基盤を提供する安定した出発点。