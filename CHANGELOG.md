# Changelog

すべての重要な変更履歴をここに記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- 開発中 / 予定
  - research.calc_momentum の実装が途中で切れているため、ファクター計算モジュールの追加実装・テストが必要。
  - テストカバレッジ拡充、CI ワークフロー、ドキュメント（PortfolioConstruction.md 等）のリンク整備予定。
  - ログ回転・権限周り、DB マイグレーション戦略、運用向け監視アラート（LINE通知など）の確認・強化予定。

---

## [0.1.0] - 2026-04-11

最初の公開リリース（推測）。以下の主要機能とユーティリティを追加。

### Added
- 基本アーキテクチャ / サービス起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite を使用（data/paper_trading.db を想定）。
    - プロセス優先度設定（high）実行、停止用フラグ（data/stop_requested.flag）・PID ファイル（data/execution.pid）を扱う。
    - BrokerClientFactory を介したブローカークライアントの生成、OrderRepository・OrderManager・RiskManager・Reconciler 等の組み立て、スレッドでエンジン実行。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグ存在時にループを終了。

- 設定管理
  - config.py: 環境変数・設定読み込みモジュールを追加。
    - プロジェクトルート検出（.git または pyproject.toml）に基づく .env 自動読み込み（.env, .env.local）。
    - _parse_env_line による引用符・エスケープ・コメント対応。
    - Settings クラス経由で各種設定を取得（DB パス、API トークン、Paper Trading 設定、監視閾値、環境判定等）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - config_setup.py: 対話式 .env ウィザードを追加（.env 作成/更新を支援）。
  - validate_config.py: 起動前の設定検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV 検証、DB パス、config/*.yaml の存在確認と YAML パース検証（PyYAML 任意））。
    - --strict モードで警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を root ロガーに設定、ログディレクトリ自動作成（失敗時はファイル出力をスキップ）。
    - LOG_LEVEL / LOG_DIR / app_name をサポート。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX を透過的に扱う。set_process_priority, set_cpu_affinity を提供。
    - 権限不足時には警告を出して安全にスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコアソートと上位選出。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア全ゼロ時は等分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限による候補除外ロジック。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 各銘柄の発注株数決定（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株丸め、per-position 上限、aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer による保守的見積り等を実装。
  - portfolio/__init__.py: 上記 API をエクスポート。

- 監視・モニタリング
  - monitoring_db 初期化呼び出し（run_monitoring / run_execution で監視テーブルを冪等に初期化）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を算出。
    - PASS/FAIL 判定にしきい値を導入（稼働率 99%、成立率 90% など）。
    - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数対応。

- リサーチ・ファクター計算（骨格）
  - research/factor_research.py: ファクター計算モジュールの骨格を追加（Momentum / Value / Volatility / Liquidity 計算の設計方針と定数を定義）。
    - DuckDB 経由で prices_daily / raw_financials を参照する設計。calc_momentum の計算ロジックの実装途中（ファイル末尾が途中で切れている）。

- パッケージ初期設定
  - __init__.py にバージョン定義 __version__ = "0.1.0" を追加。

### Changed
- （初期リリースのため履歴上の変更はなし。リポジトリ内での設計選択を反映）
  - DB 分離方針: run_execution は paper_trading の場合に専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離する設計を採用。
  - 監視プロセスは環境にかかわらず本番 sqlite_path を参照する仕様注記。

### Fixed
- N/A（スナップショットからは明示的なバグ修正履歴は推測できません）。

### Known issues / Notes
- research/factor_research.calc_momentum の実装が途中で切れている（ファイル末尾が不完全）。ファクター計算の完全実装・テストが必要。
- position_sizing の TODO: 銘柄ごとの lot_size を将来的に stocks マスタから取得する拡張がコメントで示されている。
- apply_sector_cap の価格欠損（price が 0.0 の場合）に関する挙動がコメントで注意喚起されている（将来的なフォールバック価格の検討が必要）。
- 一部機能は外部モジュール（BrokerClientFactory、ExecutionEngine 等）に依存しており、それらの実装・テストが動作保証に必須。

---

（補足）  
本 CHANGELOG は提供されたコードスナップショットから推測して作成しています。実際のリリース履歴や日付・小さな修正内容はリポジトリのコミット履歴やリリースノートに基づいて更新してください。