# Changelog

すべての変更は Keep a Changelog の形式に従って記載します。  
このファイルは、リポジトリ内のソースコード（src/ 以下）から推測して生成した変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- 現在未リリースの変更はありません。

## [0.1.0] - 2026-04-18

### Added
- 初期リリースとして主要機能を実装。
  - 実行・監視用エントリポイント
    - Execution エンジン起動スクリプトを追加（run_execution.py）。
      - KABUSYS_ENV による paper_trading モード判定を実装。paper_trading 時は専用 SQLite（data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と完全に分離（src/kabusys/run_execution.py）。
      - エンジンをデーモンスレッドで起動し、data/stop_requested.flag による停止制御を実装。PID ファイルの扱いをサポート。
    - 監視ポーリングループ起動スクリプトを追加（run_monitoring.py）。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。無効値時はデフォルト 60 秒へフォールバック。
      - 監視は環境にかかわらず本番用 sqlite_path を使用して初期化（init_monitoring_db 呼び出し）（src/kabusys/run_monitoring.py）。
  - 設定管理
    - Settings クラスを導入し、環境変数・.env の読み込みと各種設定値の取得・検証を一元化（src/kabusys/config.py）。以下を含む：
      - .env 自動ロード（プロジェクトルートの検出: .git または pyproject.toml 基準。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
      - .env パースの強化：export 形式、クォート文字列、インラインコメントの扱いに対応。
      - 各種設定プロパティ（DB パス、PID/kill フラグ、Paper Trading の設定、閾値、環境判定など）とバリデーション。
  - 設定ユーティリティ / CLI
    - 対話式 .env 作成・更新ウィザードを追加（config_setup.py）。既存 .env 読込、秘密値マスク、保存確認を実装。
    - 起動前設定検証 CLI を追加（validate_config.py）。必須環境変数チェック、KABUSYS_ENV 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在チェックおよび PyYAML があればパース検証を実行。--strict オプションで警告も失敗扱いに可能。
  - ロギング / プロセス管理ユーティリティ
    - 統一ログ設定ユーティリティを追加（setup_logging）。
      - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（30 日保持）を設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールログのみで継続（src/kabusys/utils/logging_setup.py）。
    - プロセス優先度・CPU affinity 設定ユーティリティを追加（process_priority.py）。
      - Windows と POSIX の差異を吸収して set_process_priority/set_cpu_affinity を提供。権限不足や未対応 OS では安全にフォールバックする実装。
  - ポートフォリオ構築関係（純粋関数群）
    - 候補選定・重み算出（portfolio_builder.py）
      - select_candidates（スコア降順、タイブレークルール）、calc_equal_weights、calc_score_weights（全スコア 0 の場合は等金額にフォールバック）。
    - セクター制約・レジーム乗数（risk_adjustment.py）
      - apply_sector_cap（既存保有からセクターごとのエクスポージャ算出、上限超過セクターの新規候補除外。unknown セクターは無視）
      - calc_regime_multiplier（bull/neutral/bear に対応、未知レジームは警告を出して 1.0 にフォールバック）
    - ポジションサイズ計算（position_sizing.py）
      - allocation_method に基づく株数計算（risk_based / equal / score）、単元（lot_size）丸め、per-position 上限、aggregate cap によるスケーリングと余り分配ロジック、コストバッファ対応。
  - 分析・レポートツール
    - Paper Trading 検証レポート生成スクリプトを追加（tools/paper_verification_report.py）。
      - system_stability / trade_logs / risk_logs などから稼働率・注文成功率・送信率・レイテンシ（P95 を含む）を集計し、閾値に基づく PASS/FAIL 判定を出力。PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB 指定可。
  - 研究用ファクター計算モジュール（雛形）
    - factor_research.py を追加。モメンタム・ボラティリティ等の計算方針と calc_momentum 等の実装方針を配置（DuckDB 経由で prices_daily/raw_financials を参照する設計）。（実装はモジュール内で進行中の部分あり）

### Changed
- プロセス起動時の初期設定の強化。
  - 起動スクリプトが最初にプロセス優先度を高く設定するように統一（run_execution, run_monitoring）。
  - 監視起動時に例外発生しても loop を継続するように例外ログを残して次回ポーリングへフォールバック（run_monitoring.py）。

### Fixed
- 設定読み込み・解析の堅牢化。
  - .env 行パースでのクォート・エスケープ、インラインコメントの扱いを適切に処理（config.py）。
  - MONITOR_POLL_INTERVAL の不正値を検出してデフォルトにフォールバックする処理を追加（run_monitoring.py）。
  - validate_config: PyYAML 未インストール時に YAML 検証をスキップして警告するように変更（validate_config.py）。
- ロギング設定でログディレクトリ作成失敗時もアプリケーションが継続できるように調整（logging_setup.py）。

### Documentation
- 各モジュールに docstring と使用方法を追加・整備（各ファイル）。CLI の使い方や挙動（.env の扱い、paper_trading の DB 分離、停止フラグ）を明記。

### Other
- パッケージメタ情報として __version__ を 0.1.0 に設定（src/kabusys/__init__.py）。

---

注記:
- 上記はソースコードから機能・振る舞いを推測して作成した CHANGELOG です。実際の変更履歴やリリース日時はリポジトリのコミット履歴・リリースノートと照合してください。