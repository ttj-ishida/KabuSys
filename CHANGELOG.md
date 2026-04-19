# Changelog

すべての重要な変更を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  
（内容はリポジトリ内のコードから推測して作成しています）

## [Unreleased]
- Added
  - run_monitoring 起動スクリプトを追加。SystemMonitor をポーリング実行するためのループを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（不正値はデフォルト 60 秒にフォールバック）。
    - 停止フラグファイル（data/stop_requested.flag）を検出して安全にループを終了。
    - 監視用 DB は環境に依存せず本番 sqlite_path を使用。
  - run_execution 起動スクリプトを追加。ExecutionEngine を起動して注文実行セッションを管理。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory により本番/モックブローカーの切り替えを実現。
    - 停止フラグ・PID ファイル管理、別スレッドでのエンジン実行と安全な停止処理を実装。
  - 環境設定・検証ツールを追加
    - config_setup: 対話式ウィザードで .env の作成・更新を支援。
      - シークレット項目はマスク表示、保存前に確認プロンプトあり。
      - .env 出力テンプレートを実装（.env を Git にコミットしないよう注意文を出力）。
    - validate_config: 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスや config ファイルの存在・パース検証、production（live）向けの追加ガード等を行う。
      - --strict オプションで警告を失敗扱いにできる。
  - 環境読み込みロジックを強化（kabusys.config）
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により CWD に依存しない .env 自動ロードを実現。
    - .env のパースで export プレフィックス・クォート文字列（バックスラッシュエスケープ処理）・インラインコメントを扱えるようにした。
    - 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を追加。
  - ロギングユーティリティを追加（kabusys.utils.logging_setup）
    - stdout への StreamHandler と日次ローテーション (TimedRotatingFileHandler) を組み合わせた標準的なログ設定を提供。
    - ログディレクトリの自動作成と失敗時のフォールバック（コンソールのみ）に対応。
    - ログレベル・ログディレクトリの解決順序を明示。
  - プロセス優先度・CPU affinity ユーティリティを追加（kabusys.utils.process_priority）
    - Windows / POSIX の差分を吸収して set_process_priority, set_cpu_affinity を提供。
    - 権限不足や未対応プラットフォーム時に安全にスキップし、警告出力。
  - Portfolio 関連の純粋関数群を追加（kabusys.portfolio）
    - portfolio_builder: 候補選定（select_candidates）、等配分・スコア配分（calc_equal_weights / calc_score_weights）。
    - risk_adjustment: セクター上限の適用（apply_sector_cap）、レジームに応じた乗数計算（calc_regime_multiplier）。
    - position_sizing: 各銘柄の発注株数算出（calc_position_sizes）。
      - risk_based / equal / score の配分方式をサポート。
      - lot_size（単元）丸め、単銘柄上限・集計キャップ、コストバッファの考慮、スケーリング時の端数処理を実装。
  - Paper Trading 検証レポートツールを追加（kabusys.tools.paper_verification_report）
    - Paper Trading の SQLite DB を解析して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などの指標を出力。
    - PASS/FAIL 判定ルール（稼働率、成功率、P95 レイテンシ等の閾値）を備える。
  - research/factor_research（ファクター計算）の下地を追加（DuckDB 接続でのファクター計算を想定）。
    - モメンタム / MA / ATR / 流動性等の指標計算の設計を反映（メモリ/DB を組み合わせた実装方針）。

- Changed
  - run_monitoring / run_execution 起動時にプロセス優先度を最初に "high" に設定するよう変更（set_process_priority を呼び出し）。
  - 監視・実行スクリプトで共通の監視テーブル初期化（init_monitoring_db）を行い、テーブル存在を冪等に保証。

- Fixed
  - 環境変数パースの堅牢性を向上（export プレフィックス、クォートされた値、コメント処理、未設定キーの扱い等）。
  - logging_setup: ログディレクトリ作成失敗時にファイルハンドラ作成をスキップし、コンソール出力にフォールバックするように修正。

## [0.1.0] - 2026-04-19
初回リリース（推定）。以下の主要機能を含む。
- Added
  - KabuSys パッケージ基本構成を追加。
    - __version__ = 0.1.0 を設定。
  - 基本的な設定管理（kabusys.config）を追加。
    - Settings クラスを提供し、環境変数から各種設定値を取得。
    - 環境（KABUSYS_ENV）が development / paper_trading / live のバリデーションを実装。
  - 実行系（ExecutionEngine）および監視系（SystemMonitor）を起動するためのスクリプト群を提供（run_execution, run_monitoring）。
  - ログ設定ユーティリティとプロセス優先度ユーティリティを提供。
  - Portfolio 構築・ポジションサイジング・リスク調整の関数群を実装。
  - Paper Trading 検証用のレポート生成ツールを実装。
  - 設定ウィザード（config_setup）と設定検証ツール（validate_config）を実装。
  - DuckDB / SQLite を用いたデータ保存・分析の土台を整備（デフォルトパス: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）。
  - CLI エントリポイント（python -m kabusys.*）で利用できる各種スクリプトを追加。

- Changed
  - なし（初回リリースとして集約）

- Fixed
  - なし（初回リリースとして集約）

- Security
  - config_setup にてシークレット値はマスク表示し、.env をコミットしない旨の注意を明記。

---

注記:
- 上記の変更履歴はソースコードの実装内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば、実際の git コミットログを元に正確な CHANGELOG を生成できます。