CHANGELOG
=========

すべての注目すべき変更を記録します。
このファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 必要に応じて使用

Unreleased
----------
（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-19
-------------------

Added
- 全体
  - プロジェクト初期リリース。基本的な自動売買／検証／運用ユーティリティが含まれます。
  - パッケージバージョンを設定: kabusys.__version__ = "0.1.0"

- 設定管理
  - .env 自動読み込み機能を実装（プロジェクトルートの検出を使用）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 詳細な .env パーサを実装（export プレフィックス、クォート／エスケープ、インラインコメントの考慮）。
  - Settings クラスを追加。J-Quants / kabu API / DB /監視閾値 /実行環境等のプロパティを提供。
  - PAPER_TRADING 用設定（PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH）をサポート。

- CLI ユーティリティ
  - config_setup: 対話式ウィザードで .env を作成・更新するツールを追加。
    - 秘密値はマスク表示、保存前の確認を実装。
  - validate_config: .env および config/*.yaml の事前検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DBパスの親ディレクトリ確認、YAML パース検証（PyYAML がインストールされていない場合は警告）。
    - --strict オプションで警告もエラー扱いにできる。

- 実行／監視ランナー
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を高優先（"high"）に設定（起動直後）。
    - paper_trading モード時は MockBrokerClient（BrokerClientFactory により生成）を使用し、paper 用 SQLite DB（data/paper_trading.db）へ完全分離して記録。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による開始／停止制御を実装。
    - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の組み立て例と既定の RiskConfig を提供。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計（監視データは本番 DB を想定）。

- 監視 DB 初期化
  - init_monitoring_db を呼び出して監視テーブルの存在を保証（実行中に冪等に初期化）。

- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup: ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを追加。
    - LOG_LEVEL / LOG_DIR の解決ロジック、ログディレクトリ作成失敗時のフォールバック動作を実装。
  - utils.process_priority: cross-platform（Windows / POSIX）でプロセス優先度を設定する機能を追加。
    - set_process_priority("high" | "normal" | "low")、set_cpu_affinity(N) を提供。
    - 権限不足や未対応 OS の場合は警告してスキップ。

- ポートフォリオ構築（純粋関数）
  - portfolio.portfolio_builder: 候補選定 select_candidates、等配分 calc_equal_weights、スコア重み calc_score_weights を実装。
  - portfolio.risk_adjustment: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（市場レジームに応じた乗数）を実装。
  - portfolio.position_sizing: calc_position_sizes（各種配分方式と aggregate cap、lot サイズ丸め、コストバッファ考慮）を実装。
  - portfolio パッケージから上記機能をエクスポート。

- 解析／検証ツール
  - tools.paper_verification_report: ペーパートレード DB を解析して稼働率／注文成功率／レイテンシ等を集計・判定する CLI を追加。
    - P95 レイテンシ計算、閾値（稼働率 99%、フィルレート 90%、送信率 95%、P95 <= 200ms）に基づく PASS/FAIL 判定。
    - 日付レンジフィルタ(--from / --to)、DB パス指定(--db)をサポート。

- 研究用（骨組み）
  - research.factor_research: DuckDB 接続を受けてモメンタム等のファクターを計算するモジュールを追加（モジュール設計と一部定数・関数の骨組みを実装）。

Changed
- DB 接続ポリシー
  - 監視コンポーネントは環境にかかわらず Settings.sqlite_path（監視 DB）を利用する旨を明示。
  - 実行エンジンは Settings.is_paper 判定により paper_trading 用 SQLite（paper_sqlite_path）を使用して本番 DB と分離。

- ログ出力
  - コンソール出力は stdout を使用（stderr ではない） — cron 等で stdout/stderr を一本化して扱いやすくするため。

Fixed
- 環境変数パースの堅牢化
  - .env のクォートやバックスラッシュエスケープ、export プレフィックス、コメント処理を適切に扱うよう改善。
  - 環境変数未設定時に明示的なエラーメッセージを出すヘルパー _require を提供。

- 安全対策／運用性
  - run_execution/run_monitoring の起動時にプロセス優先度を最初に設定するようにして、起動直後から優先度が適用されるように改善。
  - 停止フラグ検知・PID 管理・DB 接続の確実なクローズ処理を実装。

Notes / Known issues
- research.factor_research の calc_momentum 等はファイル末尾で途中になっている箇所があり、ファクター計算ロジックの完全実装は今後の作業となります。
- position_sizing の price フォールバック（price が欠損した場合の扱い）は TODO コメントあり。前日終値などのフォールバック導入が推奨される。
- apply_sector_cap において "unknown" セクターは上限判定対象外となる設計のため、マスターに未登録の銘柄は意図的に除外されない点に注意。

Upgrade / Migration notes
- 新規導入ツール:
  - 初回セットアップ時は python -m kabusys.config_setup で .env を作成し、python -m kabusys.validate_config で検証することを推奨。
- 本番運用:
  - KABUSYS_ENV=live の場合は、LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値を必ず確認すること（validate_config が警告を出します）。
- .env は絶対に Git にコミットしないでください（config_setup のヘッダにも注意書きを追加）。

Acknowledgements
- このリリースには実運用を想定した監視・ログ・プロセス制御・ペーパートレード分離・ポートフォリオ構築ロジックの基盤が含まれています。今後、ファクター計算や ExecutionEngine の実装詳細（ブローカーインターフェース実装等）を拡充していく予定です。