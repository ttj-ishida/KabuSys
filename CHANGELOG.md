CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
リリース日はコードベースから推測して設定しています。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-25
--------------------

Added
- 起動スクリプトを追加／実装
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して paper_trading 用 DB（data/paper_trading.db）と分離して実行する。PID 管理、停止フラグ（data/stop_requested.flag）検知による安全なシャットダウンをサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番用 sqlite_path を使用する挙動を明示。
- 設定管理・ウィザード・検証
  - config.py: 環境変数／.env ファイル読み込みロジックを実装。プロジェクトルート自動検出（.git / pyproject.toml）、.env/.env.local の優先読み込み、複雑なクォートやエスケープを考慮した .env パーサーを提供。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。Settings クラスで各種設定プロパティを一元管理（DB パス、API トークン、環境判定、閾値等）。
  - config_setup.py: .env 作成・更新の対話式ウィザードを実装。既存値の再利用、シークレットマスク、保存プレビュー機能を提供。
  - validate_config.py: 起動前検証 CLI。必須環境変数や KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース（PyYAML が利用可能な場合）を検査。--strict オプションで警告を FAIL 扱いにできる。本番環境向けのガード（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の注意喚起）も実装。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定（スコア降順）・等金額配分・スコア加重配分を実装。スコアが全て 0 の場合は等金額配分にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（売却予定銘柄の除外や unknown セクター扱いの方針）と市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームはフォールバックで 1.0。
  - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく株数算出、単元株（lot）丸め、1銘柄上限・aggregate cap（利用可能現金に応じたスケーリング）、cost_buffer を考慮した保守的な見積り、残余キャッシュの再配分ロジックを実装。
  - portfolio/__init__.py: 上記機能をエクスポート。
- ユーティリティ
  - utils/logging_setup.py: ルートロガー向けの共通ログ設定を実装。stdout へ StreamHandler、日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py: psutil を利用したプロセス優先度設定と CPU affinity（最初の N コアに固定）を実装。Windows / POSIX（Linux/macOS/FreeBSD）差分を吸収し、権限不足等は警告でスキップ。
- ツール・レポート
  - tools/paper_verification_report.py: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からレポートを生成する CLI を追加。稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL 判定を出力。日付フィルタ、P95 計算、DB 存在チェックを実装。
- データリサーチ基盤（部分実装）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨子を実装（モメンタム、MA200、ATR、出来高指標等の設計と定数）。（ファイルは途中まで実装ファンクション群を含む）

Changed
- ログやプロセス周りの挙動を統一
  - すべての起動スクリプト系で setup_logging() を呼び出して統一的なログ出力を行うようにした。
  - 起動直後に set_process_priority("high") を呼び出して重要プロセスの優先度を上げる設計とした（権限がない場合は警告でスキップ）。

Fixed
- 環境変数パースの堅牢化
  - .env の値に対するクォート・バックスラッシュエスケープ・インラインコメント処理を実装し、従来の単純パースで起きうる誤読を防止。
- MONITOR_POLL_INTERVAL の安全な取り扱い
  - run_monitoring で環境変数 MONITOR_POLL_INTERVAL を int に変換し、1 未満の値や不正値はデフォルト（60 秒）にフォールバックして警告を出すようにした（time.sleep での例外発生を防止）。
- DB 初期化の冪等性確保
  - init_monitoring_db(sqlite_conn) を呼んで監視用テーブルの存在を保証し、実行時のテーブル未作成エラーを回避するようにした（Execution 側でも実行）。
- ログ出力先ディレクトリ作成失敗時のフォールバック
  - ログディレクトリ作成に失敗しても stdout ログは継続するように変更（ファイルハンドラは作成失敗時に無効化）。

Security
- 機密情報の扱い
  - config_setup の対話ではシークレット項目をマスク表示し、.env を生成する際に "絶対に Git にコミットしないこと" を注記。

Notes
- 監視（run_monitoring）は「監視用 sqlite」を常に本番 sqlite_path でアクセスする設計になっているため、環境変数の環境切り替えに注意してください（意図的な設計）。
- Execution は paper_trading 環境時に専用の paper_sqlite_path を使用して本番 DB と完全に分離する設計。
- .env 自動ロードはデフォルトで有効。テストや特殊用途で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- config.validate() により起動前に設定ミスやファイル欠落を検出できるため、特に KABUSYS_ENV=live の場合は validate_config を推奨します。

未解決 / TODO
- research/factor_research.py はファクター計算の主要関数の実装が継続中。完全なテストと最適化が必要。
- position_sizing の lot_size を銘柄別に扱えるようにする拡張（stocks マスタとの連携）を検討中。
- price 欠損時のフォールバック（前日終値や取得原価）を用いたエクスポージャー算出の改善。

----------
（以上）