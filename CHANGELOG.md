# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
初回リリース（0.1.0）の内容は、コードベースから推測してまとめています。

今後のバージョンでは変更点をここに追記してください。

## [0.1.0] - 2026-04-18

### Added
- 全体
  - パッケージ初期版を追加。モジュール群は日本株自動売買システム（KabuSys）を想定した設計。
  - バージョン情報: `kabusys.__version__ = "0.1.0"`。

- 設定・環境管理
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml）。  
    - 読み込み順序: OS 環境変数 > .env.local > .env。  
    - 自動ロードを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサ実装（`kabusys.config`）:
    - `export KEY=val` 形式やシングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
    - `_load_env_file()` は既存 OS 環境変数を保護する仕組みを備える（protected set）。
  - `Settings` クラスを導入し、環境変数からアプリ設定を安全に取得（プロパティとして提供）。
    - DB パス、LINE トークン、kabu API 設定、閾値（CPU/MEM/DISK）などのプロパティを提供。
    - `KABUSYS_ENV` / `LOG_LEVEL` 等の値検証を実施（許容値チェック）。
    - Paper Trading 用設定（`is_paper`, `paper_sqlite_path`, `paper_fill_mode`）をサポート。`paper_fill_mode` の有効値検査あり。

- 設定支援ツール
  - 対話式設定ウィザード CLI (`kabusys.config_setup`) を追加。
    - `.env` の初期作成・更新を対話的に行う。
    - シークレット項目のマスク表示やデフォルト値の採用、保存確認付き。
  - 設定検証 CLI (`kabusys.validate_config`) を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パス親ディレクトリ存在確認、config/*.yaml の存在・パースチェック（PyYAML がインストールされている場合）。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 本番（live）用の追加ガード（LINE 通知設定や Kill Switch 設定の確認）。

- 実行用スクリプト
  - 実行エンジン起動スクリプト (`kabusys.run_execution`) を追加。
    - 起動時にプロセス優先度を設定（`set_process_priority("high")`）。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite を使用して本番 DB と分離（`paper_sqlite_path`）。
    - ブローカークライアントのファクトリ経由生成（`BrokerClientFactory`）、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、`ExecutionEngine` の起動／停止制御（停止フラグおよび PID ファイルの管理）。
    - デーモンスレッドで engine を実行し、停止フラグ検知で安全に停止処理を実施。
  - 監視ポーリング起動スクリプト (`kabusys.run_monitoring`) を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の sqlite_path を使用し、監視用テーブルの初期化を行う（`init_monitoring_db`）。
    - 停止フラグ検知、例外ハンドリング（次ポーリングまで継続）を実装。
    - DuckDB への接続（分析用）を確立。

- 監視関連
  - 監視テーブルの初期化関数 `init_monitoring_db` を利用（起動スクリプトから呼び出し、冪等にテーブル保証）。

- ロギング関連
  - 統一ロギング設定ユーティリティ（`kabusys.utils.logging_setup.setup_logging`）を追加。
    - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でログを出す仕組みをルートロガーに設定。
    - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順: 引数 > 環境変数 `LOG_LEVEL` > デフォルト `"INFO"`。
    - 既存ハンドラはクリアして再設定（重複防止）。
    - デフォルト保存期間 30 日。

- プロセス優先度・CPU 固定ユーティリティ
  - `kabusys.utils.process_priority` を追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）に対応して `set_process_priority(level)` を実装（"high"/"normal"/"low"）。
    - CPU affinity 固定用 `set_cpu_affinity(cpu_count)` を追加（利用可能コア数チェック・例外ハンドリングあり）。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - シグナル選定（score 降順、同点は signal_rank でタイブレーク）`select_candidates`。
    - 等額配分 `calc_equal_weights`、スコア正規化配分 `calc_score_weights`（全スコアが 0 の場合は等額にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限を適用する `apply_sector_cap`（売却予定銘柄を除外、"unknown" セクターは制限適用外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" をサポート、未知レジームは 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - 発注株数決定ロジック `calc_position_sizes` を実装（`allocation_method` = "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、銘柄毎の上限（max_position_pct）、投下資金の aggregate cap、コストバッファ（手数料・スリッページ）を考慮したスケーリングロジックを実装。
    - risk_based の場合は risk_pct / stop_loss_pct ベースでポジションサイズを算出。
    - スケーリング後の端数処理は fractional remainder に基づく lot 単位での再配分を行い、安定した再現性を確保。

- 研究・ファクター
  - `kabusys.research.factor_research`（ファクター計算モジュール）を追加。
    - Momentum（1M/3M/6M リターン、200日移動平均乖離率）や ATR, ボラティリティ、流動性等の計算を設計（DuckDB 接続を使用、prices_daily / raw_financials を参照）。
    - 関数群の設計方針と定数が定義済み（計算ロジックは実装中／継続）。

- ツール
  - Paper Trading 検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）を追加。
    - paper_trading 用 SQLite（デフォルト: data/paper_trading.db）からデータを読み取り、稼働率・注文成功率・送信率・レイテンシなどの指標を算出してレポート出力。
    - P95 レイテンシ計算、閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づき PASS/FAIL を判定。
    - CLI 引数で期間指定（--from/--to）および DB パス指定（--db）に対応。

### Changed
- 初回リリースのため該当なし（初期導入機能の一覧）。

### Fixed
- 初回リリースのため該当なし。

### Notes / Migration
- .env の自動読み込みに依存するコードがあるため、自分の環境で明示的に .env を読み込ませたくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。
- paper_trading を使用する場合、`KABUSYS_ENV=paper_trading` とし、必要に応じて `PAPER_TRADING_SQLITE_PATH` を設定してください。本番 DB とデータが分離されます。
- 実行スクリプトはログ出力を行うため、`logs/` ディレクトリへの書き込み権限を確認してください。作成に失敗した場合はコンソールログのみになります。
- プロセス優先度や CPU affinity の設定は権限が必要な場合があります。権限不足時は警告が出てスキップされます。

もし特定のファイル・関数についてより詳しい変更ログや使用例（CLI の例、Settings の各プロパティの説明等）が必要であれば、その項目に絞って詳述します。