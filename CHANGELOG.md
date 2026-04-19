# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースから推測した初期リリースの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-04-19

### Added
- 初期リリース: KabuSys 日本株自動売買システムの基礎機能群を追加。
  - 実行エントリ／ランナー
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。プロセス優先度を "high" に設定し、PID ファイル／停止フラグで制御。
      - KABUSYS_ENV による paper_trading モードをサポート。ペーパートレード時は専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用し MockBrokerClient を想定。
      - DuckDB を分析用に接続。
    - run_monitoring.py
      - SystemMonitor ポーリングループを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視系は環境に関わらず本番 sqlite_path を使用する設計。
  - 設定・環境管理
    - config.py
      - .env 自動読み込み機構（プロジェクトルート検出: .git / pyproject.toml 基準）を実装。
      - .env 行パーサーを実装（export プレフィックス対応、シングル/ダブルクォート・エスケープ対応、インラインコメント処理）。
      - Settings クラスを実装し、環境変数のアクセス・バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）とデフォルト値を提供。
    - config_setup.py
      - 対話式ウィザードで .env を初期作成/更新する CLI を追加（秘密入力のマスク表示、既存 .env の読み込み、テンプレート書き出し）。
    - validate_config.py
      - 起動前チェック CLI を追加。必須環境変数の存在、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML がない場合は警告してスキップ）。--strict オプションで警告も失敗扱いに可能。
  - ロギング／運用ユーティリティ
    - utils/logging_setup.py
      - 統一ログ設定ユーティリティを追加。コンソール出力は stdout（StreamHandler）、日次ローテーションのファイル出力（TimedRotatingFileHandler）を追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - utils/process_priority.py
      - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定関数 set_process_priority を追加。CPU affinity 設定関数 set_cpu_affinity も実装。権限不足などは警告して安全にスキップ。
  - ポートフォリオ構築（純粋関数）
    - portfolio/portfolio_builder.py
      - 候補選定 select_candidates、等分配 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等分配にフォールバック）を追加。
    - portfolio/risk_adjustment.py
      - セクター集中制限を適用する apply_sector_cap を実装（unknown セクターは制限適用除外）。
      - 市場レジームに応じた投資乗数 calc_regime_multiplier を実装（'bull'/'neutral'/'bear' マップ。未知レジームは警告して 1.0 フォールバック）。
    - portfolio/position_sizing.py
      - 各種配分方式（risk_based / equal / score）に応じた株数決定 calc_position_sizes を実装。
      - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金に応じたスケールダウン）、cost_buffer を用いた保守的コスト見積り、余剰配分の再割当アルゴリズムを実装。
  - モニタリング周辺
    - monitoring_db 初期化呼び出しが run_execution/run_monitoring に組み込まれ、監視テーブル存在を保障（冪等）。
  - 開発者向けツール
    - tools/paper_verification_report.py
      - ペーパートレードの検証レポート生成スクリプトを追加。稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を算出し、所定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）で PASS/FAIL を判定。
  - リサーチ（未完）
    - research/factor_research.py にモメンタム等のファクター計算モジュールの骨子を追加（DuckDB を使用する設計、各種窓サイズ定義）。一部実装が途中で存在。

### Changed
- なし（初期リリースとして新規追加が中心）。

### Fixed
- .env の自動読み込みで OS 環境変数を上書きしないよう保護する仕組みを導入（config._load_env_file の protected 実装）。
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合、System 単位でフォールバックして動作を続行するよう堅牢化（ログの二重設定防止とハンドラ再初期化）。
- 環境変数のパースにおいてクォート内のエスケープやインラインコメントを正しく扱うよう実装（config._parse_env_line）。

### Security
- .env のテンプレート生成時に注意喚起を明記（config_setup.py: .env を絶対に Git にコミットしない旨）。

### Notes
- 多くのデフォルトパスは data/ フォルダ配下に置かれる（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）。環境変数で上書き可能。
- run_monitoring は監視用 sqlite を環境にかかわらず本番 sqlite_path を参照する設計であるため、起動前に設定を確認してください。
- Settings クラスは property ベースで即時に環境変数の妥当性チェックを行うため、起動時に未設定の必須変数があると例外を送出します。validate_config を使用して事前検証することを推奨します。

---

（この CHANGELOG はコードベースからの推測に基づいて作成しています。実際のコミット履歴や変更意図と差異がある場合があります。）