CHANGELOG
=========

すべての重要な変更履歴をここに記録します。これは Keep a Changelog の形式に準拠しています。
バージョン番号は semantic versioning に従います。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-13
-----------------

Added
- 基本パッケージ初期実装（kabusys v0.1.0）。
  - パッケージメタ情報: __version__ = "0.1.0" を追加。
- 実行エントリスクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境に応じて paper_trading 用 DB を分離して使用（KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
- 環境設定 / ローダー
  - config.py: .env 自動読み込み機能を実装（プロジェクトルート検出：.git または pyproject.toml を基準）。.env / .env.local の読み込み順と上書きルール（OS 環境変数保護）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 複雑な .env 行パーサを実装（export プレフィックス、クォート文字列、エスケープ、インラインコメント処理など）。
  - Settings クラスを実装し、各種設定（API トークン、DB パス、PID/KILL ファイルパス、閾値、環境判定ロジック、paper_trading 関連オプションなど）を環境変数から提供。
- Execution 関連コンポーネント（起動時に組み立てられる）
  - BrokerClientFactory（ブローカークライアント生成）
  - OrderRepository / OrderManager / Reconciler / RiskManager / ExecutionEngine（起動時連携）
  - RiskConfig / EngineConfig を用いた初期化と運用（例: RiskConfig にて各種制限パラメータを設定、初期ポートフォリオ値は broker.get_available_cash() により設定）。
- 監視 DB 初期化
  - init_monitoring_db を呼び監視テーブルの冪等な作成を保証（run_execution / run_monitoring 両方で呼び出し）。
- プロセス優先度・CPU アフィニティユーティリティ
  - utils/process_priority.py を追加。Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収してプロセス優先度を設定する set_process_priority(level)。CPU 固定用 set_cpu_affinity(cpu_count) も実装。権限不足や未対応 OS の場合は警告ログを出しスキップ。
- Portfolio 構成モジュール
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバックし警告ログ。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap と市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（レジームごとのデフォルトマッピングと不明レジームのフォールバック挙動）。
  - portfolio/position_sizing.py: risk_based / equal / score ベースの発注株数計算 calc_position_sizes を実装。単元株丸め、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ保守見積り）や aggregate スケーリングロジックを備える。
  - portfolio/__init__.py で上記関数を公開。
- 研究（research）モジュール
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算を DuckDB を用いて実装（prices_daily, raw_financials テーブル参照）。MA200、ATR20、各期間リターン、PER/ROE 等を計算。
  - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（スピアマン）計算（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。外部依存を避け標準ライブラリで完結する設計。
  - research/__init__.py で主要関数を公開（zscore_normalize は data.stats から再エクスポート）。
- AI ニュース NLP スコアリング
  - ai/news_nlp.py を追加。raw_news と news_symbols から記事を集約し、OpenAI (gpt-4o-mini) を用いて銘柄別センチメント（-1.0〜1.0）を計算して ai_scores テーブルへ書き込む。バッチ処理（最大 20 銘柄/チャンク）、スコアのクリップ、リトライ（429/ネットワーク/5xx に対する指数バックオフ）やレスポンスバリデーションを実装。API キーは引数または環境変数 OPENAI_API_KEY を参照。部分更新戦略（対象コードのみ DELETE→INSERT）により部分失敗時の既存スコア保護を考慮。
  - ニュースウィンドウのUTC計算 calc_news_window（JST ベースの時間ウィンドウ）を実装。
- ユーティリティ / ツール
  - tools/paper_verification_report.py: Paper Trading 向け検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH を読み、システム稼働率・注文成功率・送信率・レイテンシ（P95 等）・リスク却下数を集計して PASS/FAIL を判定するレポートを標準出力に出力。P95 計算や日付フィルタの組み立て、SQL のエラー耐性を実装。
  - tools パッケージ初期化ファイルを追加。

Changed
- 設計上の方針や挙動を明確化（ドキュメンテーションコメント）
  - 多くのモジュールに実装方針・制約（例: DuckDB を用いる、ローカル DB のみ参照、外部取引 API へはアクセスしない等）を明記。
  - ランタイムでの安全性を重視（例: レスポンスバリデーション、データ不足時の None フォールバック、例外キャッチしてログ出力して継続する挙動など）。
- 環境変数の扱い
  - .env 読み込みはプロジェクトルートが解決できない場合はスキップすることで配布後の挙動を安定化。

Fixed
- ファイル/値の不正に対するフォールバック処理
  - MONITOR_POLL_INTERVAL が不正（非整数や 0 以下）の場合にデフォルトにフォールバックして警告ログを出す実装を追加（run_monitoring）。
  - calc_score_weights で全スコアが 0 の場合に等金額配分に安全にフォールバックし、警告ログを出す。
  - process_priority/set_cpu_affinity が権限エラーや未対応環境で失敗してもプロセスを停止させない（警告ログのみ）ように改善。
  - Paper 検証レポートではテーブルが存在しない等の sqlite3.OperationalError を捕捉してレポート生成を継続できるようにした（存在しないテーブルは N/A として扱う）。
- レイテンシ統計（P95）計算の実装と欠損値取り扱い（paper_verification_report）。

Security
- API キーの取り扱いは環境変数（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を前提とし、未設定時は明示的にエラーを投げるか（必要に応じて）起動を中止する設計。 .env 自動読込はデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

Internal
- 多数のログ出力（info/debug/warning/exception）を追加し、運用時の可観測性を向上。
- DuckDB/SQLite を併用する I/O 層を採用（研究処理は DuckDB、監視は SQLite を利用する想定）。
- ドキュメント参照として各モジュール内に PortfolioConstruction.md / StrategyModel.md 等のセクション番号を示すコメントを追加（実装根拠の明示）。

注意事項 / 既知の制約
- 一部の箇所で将来的拡張を想定した TODO コメントあり（例: 銘柄ごとの lot_size 管理、価格フォールバック戦略など）。
- news_nlp の OpenAI 呼び出しは外部ネットワークに依存するため、API 利用制限やコストに注意。
- calc_forward_returns の horizons は 1〜252 営業日の範囲であることを前提とし、不正値は ValueError を送出。

署名
- この CHANGELOG は現行コードベースの実装内容から推測して作成しました。実際のコミット履歴や過去リリースノートが存在する場合は、差分を反映するように更新してください。