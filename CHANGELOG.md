# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています（https://keepachangelog.com/ja/1.0.0/）。

## [Unreleased]

## [0.1.0] - 2026-04-17

### Added
- 初回リリース: KabuSys 基本機能群を追加。
- CLI / 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用して paper_trading 専用 DB（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）に記録。
    - プロセス優先度を起動直後に High に設定する仕組みを追加（utils.process_priority.set_process_priority を呼び出し）。
    - 停止フラグ（data/stop_requested.flag）検出による安全な停止処理と実行中 PID ファイル管理。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は起動環境にかかわらず本番 sqlite_path を使用する（監視 DB と本番データの共通利用設計）。
    - プロセス優先度を High に設定してから監視を開始する。
- 設定管理
  - config.py: Settings クラスを追加し、環境変数から設定値を提供。主なプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL, LINE_*（任意）、DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH など
    - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL の検証
    - 監視閾値（CPU/MEM/DISK）および PID/kill flag 関連設定
  - 自動 .env ロード機能:
    - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env と .env.local を自動ロード（OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - config_setup.py: 対話式 .env 生成ウィザードを追加（.env の初期作成・更新を支援）。
    - J-Quants / kabuAPI / DB パス / ログレベル / Kill Switch 設定などの入力を支援。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス存在チェック、config/*.yaml の存在と YAML パース（PyYAML が利用可能な場合）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates, calc_equal_weights, calc_score_weights を追加（スコア正規化・同点タイブレーク挙動を実装）。
  - portfolio/position_sizing.py:
    - calc_position_sizes を追加。allocation_method（risk_based / equal / score）に対応し、lot 単位丸め、aggregate cap（available_cash に基づくスケーリング）、cost_buffer を用いた保守的見積り、単元株処理を実装。
    - 将来的な拡張点として銘柄別 lot_size の導入を TODO として注記。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap（セクター集中制限）と calc_regime_multiplier（市場レジームに基づく投下資金乗数）を追加。
    - 不明セクターは "unknown" として扱い上限を適用しない挙動を採用。
- 監視・モニタリング
  - monitoring データベース初期化（init_monitoring_db）を呼び出して監視テーブルの冪等的作成を保証（run_execution/run_monitoring から呼び出し）。
  - SystemMonitor（モジュール本体は別ファイル想定）を run_monitoring で利用。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成ツールを追加（SQLite の paper_trading DB を参照）。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）を計算して PASS/FAIL 判定を行う。
    - デフォルト閾値: 稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms。
- リサーチ
  - research/factor_research.py:
    - モメンタム / ボラティリティ / 流動性などのファクター計算関数（DuckDB 接続を受け取り SQL ベースで計算）を追加。MA200, ATR20, 複数期間リターン等を実装。
- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level) を実装し、Windows（psutil の優先度定数）と POSIX（nice 値）で差分を吸収。
    - set_cpu_affinity(cpu_count) を実装（利用可能コア数の検証、psutil による CPU affinity 設定）。
    - psutil の AccessDenied / NotImplementedError 等を捕捉して警告に留める耐障害性を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env パーサ（config._parse_env_line）を頑健に実装:
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱い、空行/コメント行の無視。
  - これにより .env の様々な記法に対する互換性が向上。
- MONITOR_POLL_INTERVAL のパース時に不正値（非整数・0 以下）を検出して警告を出し、デフォルト（60 秒）へフォールバックする処理を追加。
- run_monitoring の監視ループで stop flag 検出時に安全に終了する処理を実装。
- run_execution の起動時に停止フラグが既に立っている場合は実行をスキップして安全に終了するよう修正。

### Deprecated
- （初回リリースのため該当なし）

### Security
- 環境設定生成時の注意: .env を絶対にリポジトリへコミットしない旨を README/ウィザードに明記。

### Notes / Known limitations
- position_sizing.calc_position_sizes:
  - 現状は全銘柄共通の lot_size（デフォルト 100）を想定。将来的に銘柄別 lot_size の導入を検討中（TODO を記載）。
  - price が欠損（0.0）の場合、エクスポージャーが過少見積もられる可能性があるため、将来的にフォールバック価格（前日終値等）を導入する余地あり。
- calc_regime_multiplier:
  - 未知のレジーム値は警告を出して 1.0 でフォールバックする設計。
- utils/process_priority:
  - 一部 OS（psutil がサポートしないプラットフォーム）では優先度/affinity 設定がスキップされ、警告を出力する。
- paper_verification_report:
  - P95 は単純なパーセンタイル実装（ソート + index を採用）。大量データの際の性能や厳密な百分位数アルゴリズムの選定は今後検討項目。

---

以上が初回リリース（0.1.0）の主要な変更点・実装内容です。詳細は各モジュール内のドキュメント文字列およびコードコメントを参照してください。