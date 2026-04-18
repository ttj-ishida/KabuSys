# Changelog

すべての重要な変更をこのファイルに記録します。
このファイルは「Keep a Changelog」形式に準拠しています。

現在の日付: 2026-04-18

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
  - バージョン定義: src/kabusys/__init__.py にて `__version__ = "0.1.0"` を設定。
- 実行・監視エントリポイントを追加
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を想定した分離を実施。
    - プロセス優先度を高優先（"high"）に設定するユーティリティ呼び出しを実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を使用した起動・停止制御。
    - スレッドベースで ExecutionEngine を実行し、停止フラグ検知時に安全に停止を試みる。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用（設計上の明示的な仕様）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
- 設定管理と初期化ツールを追加
  - config.py
    - .env の自動ロード（プロジェクトルート検出に基づく）、環境変数のラッパー Settings クラスを提供。
    - 各種既定値（DUCKDB_PATH, SQLITE_PATH など）と妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装。
    - .env の自動読み込みを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env パースの堅牢化（export プレフィックス、クォート／エスケープ処理、インラインコメントの扱いなど）。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI。
    - デフォルト値の提示、シークレットマスク表示、保存確認などの UX を提供。
  - validate_config.py
    - 起動前に環境変数・config/*.yaml を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在確認、YAML ファイルの存在/パース確認（PyYAML があればパース検証を実施）等を実装。
    - `--strict` オプションで警告をエラー扱いにできる。
- ポートフォリオ構築（純関数群）を追加（kabusys.portfolio）
  - portfolio_builder.py
    - 候補選定（select_candidates）、等ウェイト（calc_equal_weights）、スコア加重（calc_score_weights）。
  - risk_adjustment.py
    - セクター集中の制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。未定義レジームでのフォールバックと警告ログを実装。
  - position_sizing.py
    - 銘柄ごとの発注株数計算（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウンと端数処理。
    - lot_size（デフォルト 100）や cost_buffer によるコスト保守見積りに対応。
- ユーティリティ
  - utils/logging_setup.py
    - 標準化されたロギング設定関数 `setup_logging()` を実装。
    - stdout 出力の StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度を設定する関数 `set_process_priority()` を実装。
    - CPU affinity を設定する `set_cpu_affinity()` を提供（アクセス権限エラー等は警告で無視）。
- 監視・DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を起動時に呼び出して監視テーブルの存在を保証（冪等）。
  - SystemMonitor の呼び出しポイントを用意（run_monitoring）。
- 分析用ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を計算して評価（閾値による PASS/FAIL）。
    - P95 計算、日付フィルタ、DB パス解決（引数・環境変数・デフォルト）を実装。
- リサーチ（研究）用モジュール（初期実装）
  - research/factor_research.py
    - ファクター計算の骨格（モメンタムや MA200、ATR、ボリューム関連の定義と設計方針）を追加（部分実装、関数群の骨子あり）。

### Changed
- （初回リリースのため該当なし）

### Fixed / Hardened
- .env パースの堅牢性向上
  - export プレフィックス、クォート文字列内のバックスラッシュエスケープ、インラインコメント処理など、一般的な .env 表記に対応。
  - OS 環境変数を保護するため .env ロード時の上書き保護を実装（.env.local は上書き可能だが OS 環境変数は保護）。
- ロギング初期化の安全化
  - 既存ハンドラ削除時に flush/close を試みる。
  - ログディレクトリ作成やファイルハンドラ生成に失敗した場合、コンソール出力のみで問題なく継続。
  - stdout を StreamHandler に使うことで cron 等からのリダイレクトに対応。
- 実行・監視ループの安定化
  - run_monitoring: check_once() で例外が発生してもループを継続し、例外内容はロギングして次回ポーリングまで待機。
  - run_monitoring: MONITOR_POLL_INTERVAL の不正値に対して警告ログを出しデフォルトへフォールバック。
  - run_execution: 起動時に停止フラグが立っている場合は起動せず終了、実行中に停止フラグを検知したらエンジンに stop を呼び出して安全停止を試みる。thread.join 時のタイムアウト保護。
- DB 初期化は冪等化（init_monitoring_db 呼び出しによる安全な初期化）。

### Removed
- （初回リリースのため該当なし）

### Security
- 本リリースでは機密情報（API トークン・パスワード）を .env に保存する設計のため、.env を絶対にリポジトリにコミットしない旨を config_setup のヘッダに明示。

### Notes / Known limitations
- research/factor_research.py はモメンタム等の計算設計を含むが、ファイル末尾で未完の実装（truncated）箇所が見られます。追加実装・テストが必要です。
- position_sizing 内に「価格欠損時のフォールバック」といった TODO コメントあり（前日終値や取得原価のフォールバックは未実装）。
- process_priority や set_cpu_affinity は権限や OS により動作しない場合があり、その場合は警告を出してスキップします。
- Paper Trading と Live の DB は明確に分離する設計（paper_trading 用 DB を使用）ですが、運用前に validate_config と config_setup で設定を確認してください。

---

今後のリリースでは以下を想定しています（例）:
- research モジュールの完実装とテスト追加
- ExecutionEngine / Broker クライアント周りの詳細実装と E2E テスト
- モニタリング・アラート（LINE送信等）の実装拡充
- 単体テストと CI 設定の導入

（以上）