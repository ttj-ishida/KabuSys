# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
形式は "Keep a Changelog" に準拠します。

現在のリリース履歴
- [0.1.0] - 2026-04-18

## [0.1.0] - 2026-04-18

### Added
- 実行・監視系の起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。プロセス優先度設定、SQLite / DuckDB 接続、Broker クライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッド起動と停止フラグ検知を実装。KABUSYS_ENV=paper_trading の場合は専用の paper DB を使用（data/paper_trading.db をデフォルト）し、MockBroker を想定した分離をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルを検知して安全に終了する動作を実装。Monitoring は環境にかかわらず本番 sqlite_path を使用する旨の挙動を明示。

- 設定管理・補助ツールを追加
  - config.py: 環境変数 / .env 自動ロード機能（.env / .env.local）を追加。プロジェクトルート検出（.git または pyproject.toml 基準）を実装。.env パースは export プレフィックス・クォート・エスケープ・インラインコメント等に対応。Settings クラスで各種設定値（DB パス、PID / kill flag パス、しきい値、env/log_level 等）の取得とバリデーションを提供。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。シークレット項目のマスク表示、既存値の再利用、保存確認を実装。
  - validate_config.py: 起動前に .env と config/*.yaml の簡易検証を行う CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML がインストールされている場合の）パース検証、本番環境向けの追加警告などを実装。--strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築・リスク調整・ポジション割付の純粋関数群を追加（DB 参照なし、メモリ内計算）
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合のフォールバックを実装。
  - portfolio/risk_adjustment.py: セクター集中制限を行う apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装。未知レジームのフォールバックやログ出力を含む。
  - portfolio/position_sizing.py: 発注株数算出ロジックを実装（risk_based / equal / score の各方式に対応）。単元株丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケールダウン）、cost_buffer を考慮した保守的見積り、残余キャッシュでの端数配分アルゴリズムを実装。

- ユーティリティ群を追加
  - utils/logging_setup.py: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティを追加。ログディレクトリ作成失敗時やファイルハンドラ作成失敗時にフォールバックする堅牢な実装。ログレベル・ログディレクトリの解決ルールを提供。
  - utils/process_priority.py: Windows / POSIX（Linux / macOS 等）に対応したプロセス優先度設定と CPU affinity 設定ユーティリティを追加。権限不足などで設定できない場合は警告を出し安全にスキップする。

- Paper Trading の検証ツールを追加
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から集計を行い、稼働率（uptime）、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出してレポート表示するスクリプトを追加。P95 計算、期間フィルタ、表形式の出力、閾値による PASS/FAIL 判定を実装。

- リサーチ用のファクター計算モジュールを追加（開発中）
  - research/factor_research.py: モメンタム等のファクター計算の設計と一部実装を追加（DuckDB 接続受け取り、prices_daily / raw_financials を参照）。（ファイル末尾が途中であるため、モジュールは部分実装）

- パッケージメタ情報
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- 起動・監視ロジックの堅牢化
  - run_monitoring.py/run_execution.py と utils/* の連携により、起動時にログ設定・プロセス優先度設定を行い、安全な DB 接続・クリーンな終了処理（接続クローズ、スレッド join、停止フラグ検知）を行うように改善。
  - logging_setup は既存ハンドラを適切にフラッシュ・クローズしてから再設定するため、複数回呼び出しても二重出力にならないようにした。

- .env 自動ロードの動作
  - config.py がプロジェクトルートの検出ロジックを導入し、.env/.env.local を OS 環境変数を保護したうえで上書き順序に基づき読み込むように変更。環境変数による自動ロード無効化オプション（KABUSYS_DISABLE_AUTO_ENV_LOAD）を追加。

### Fixed
- 環境変数の取り扱い安全性向上
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出してデフォルト値にフォールバックし、警告ログを出すようにした（run_monitoring.py）。これにより time.sleep に渡す不正値でクラッシュすることを防止。
  - Settings.paper_fill_mode の妥当性チェックを追加し、無効な値の入力時に明示的に例外を送出するようにした（config.py）。

- DB 初期化の冪等性
  - init_monitoring_db を起動時に必ず呼び出すことで、monitoring 用テーブルの存在を保証（既に存在しても安全に動作）するようにした（run_execution.py/run_monitoring.py）。

- ファイル・パス取り扱いの堅牢化
  - config_setup/validate_config において、環境変数で指定されたパスの親ディレクトリが存在しない場合に警告を出すようにした（自動作成の可能性を注記）。

### Known issues / Notes
- research/factor_research.py はファイル終端が途中で切れており、モメンタム計算の実装が完了していない箇所があります（開発中）。今後のリリースで続き実装を行う予定です。
- 一部の機能（ExecutionEngine 本体、BrokerClient の具体実装、SystemMonitor 内部、init_monitoring_db 実装等）はこの差分に含まれているスクリプトから参照されているが、本 changelog の対象ファイル群のみでは全機能の動作確認はできません。実行環境では関連モジュールの実装が必要です。

### Security
- なし（このリリースでセキュリティ関連の修正・脆弱性対応は行っていません）

---

今後の予定:
- research/factor_research の完成、Strategy 実装との統合、ExecutionEngine の稼働監査・追加ユニットテスト整備を予定しています。