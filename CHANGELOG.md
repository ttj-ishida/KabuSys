KEEP A CHANGELOG 準拠の CHANGELOG.md（推測・日本語）

注: 以下は提示されたソースコードの内容から推測して作成した変更履歴です。実際のコミット履歴ではなく、機能追加・設計上の注記をまとめたものです。

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and Semantic Versioning.

Unreleased
----------
Added
- research.calc_momentum の実装を着手（モメンタム系ファクター計算の骨格を追加、未完の箇所あり: 実装継続中）。
- いくつかの TODO / 将来拡張ポイントをソースに注記（例: position_sizing の銘柄別 lot_size 拡張、price フォールバック等）。

Changed
- 内部設計/実装の微調整（ログ出力先やエラーハンドリングを強化するための調整） — 詳細はコード内コメント参照。

Fixed
- 一部のエラーハンドリングを改善（DB 操作やファイル操作時の例外を安全に処理するように改善）。

[0.1.0] - 2026-04-25
--------------------
Added
- 初期リリース: KabuSys v0.1.0 を公開。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、DB接続、BrokerClientFactory によるブローカークライアント生成、ExecutionEngine のスレッド実行・停止フラグ処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイル検知でループ終了。monitoring は環境にかかわらず本番 sqlite_path を使用する旨を明示。
- 設定管理
  - config.py: .env 自動読み込み機能（.env / .env.local、OS 環境変数保護付き）、.env 行パーサ（export プレフィックス・クォート・インラインコメント考慮）、Settings クラスによる環境変数アクセスラッパーを追加。多くの設定プロパティ（DB パス、Paper Trading 用設定、監視閾値、KABUSYS_ENV 検証など）を提供。
  - config_setup.py: 対話式 .env ウィザードを追加（既存 .env 読み込み、シークレットマスク、保存ファイルテンプレート生成）。
  - validate_config.py: 設定検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスや config/*.yaml の存在・パースチェック、--strict モード）。
- ロギング・ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。ログディレクトリの解決ロジックと失敗時のフォールバックを実装。
  - logging は stdout を使う設計（cron/スケジューラ向けの扱いに配慮）。
- プロセス制御ユーティリティ
  - utils/process_priority.py: プロセス優先度設定（Windows / POSIX を吸収）、CPU affinity 設定関数を追加。無効 OS やアクセス権のない環境では安全にスキップ。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定および重み計算（等配分・スコア加重）を追加。スコア全0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py: セクターキャップ適用（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を追加。未知レジームはフォールバックして警告を出す。
  - portfolio/position_sizing.py: 発注株数算出ロジックを実装（allocation_method: risk_based / equal / score に対応）。単元株丸め、per-stock 上限、aggregate cap（利用可能現金に対するスケーリング）、手数料・スリッページのバッファを考慮。銘柄価格欠損時のスキップやログ出力あり。
  - portfolio/__init__.py で主要関数を公開。
- ツール群
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出し PASS/FAIL 判定を行う。閾値（稼働率 99% 等）を定義。
- monitoring/ および execution/ 関連の基盤（init_monitoring_db 呼び出しなど）
  - 各起動スクリプトで監視テーブルの作成を保証（init_monitoring_db を起動時に呼ぶことで冪等にテーブル存在を確保）。
- パッケージ情報
  - __init__.py にてバージョン __version__ = "0.1.0" を設定。

Changed
- ログ出力先を stdout に明確化（logging_setup）。ログディレクトリ作成失敗時はファイル出力を無効化しても起動継続する設計に変更。
- .env 自動読み込みの動作
  - OS 環境変数が優先され、.env.local は .env の上書きに使用される。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
- Execution / Monitoring 起動フローの明確化
  - 起動直後にプロセス優先度を high に設定する処理を追加（set_process_priority の呼び出し）。
  - run_execution は KABUSYS_ENV=paper_trading の場合に paper_trading 用 SQLite を使用するよう分離（本番 DB と完全分離）。

Fixed
- 各種ファイル/ディレクトリ操作での例外に対する安全なフォールバック（ログ出力・警告表示）を実装。例えばログディレクトリ作成失敗時のハンドリング、.env 読み込み失敗時の警告など。
- settings の一部プロパティに入力検証を追加（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL の妥当性チェック）。

Security
- .env を生成するウィザードでは秘密トークン（JQUANTS_REFRESH_TOKEN 等）を明示的にマスクして表示。README 等で .env を Git にコミットしない旨を注記。

Notes / Limitations
- research.calc_momentum は実装途中で、ソースに "start_da" のような未完のシンボルが存在（実装継続が必要）。
- position_sizing の銘柄別 lot_size 対応や price のフォールバックロジックは TODO。現状は単元株数がグローバルで固定（デフォルト 100）になっている。
- Paper Trading 環境では MockBrokerClient を使う設計が示唆されている（BrokerClientFactory 経由）。実稼働 API 連携は実装/設定に依存。

以降のリリースでの予定（推測）
- research モジュールの完成（ファクター計算の完成、Z スコア正規化の連携）
- 銘柄マスタによる個別 lot_size / 手数料設定対応
- テストカバレッジ拡充と CI 設定、ドキュメント整備

--- End of CHANGELOG ---