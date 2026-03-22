# Changelog

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」準拠の形式で記述しています。

フォーマット:
- すべてのバージョンは SemVer に従います。
- 各リリースにはカテゴリ（Added, Changed, Fixed, Security, …）を付与します。

## [0.1.0] - 2026-03-22

初回公開リリース。

### Added（追加）
- パッケージ基盤
  - kabusys パッケージの初期公開。バージョンは 0.1.0。
  - パッケージ public API: data, strategy, execution, monitoring（__all__ に定義）。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local ファイルと OS 環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応（テスト用途）。
  - .env パーサ実装:
    - export KEY=val 形式、クォート（シングル／ダブル）とバックスラッシュエスケープ、インラインコメント対応。
    - クォートなし値の # をコメントとして扱うルール（直前が空白またはタブの場合）。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック。
    - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL の値検証。
    - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）取得/展開。
    - is_live / is_paper / is_dev ヘルパー。

- 研究用ファクター計算（kabusys.research）
  - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials を参照してファクターを計算。
  - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
  - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。
  - factor_summary / rank: ファクターの統計サマリー＆同順位平均ランク処理。
  - 実装方針: DuckDB + 標準ライブラリのみで動作、ルックアヘッドを避ける設計。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date): research で得た raw ファクターをマージ、ユニバースフィルタ（最低株価 300 円・20日平均売買代金 5 億円）を適用、Zスコア正規化（指定列）→ ±3 でクリップし features テーブルへ日付単位で置換（冪等／トランザクション処理）。
  - 欠損／外れ値の取り扱い、最新価格取得は target_date 以前の最終値を参照して休場日対応。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合して各銘柄のコンポーネント（momentum/value/volatility/liquidity/news）を算出。
    - コンポーネントはシグモイド変換／補完（欠損は中立 0.5）して重み付き合算で final_score を計算。
    - デフォルト重みは StrategyModel.md に基づく値を採用。ユーザー指定の weights は検証・合成・再スケールされる（不正値は無視）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上）により BUY を抑制。
    - SELL（エグジット）判定: ストップロス（-8%）優先、スコア低下（threshold 未満）などを実装。positions / prices を参照して判定。
    - signals テーブルへ日付単位置換で書き込み（冪等／トランザクション処理）。

- バックテストフレームワーク（kabusys.backtest）
  - run_backtest(conn, start_date, end_date, initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20):
    - 本番 DuckDB からバックテスト用に範囲フィルタしたデータを in-memory DuckDB にコピー（init_schema(":memory:") を利用）して隔離されたバックテスト環境を構築。
    - 日次ループ: 前日シグナルの約定、positions の書き戻し、終値で時価評価、generate_signals による翌日シグナル生成、ポジションサイジング、約定処理の順で処理。
    - 日付範囲のコピー最適化やテーブル単位のコピー失敗時ログ出力を実装。
  - PortfolioSimulator:
    - メモリ内でのポジション／コスト管理、BUY/SELL の擬似約定（始値で約定、スリッページ・手数料モデル適用）。
    - SELL は保有全量クローズ（部分利確未対応）、BUY は配分に応じて株数を切り下げ。
    - mark_to_market により DailySnapshot を記録（終値欠損は 0 評価で警告）。
  - バックテスト指標計算（kabusys.backtest.metrics）
    - calc_metrics(history, trades) により CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を算出。

### Changed（設計上の決定 / 実装上の注意）
- 外部依存の最小化:
  - research / exploration 機能は pandas などの外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。
- DuckDB を主要なデータ層として使用。in-memory コピーやウィンドウ関数を多用して効率的に集計を実行。
- ファイル／DB 書き込みは可能な限りトランザクション（BEGIN/COMMIT/ROLLBACK）で原子性を担保。ROLLBACK 失敗時は警告ログを出力。

### Fixed（既知の実装上の挙動・保護）
- .env 読み込みでファイルが開けない場合は警告を出し自動ロードを続行（致命的失敗を回避）。
- weights 引数に不正な値（負値・NaN・非数値・未知キー）が含まれる場合はその要素をスキップし、デフォルト重みへフォールバックまたは正規化を行う。

### Internal / Notes（内部実装・既知の制約）
- ルックアヘッド回避:
  - 全ての戦略・研究機能は target_date 時点のデータのみを利用するよう設計（将来データ参照を意図的に防止）。
- 一部未実装の戦術（既知）:
  - トレーリングストップや時間決済（保有 60 営業日超）等は現時点で未実装（必要データ: positions に peak_price / entry_date）。
- デフォルト値（参照用）:
  - features 正規化クリップ: ±3.0
  - ユニバース最小株価: 300 円
  - ユニバース最小 20 日平均売買代金: 5e8 円
  - BUY threshold デフォルト: 0.60
  - STOP_LOSS_RATE: -0.08（-8%）
  - run_backtest の slippage_rate デフォルト: 0.001（0.1%）
  - run_backtest の commission_rate デフォルト: 0.00055（0.055%）
  - run_backtest の initial_cash デフォルト: 10_000_000 円
  - run_backtest の max_position_pct デフォルト: 0.20（1 銘柄あたり最大 20%）
- 必要環境:
  - DuckDB の Python バインディングが必要（DuckDB の SQL ウィンドウ関数を多用）。
  - .env.example を参考に環境変数を用意すること。

---

今後の予定（例）
- ポジション管理の強化（部分利確／トレーリングストップ／時間決済の実装）
- execution 層（発注 API 統合）およびモニタリング周りの実装拡充
- テストカバレッジと CI の追加

（問題・要望があれば ISSUE を作成してください）