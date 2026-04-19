# CHANGELOG

すべての重要な変更は「Keep a Changelog」形式に従って記載しています。リリースはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-04-19

Added
- 実行・監視用の起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB と MockBrokerClient を使用して本番 DB と分離する。スレッドで engine.run_session をデーモン実行し、data/stop_requested.flag による安全停止、実行 PID ファイル管理に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を参照する旨の挙動を明記。
- 設定・環境管理
  - config.py: .env の自動ロード機能を実装（プロジェクトルート自動検出、.env/.env.local の読み込み順、OS 環境変数保護）。.env 行パーサを強化してクォート、エスケープ、インラインコメントを適切に処理。Settings クラスを追加して環境変数アクセスをプロパティ化（J-Quants/Kabu API/DB パス/監視閾値/フラグなど多数）。
  - config_setup.py: .env を対話式に作成・更新するウィザードを追加。既存値の読み込み・マスク表示・保存確認・ファイルテンプレート出力に対応。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加警告などを実行。--strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap と市場レジームに応じた乗数を返す calc_regime_multiplier を実装。unknown セクターの扱い、レジーム未定義時のフォールバック（1.0）を明記。
  - portfolio/position_sizing.py: 株数決定ロジックを実装（risk_based / equal / score）。単元株丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）および残差を考慮した追加配分ロジックを実装。手数料・スリッページ見積りのための cost_buffer をサポート。
- ユーティリティ
  - utils/logging_setup.py: 統一的ロギング設定ユーティリティを追加。既存ハンドラのクリア、コンソール出力を stdout に固定、日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を追加（デフォルト logs/<app_name>.log、30日保持）。LOG_DIR / LOG_LEVEL の解決順を実装し、ディレクトリ作成失敗時はファイル出力をスキップして継続。
  - utils/process_priority.py: psutil を使ったプロセス優先度設定および CPU affinity 設定ユーティリティを追加。Windows と POSIX（Linux/Mac 等）の差分を吸収し、未対応 OS や権限不足時は警告を出して安全にフォールバック。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から指標（稼働率、注文成功率、送信率、レイテンシ等）を集計して PASS/FAIL 判定するレポート生成ツールを追加。P95 計算、期間フィルタ、テーブル欠損時のフォールバックを実装。
- research/factor_research.py（ファクター計算基盤）
  - DuckDB 接続を受け取ってモメンタム等のファクターを計算するための設計・定数群と calc_momentum の骨格を追加（prices_daily / raw_financials に依存）。（注: ファイル末尾で実装が途中で切れている箇所あり）

Changed
- ログの出力先標準化: logging_setup はコンソール出力を stdout に固定（stderr ではなく）。これにより cron 等で stdout/stderr をリダイレクトする運用を想定。
- .env 読み込みロジック: .env.local を .env より優先して上書きする動作を採用。既存 OS 環境変数は保護され、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
- run_monitoring の挙動: 監視用 DB 初期化（init_monitoring_db）と duckdb 接続確立を行い、環境にかかわらず本番 sqlite_path を使用することを明示。
- run_execution の DB 選択: paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番データと分離。監視テーブルの存在を保証するため init_monitoring_db を実行。
- プロセス起動時の優先度設定を全起動スクリプトで実行（set_process_priority("high") を最初に呼ぶ）して実行安定性を向上。

Fixed
- 重複ハンドラによる二重ログ出力を防止: setup_logging が既存ハンドラをクリアするようにして、多重登録によるログ重複を回避。
- 環境変数パーサの不正処理回避: _parse_env_line がクォート内のバックスラッシュエスケープとインラインコメント処理を適切に扱うよう改善し、意図しない値切り詰めやパースエラーを減らす。
- run_monitoring の MONITOR_POLL_INTERVAL の変換と検証: 0 以下や不正な値を検知した場合にデフォルトにフォールバックして time.sleep への ValueError を回避。

Security
- .env 取り扱いの注意書き追加: config_setup が .env を生成する際に Git にコミットしない旨を明示。

Notes / Known issues
- research/factor_research.calc_momentum の実装が途中で切れている箇所が存在します（ファイルの末尾が未完）。今後のコミットで完了予定です。
- position_sizing の価格欠損（price が 0.0 または未定義）の場合、現状はログ出力してスキップする実装です。将来的には前日終値や取得原価をフォールバックする拡張を検討中。
- apply_sector_cap では "unknown" セクターに対しては上限制約を適用しない設計です。マスタ不整合時の挙動として意図的な扱いになっています。

開発者向けヒント
- 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利です）。
- run_execution / run_monitoring はそれぞれ独立したログファイル（logs/execution.log, logs/monitoring.log）を出力します。LOG_DIR を環境変数で指定可能です。
- Paper Trading の検証レポートは --db オプションで任意の SQLite ファイルを指定できます。

--- 

（初回リリース: 0.1.0）