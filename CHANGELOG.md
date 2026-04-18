# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
日付はコードベースから推測できる最新の状態（本ファイル作成日）を使用しています。

なお、本 CHANGELOG は与えられたコードの内容から機能追加・挙動を推測してまとめたもので、実際のコミット履歴ではありません。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-04-18

### Added
- 基本機能の初期実装（KabuSys v0.1.0 として公開相当）
  - 日本株自動売買システムのコアモジュール群を実装:
    - execution（ExecutionEngine 起動スクリプト run_execution.py、発注管理、OrderRepository、OrderManager、RiskManager、Reconciler 等）
    - monitoring（SystemMonitor 起動スクリプト run_monitoring.py、監視用 DB 初期化関数）
    - portfolio（銘柄選定・重み計算・リスク調整・ポジションサイジング）
    - research（ファクター計算基盤の骨格）
    - tools（Paper Trading 検証レポート生成スクリプト）
    - 設定関連（config, config_setup, validate_config）
    - ユーティリティ（logging_setup, process_priority 等）
- CLI / ユーティリティ:
  - python -m kabusys.config_setup: .env の対話的ウィザードで初期設定を作成/更新する機能を追加。
  - python -m kabusys.validate_config: 環境変数や config/*.yaml の事前チェックを行う検証 CLI を追加（--strict オプションあり）。
  - python -m kabusys.tools.paper_verification_report: Paper Trading 用の検証レポートを生成するツールを追加（期間指定 --from/--to、DB 指定 --db）。
- 環境変数・設定:
  - .env 自動読み込みの実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - 新規/既存の重要な環境変数を多数サポート:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live）
    - LOG_LEVEL, LOG_DIR
    - PAPER_FILL_MODE（paper_trading 用のモック成行/部分約定設定: instant/partial/never/reject）
    - MONITOR_POLL_INTERVAL（監視ループのポーリング間隔を上書き）
    - KILL_FLAG_CLEAR_ON_START（Kill Switch 自動クリア のフラグ）
- ロギング:
  - 統一ログ設定ユーティリティを追加（kabusys.utils.logging_setup.setup_logging）。
    - stdout への StreamHandler（stdout を使用）と、日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR 指定やディレクトリ作成失敗時のフォールバック処理あり。
- プロセス制御:
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX (Linux, Darwin, FreeBSD) に対応し、権限不足時は警告を出してスキップ。
- Execution / Monitoring の実行スクリプト:
  - run_execution.py:
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、RiskManager の初期設定（初期ポートフォリオ値を broker.get_available_cash() で初期化）を実装。
    - execution.pid を利用した PID 管理、data/stop_requested.flag による安全停止対応。
  - run_monitoring.py:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する挙動を採用（安全上の設計判断の反映）。
    - stop フラグ検知でループを終了。例外発生時はログ出力して次サイクルへフォールバック。

- Portfolio モジュール（純粋関数ベース、DB 参照なし）:
  - select_candidates: スコア降順で上位 N 件を返す。
  - calc_equal_weights / calc_score_weights: 等金額/スコア加重の重み計算（スコア合計 0 の場合は等配分にフォールバック）。
  - apply_sector_cap: セクター集中度チェックで当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
  - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear を実装、未知は 1.0 でフォールバック）。
  - calc_position_sizes: allocation_method("risk_based"|"equal"|"score") に応じた発注株数計算。単元株対応、max_position_pct/ max_utilization/ cost_buffer による制約、aggregate cap によるスケールダウンと端数処理を実装。

- Paper Trading 検証レポート:
  - 稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）などを集計して PASS/FAIL 判定を出力するツールを追加。
  - P95 計算、期間フィルタの実装、閾値はソース内定義（稼働率 99% など）。

### Changed
- .env 読み込み・パース仕様の強化:
  - export KEY=val 形式のサポート、引用符付き値のエスケープ処理、インラインコメントの取り扱い（クォート内は無視、クォート外は先行スペースで # をコメントと判定）を実装。
  - _load_env_file に override / protected 引数を導入し、OS 環境変数を保護しつつ .env.local で上書きできる挙動を採用。
- validate_config の挙動:
  - 必須環境変数未設定やプレースホルダ（_here / your_value）に対する警告/エラー判定を実装。
  - PyYAML 未インストール時の挙動を明示（YAML 検証をスキップして警告を出す）。
  - config/*.yaml の存在チェックとパース検証を追加。
  - KABUSYS_ENV=live 時の追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険値に対する警告）を追加。
- ログ設定:
  - 既存ハンドラを一旦 flush/close してから再設定することで二重ハンドラ登録を防止。
  - ファイルハンドラ作成失敗時はコンソール出力にフォールバックして継続するよう変更。
- run_monitoring のポーリング間隔取得:
  - 不正な MONITOR_POLL_INTERVAL 値は警告を出してデフォルトにフォールバックする（0 や負値は無効）。

### Fixed
- 安全性と堅牢性の改善:
  - DB が開けない/テーブル欠損時のツール側の例外ハンドリング（paper_verification_report は OperationalError を捕捉してデフォルト値を返す）。
  - process_priority / set_cpu_affinity が権限不足や未対応プラットフォームで失敗した場合、警告ログを出してスキップするように変更（起動失敗を避ける）。
  - .env ファイル読み込み失敗時に warnings.warn でユーザーに通知するよう改善。
  - execution のスレッド終了待機と停止フラグ検知の取り扱い（短い join timeout を使いループで監視）を実装し、安全に停止できるように改善。

### Security
- シークレット値の取り扱い:
  - config_setup のウィザードで J-Quants トークンや KABU API パスワードを "secret" 扱いとして表示をマスク（出力時は **** 表示）。
  - .env のテンプレート生成時に .env を絶対に Git にコミットしない旨の注意書きを追加。

### Notes / Misc
- バージョン情報:
  - パッケージバージョンを __version__ = "0.1.0" として定義。
- 未実装 / TODO（コード内コメントより）:
  - position_sizing: 銘柄別の lot_size を将来的にサポートするための拡張予定（stocks マスタへの lot_size 記載）。
  - risk_adjustment: price が欠損（0.0）の場合のフォールバック価格の扱い改善の検討事項あり。
  - research.factor_research はファクター計算ロジックの実装途中（スニペット末尾が未完）。

---

今後のリリースでは、テストケースの追加、ドキュメント（API リファレンス・設計ドキュメント）整備、運用監視のアラート送信（LINE 連携テスト）などを予定してください。必要であれば、この CHANGELOG を元により詳細なリリースノート（英語/日本語）を作成します。