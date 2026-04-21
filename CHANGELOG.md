# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
日付はコードベースから推測できる最新リリース日として 2026-04-21 を使用しています。

## [0.1.0] - 2026-04-21

### Added（追加）
- 基本パッケージ初期実装を追加
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。
- 実行用スクリプト
  - Execution エンジン起動スクリプトを追加（src/kabusys/run_execution.py）
    - プロセス優先度を High に設定して起動。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 実行中は PID ファイルを管理し、data/stop_requested.flag による停止を監視。
  - Monitoring ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイルでループを終了し、例外はログに記録して次のポーリングへフォールバック。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用する設計。
- 設定管理・ユーティリティ
  - 環境変数 / .env 自動読み込み・パース機能を追加（src/kabusys/config.py）
    - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を自動ロード（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメント等を考慮した .env パース実装。
    - 各種設定プロパティ（DB パス、KABUSYS_ENV、LOG_LEVEL、paper_trading 関連など）を提供。
  - 対話式設定ウィザードを追加（src/kabusys/config_setup.py）
    - .env の初期作成・更新を支援する CLI。デフォルト値・選択肢・シークレット表示をサポート。
  - 設定検証ツールを追加（src/kabusys/validate_config.py）
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスや config/*.yaml の存在チェック、`--strict` オプションで警告を FAIL 扱いに。
- ポートフォリオ構築ロジック（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates、calc_equal_weights、calc_score_weights を実装。スコアが全て 0 の場合は等重でフォールバック。
  - セクター制約・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（セクター集中を除外）、calc_regime_multiplier（bull/neutral/bear に応じた乗数）。
  - 株数決定・丸め・制限（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）での丸め、1銘柄上限・投下資金上限、コストバッファ、合計投資が利用可能現金を超えた場合のスケーリング（端数再配分ロジック）を実装。
  - portfolio パッケージのエクスポートを追加（src/kabusys/portfolio/__init__.py）
- ロギング・プロセス管理ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）
    - コンソール出力（stdout）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の優先解決、ログディレクトリ作成の失敗をハンドリング。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）
    - Windows / POSIX を吸収して nice / priority を設定。psutil の権限不足等は警告ログでフォールバック。
- Paper Trading 検証ツール
  - 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading 用 SQLite を読み、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを集計し、閾値に基づいて PASS/FAIL 判定を行う。コマンドライン引数で期間・DB パス指定可能。
- research 基盤
  - ファクター計算モジュールの骨組みを追加（src/kabusys/research/factor_research.py）
    - Momentum / Value / Volatility / Liquidity の設計方針と定数を定義。DuckDB を使った prices_daily / raw_financials 参照での計算を想定。モメンタム計算関数の雛形あり（計算範囲やウィンドウ定義を含む）。
- DB 初期化用ヘルパー呼び出し
  - 監視テーブルの初期化呼び出しを起動スクリプトから実行（init_monitoring_db を使用）。起動時に監視テーブル存在を保証（冪等）。

### Changed（変更）
- ログの標準出力を stderr から stdout に変更（src/kabusys/utils/logging_setup.py）
  - cron / Task Scheduler 等で stdout/stderr を一本化してリダイレクトする運用を想定した変更。
- .env 読み込みの優先度を明確化（src/kabusys/config.py）
  - OS 環境変数 > .env.local > .env の順で読み込み。OS 環境変数は protected として上書き防止。

### Fixed（修正・改善）
- .env パーサを強化（src/kabusys/config.py）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、空行・コメント行のスキップ等を実装し、より堅牢な読み込みを実現。
- process_priority / set_cpu_affinity のフォールトトレランス
  - psutil の AccessDenied などで失敗しても起動を継続し、警告ログを出力するように改善（src/kabusys/utils/process_priority.py）。
- Execution 起動時の DB 分離
  - paper_trading 環境では paper_sqlite_path を優先して使用することで、本番 DB と完全に分離するように修正（src/kabusys/run_execution.py）。
- Monitoring のポーリング挙動の堅牢化
  - check_once() 単位で例外を捕捉してログを出力し、ループを継続するようにして単発エラーでプロセス全体が停止するのを防止（src/kabusys/run_monitoring.py）。

### Deprecated（非推奨）
- なし（初期リリース）

### Removed（削除）
- なし（初期リリース）

### Security（セキュリティ関連）
- .env ファイル取り扱いについて注意を明記（src/kabusys/config_setup.py）
  - .env を絶対にリポジトリにコミットしない旨のヘッダを自動生成するようにした。
- 実行環境に応じて paper_trading を完全分離することで本番 API / 資金への誤発注リスクを低減（src/kabusys/run_execution.py）。

### Notes（備考 / 既知の制約）
- research モジュール（factor_research）は設計と定数類、モメンタム処理の雛形を含みますが、計算関数の実装が途中で終わっている箇所が見受けられます。実運用での使用前に追加実装・テストが必要です。
- 設定値検証ツール（validate_config）は PyYAML 未導入時に YAML 検証をスキップします。その場合は警告が出力されます。
- PAPER_FILL_MODE など paper_trading 固有設定は、環境変数で厳密に検証（有効値チェック）されます。無効な値だと起動時に例外が発生します（src/kabusys/config.py）。

---

将来的なリリースでは、research のファクター実装完了、追加のユニットテスト、さらに運用向けの監視・アラート（LINE 通知等）の実装を推奨します。必要であれば、各ファイルや機能ごとにより詳細な変更履歴（コミット単位推定）を作成します。