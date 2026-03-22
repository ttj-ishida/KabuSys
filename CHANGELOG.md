# Changelog

すべての注目すべき変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。意図的な互換性ポリシーはセマンティックバージョニングに従います。

= Unreleased =
（現時点の未リリース変更はありません）

[0.1.0] - 2026-03-22
-------------------

Added
- 初回リリースを公開（パッケージバージョン: 0.1.0）。
- パッケージ構成
  - 公開トップレベル API を定義（kabusys.__init__ にて version と __all__ を設定）。
  - サブパッケージ: data, strategy, execution, monitoring（将来的な拡張を想定したエクスポート）。
- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml を基準に探索して .env/.env.local を読み込む。
    - OS 環境変数を保護する仕組み（.env.local は上書き、.env は未設定キーのみセット）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 強力な .env パーサー実装:
    - コメント、export プレフィックス、クォート文字、バックスラッシュエスケープ、インラインコメントの取り扱い等に対応。
  - 必須キー取得用の _require()、環境値検証（KABUSYS_ENV, LOG_LEVEL）のバリデーションあり。
  - 例: JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID / DUCKDB_PATH / SQLITE_PATH 等の設定取得プロパティを提供。
- 戦略（kabusys.strategy）
  - 特徴量作成（feature_engineering.build_features）
    - 研究環境で計算した生ファクターを正規化・合成し features テーブルへ UPSERT（冪等）。
    - ユニバースフィルタ（最低株価/最低平均売買代金）を実装（デフォルト: 300 円、5 億円）。
    - Z スコア正規化（指定列）と ±3 でのクリップ、DuckDB トランザクションを用いた日付単位の置換（BEGIN/COMMIT/ROLLBACK）で原子性を保証。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付き合算で final_score を算出。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と閾値（BUY 閾値 0.60）を提供。外部から重みを渡せるが検証・再スケールの処理を実施。
    - Bear レジーム検知（ai_scores の regime_score の平均が負 -> BUY を抑制）。サンプル不足時は Bear としない。
    - 保有ポジションに対するエグジット条件（ストップロス -8%、スコア低下）を実装。SELL 対象は BUY から除外してランク再付与。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入で冪等性）。
    - 欠損値の扱い: コンポーネントが None の場合は中立値 0.5 で補完（過度な降格を防止）。
- 研究ツール（kabusys.research）
  - ファクター計算（factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA 必要数チェック）を計算。
    - calc_volatility: 20 日 ATR（true_range の NULL 伝播制御）、atr_pct、avg_turnover、volume_ratio を計算。
    - calc_value: raw_financials から直近財務データを取得し PER / ROE を計算（EPS が 0 または欠損の場合は None）。
    - SQL + DuckDB ベースで、prices_daily / raw_financials のみを参照。外部 API にはアクセスしない設計。
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21]）先の将来リターンを計算。範囲チェック（horizons は 1〜252）。
    - calc_ic: Spearman（ランク相関）による Information Coefficient（IC）を計算。サンプル不足（3 未満）は None を返す。
    - factor_summary: count/mean/std/min/max/median を算出。
    - rank: 同順位は平均ランクを採用（丸めにより ties 検出を安定化）。
  - 研究ユーティリティは pandas 等に依存せず標準ライブラリ + duckdb を使用。
- バックテスト（kabusys.backtest）
  - シミュレータ（backtest.simulator.PortfolioSimulator）
    - 擬似約定ロジック（SELL を先に処理、BUY は配分に応じて株数を計算、スリッページ・手数料モデルを適用）。
    - mark_to_market により DailySnapshot を記録。約定記録は TradeRecord（realized_pnl を SELL 時のみ保持）。
    - 初期現金の与え方、取引日付の扱い（history が空の場合のデフォルト日付処理）等を備える。
  - メトリクス（backtest.metrics）
    - CAGR, Sharpe Ratio（無リスク金利=0）, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算するユーティリティを提供。
  - エンジン（backtest.engine.run_backtest）
    - 本番 DuckDB から必要データをインメモリ DuckDB へ部分コピーしてバックテスト用接続を構築（signals/positions を汚染しない）。
    - 日次ループ: 前日シグナルの約定 -> positions テーブル書き戻し -> 時価評価記録 -> generate_signals 呼び出し -> 発注リスト組成（ポジションサイジング）... のフローを実装。
    - デフォルトパラメータ: initial_cash=10_000_000 円、slippage_rate=0.001、commission_rate=0.00055、max_position_pct=0.20。
    - DB テーブルの部分コピー時に失敗した場合は警告ログを出しスキップする堅牢性（_build_backtest_conn）。
- パッケージ内部での堅牢性・ログ
  - DuckDB 操作時のトランザクション（BEGIN/COMMIT/ROLLBACK）や例外時のロールバック処理、warning/情報ログ出力を適切に追加。
  - 欠損データに対する安全処理（価格欠損時の SELL 判定スキップ / features に存在しない保有銘柄の扱いなど）。

Changed
- N/A（初回リリースのため履歴上の変更は無し）

Fixed
- N/A（初回リリース）

Removed
- N/A（初回リリース）

Notes / Known limitations
- signal_generator のエグジット条件は一部未実装（トレーリングストップ、時間決済などは実装予定で、positions に peak_price / entry_date が必要）。
- 一部の集計・解析は研究向け（research/）に実装されており、本番発注層（execution）への依存を避ける設計。
- DuckDB のスキーマ（tables: prices_daily, features, ai_scores, positions, signals, raw_financials, market_calendar 等）は外部に定義される前提。init_schema 等の存在を仮定した処理がある。
- 現バージョンでは外部依存（pandas 等）を明示的に排除しているため、大規模データ処理時はパフォーマンス調整や最適化が必要な場合がある。

Authors
- 実装者（コードベースから想定）: kabusys 開発チーム

関連ドキュメント
- コード内で参照される設計ドキュメント: StrategyModel.md, BacktestFramework.md（実装の設計方針や数値の由来が記載されている想定）

----- End of CHANGELOG -----

もし CHANGELOG に追記したい項目（例えば採用した設計判断の詳細、公開 API の例、将来のマイルストーンなど）があれば教えてください。必要に応じてカテゴリ分けや日本語表現を調整します。