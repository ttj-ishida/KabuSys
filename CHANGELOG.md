# CHANGELOG

すべての重要な変更はこのファイルに記録します。形式は「Keep a Changelog」に準拠します。  
バージョニングは SemVer を想定します。

## [Unreleased]

（今後の変更を記録してください）

---

## [0.1.0] - 2026-04-24

初回公開リリース。コードベースから推測される主な機能追加・修正点をまとめています。

### 追加 (Added)
- 基本アーキテクチャ
  - KabuSys 自動売買システムの初期実装を追加。
  - パッケージメタ情報: __version__ = "0.1.0"。

- 起動スクリプト
  - run_execution.py: 実行エンジン（ExecutionEngine）起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、本番 DB と分離して `data/paper_trading.db` に記録する仕組みをサポート。
    - 実行中の PID 管理（data/execution.pid）および停止フラグ（data/stop_requested.flag）を考慮した起動／停止処理。
    - ExecutionEngine を別スレッドで起動し、停止フラグ検知で安全に停止。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は実行環境にかかわらず本番 sqlite_path を使用（監視は本番 DB を参照）。

- 設定管理
  - config.py:
    - .env ファイル（.env / .env.local）の自動読み込み機能（CWD に依存せずプロジェクトルートを探索）。
    - 複雑な .env 行のパース実装（export プレフィックス、クォート中のエスケープ、インラインコメント処理など）。
    - Settings クラスによる環境変数アクセスラッパー（多くの設定をプロパティとして提供）。
    - Paper Trading 用パス、閾値、ログ設定等のプロパティ実装。
  - config_setup.py: 対話式ウィザードで .env を初期作成／更新する CLI を追加。
    - シークレット値は表示マスク。既存 .env の読み込み・再利用をサポート。
  - validate_config.py: 起動前に環境変数・config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML 有無に応じた挙動）、本番環境向けの追加ガードを実装。
    - --strict モードで警告も失敗扱いに可能。

- ポートフォリオ構築（pure functions）
  - portfolio/portfolio_builder.py:
    - 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - portfolio/risk_adjustment.py:
    - セクター集中制限 apply_sector_cap、レジームに応じた投下資金乗数 calc_regime_multiplier を実装（レジームに対する安全弁を提供）。
  - portfolio/position_sizing.py:
    - position sizing（リスクベース／equal／score ベース）を実装。単元株（lot_size）丸め、per-stock / aggregate cap、cost_buffer を考慮したスケーリングを含む。
  - portfolio/__init__.py で上記機能をエクスポート。

- ユーティリティ
  - utils/logging_setup.py:
    - 共通ロギング設定ユーティリティを追加。stdout ストリーム出力 + 日次ローテーションのファイル出力（TimedRotatingFileHandler）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
    - 既存ハンドラのクリア処理を含む。
  - utils/process_priority.py:
    - Windows / POSIX の差分を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定するユーティリティを追加。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供（権限がない場合は警告を出してスキップ）。
    - psutil の例外を安全にハンドリング。

- 監視・初期化
  - monitoring.monitoring_db.init_monitoring_db を使用して監視テーブルを初期化（起動時に冪等にテーブルを確保）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading の DB を解析して検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
    - デフォルト閾値と PASS/FAIL 判定ロジックを組み込み。
    - 日付フィルタ（--from/--to）および --db オプションをサポート。

- リサーチ
  - research/factor_research.py:
    - モメンタム等ファクター計算モジュールを追加（DuckDB を用いた prices_daily / raw_financials 参照想定）。
    - モメンタム計算（mom_1m/mom_3m/mom_6m、MA200 乖離）等を設計。※ファイル末尾で関数実装が途中で切れているため継続実装が必要。

### 変更 (Changed)
- デフォルト動作・環境変数
  - .env の自動ロード順序を明確化: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - run_monitoring と run_execution で起動直後にプロセス優先度を "high" に設定するように変更（set_process_priority 呼び出しを最初に実行）。

- DB 周り
  - run_execution は paper_trading 環境の場合は paper_sqlite_path を使用し、発注系ログを本番 DB と切り分ける設計に変更。

### 修正 (Fixed)
- .env パーサーの堅牢化
  - export プレフィックス対応、クォート内エスケープ対応、インラインコメントの取り扱いなどを実装し、従来の単純実装で失敗しやすかったケースを改善。
- ロギング設定の堅牢化
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合にフォールバックしてコンソール出力のみで継続するように改善。
- validate_config の堅牢化
  - PyYAML 未インストール時に YAML 検査をスキップし、適切に警告を出すように変更。
- 監視／実行プロセスの安全停止
  - stop flag（data/stop_requested.flag）および kill flag の扱いに関する検出とログ出力を追加。起動時に停止フラグが立っている場合は Engine を起動しない。

### ドキュメント（コード内コメント）
- 各モジュールに設計方針や使用方法の docstring を充実させ、CLI の使用例や注意点（.env を Git にコミットしない等）を明記。

### 既知の問題 / 今後の作業 (Known issues / TODO)
- research/factor_research.py の実装が途中で切れている（calc_momentum の途中）。ファクター計算の追加実装・単体テストが必要。
- position_sizing の価格欠損時の挙動について注記あり（0.0 price の場合のフォールバック戦略を改善する必要）。
- 将来的な拡張案として、銘柄ごとの lot_size をマスタで管理する設計への変更を検討している（現行は全銘柄共通 lot_size）。
- 一部の機能（BrokerClientFactory, ExecutionEngine, SystemMonitor 等）の内部実装は本 changelog の対象外（別モジュールに実装）だが、テストカバレッジの整備が望まれる。

---

## 参考（設計上の重要点）
- デフォルト設定やファイルパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_DIR: logs/
- 監視ポーリング間隔のオーバーライド: MONITOR_POLL_INTERVAL（秒）
- Paper Trading 判定閾値（tools/paper_verification_report.py）:
  - 稼働率: 99.0 %
  - 注文成功率(Fill): 90.0 %
  - 送信率(Send): 95.0 %
  - P95 レイテンシ: 200 ms

---

（注）本 CHANGELOG は提供されたソースコードから推測して作成しています。実際のコミット履歴や意図した変更履歴が存在する場合は、実コミットログに基づいて調整してください。