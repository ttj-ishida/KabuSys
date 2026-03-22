CHANGELOG
=========

すべての重要な変更履歴をこのファイルに記録します。形式は "Keep a Changelog" に準拠します。

[Unreleased]
------------

- 現在未リリースの変更はありません。

[0.1.0] - 2026-03-22
-------------------

Added
- パッケージ初回リリース。
- 基本構成
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージの公開 API を定義（data, strategy, execution, monitoring を __all__ に含める）。
- 環境設定管理（kabusys.config）
  - .env / .env.local からの自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索するため、CWD に依存しない読み込みを実現。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを提供（テスト用途を想定）。
  - 複雑な .env 行のパースに対応（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルールなど）。
  - OS 環境変数を保護する protected オプションを採用して .env.local の上書きを制御。
  - Settings クラスを提供し、アプリケーションで使用する主要な環境変数アクセスをラップ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト付与）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（Path オブジェクトを返す）
    - KABUSYS_ENV（validation: development / paper_trading / live）
    - LOG_LEVEL（validation: DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のユーティリティプロパティ
- 特徴量計算 / 戦略（kabusys.strategy）
  - feature_engineering.build_features(conn, target_date)
    - research モジュールで算出した raw factors を統合、ユニバースフィルタ（最低株価・最低平均売買代金）を適用し、指定カラムを Z スコア正規化・±3 でクリップして features テーブルに日単位の置換（削除→挿入）で保存。トランザクションにより原子性を保証。
    - DuckDB を想定した SQL と Python の組合せで実装。
  - signal_generator.generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features / ai_scores / positions を参照して各銘柄のコンポーネントスコア（momentum, value, volatility, liquidity, news）を計算、重み付き合算により final_score を計算して BUY / SELL シグナルを生成。
    - AI の regime_score に基づく Bear レジーム検知により BUY シグナル抑制ロジックを実装。
    - SELL 条件としてストップロス（-8%）とスコア低下を実装。SELL は保有銘柄優先で BUY から除外しランクを再付与。
    - 重み（weights）は不正値や未知キーを無視し、合計が 1.0 になるように補正。
    - signals テーブルへの日付単位置換はトランザクションで実施（ROLLBACK の失敗をログ警告）。
- リサーチユーティリティ（kabusys.research）
  - calc_momentum / calc_volatility / calc_value を提供し、prices_daily / raw_financials からモメンタム・ボラティリティ・バリュー系ファクターを算出。
  - calc_forward_returns(conn, target_date, horizons=[1,5,21])
    - 指定日の終値から各ホライズン先の値までの将来リターンを効率的に取得（1 クエリで複数ホライズン）。
    - horizons のバリデーション（正の整数かつ <=252）。
  - calc_ic(factor_records, forward_records, factor_col, return_col)
    - Spearman のランク相関（IC）を実装。サンプル数が 3 未満や分散がゼロの場合は None を返す。
  - factor_summary(records, columns)
    - count, mean, std, min, max, median のサマリを返す。
  - rank(values)
    - 同順位は平均ランクとするランク付けを実装（浮動小数の丸めで ties を安定検出）。
  - 研究用モジュールは pandas 等に依存せず標準ライブラリ + DuckDB の SQL を活用する設計。
- バックテスト（kabusys.backtest）
  - simulator.PortfolioSimulator
    - メモリ内でのポートフォリオ状態管理、BUY/SELL の擬似約定（スリッページ・手数料を反映）。SELL は保有全量をクローズ。約定は始値を基にスリッページ適用。
    - mark_to_market で DailySnapshot を記録。保有銘柄に終値が欠ける場合は 0 評価で警告ログ。
    - TradeRecord / DailySnapshot の dataclass 定義を提供。
  - metrics.calc_metrics / BacktestMetrics
    - CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算するユーティリティ。
  - engine.run_backtest(conn, start_date, end_date, ...)
    - 本番 DB からインメモリ DuckDB へ必要データをコピーして（signals/positions を汚さないように）日次でシミュレーションを実行するフローを提供。
    - コピー対象テーブル: prices_daily, features, ai_scores, market_regime を日付範囲でフィルタコピー。market_calendar は全件コピー。
    - 日次ループ: 前日シグナルの約定→positions の書き戻し→時価評価→generate_signals によるシグナル生成→シグナル読み込み→ポジションサイジング→次日のオーダー組成。
    - バックテスト用接続構築時に init_schema(":memory:") を利用。
- 実装上の安全策・運用面
  - DB 操作はトランザクション（BEGIN/COMMIT/ROLLBACK）で実施し、ROLLBACK 失敗をログで通知。
  - 多くの箇所で入力バリデーション（数値の有限性チェック、None の扱い、最小サンプル数判定など）を導入して堅牢性を高めた。
  - 明示的に未実装/拡張予定な設計ノートをコード内コメントで残す（例: トレーリングストップ、時間決済、PBR 等）。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Deprecated
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Security
- 初版のため該当なし。

Notes / Known limitations
- trailing stop / 時間決済など、StrategyModel に記載の一部条件は未実装（コメントで明記）。positions テーブルに peak_price / entry_date 等の追加が必要。
- zscore_normalize の実装は data.stats モジュールに依存（このリリースでは参照）。外部ライブラリに依存しない設計を維持する一方、詳細な統計ユーティリティは別モジュールで提供。
- バックテストでは日付範囲コピーに失敗した場合に警告を出してスキップする実装のため、部分的にデータ欠落があると結果に影響する可能性がある。
- 本リリースは DuckDB を前提としており、他の DB での動作は保証しない。

作者/貢献
- 初回実装: コードベースに含まれる各モジュールの寄稿者に感謝します。今後の改善・バグ修正・機能追加を歓迎します。