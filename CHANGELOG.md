# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、コードベース（src/kabusys 配下）の現状から推測して作成した初期の変更履歴です。リリース履歴は実装内容を元に要点を抜粋しています。

なお、バージョンはパッケージの __version__（0.1.0）に合わせています。

## [Unreleased]
（未リリースの変更はここに記載）

## [0.1.0] - 初期リリース
リリース日: 2026-04-25（推定）

### Added
- 基本機能の実装
  - 日本株自動売買システム「KabuSys」のコアモジュール群を追加。
  - モジュール構成（主要ファイル）:
    - run_execution.py: ExecutionEngine 起動スクリプト（本番/ペーパートレード分離、PID 管理、停止フラグ対応）
    - run_monitoring.py: SystemMonitor 起動スクリプト（ポーリングループ、停止フラグ検知、MONITOR_POLL_INTERVAL 環境変数対応）
    - config.py: 環境変数 / .env 自動ロードと Settings クラス（各種設定プロパティ、妥当性チェック）
    - config_setup.py: 対話式 .env 作成ウィザード（シークレットマスク、既存値再利用、ファイル書き出し）
    - validate_config.py: 起動前設定検証 CLI（必須環境変数・YAML ファイル存在・本番環境ガード等）
    - utils/logging_setup.py: 統一ログ設定ユーティリティ（stdout 出力 + 日次ローテーションファイル）
    - utils/process_priority.py: クロスプラットフォームのプロセス優先度 / CPU アフィニティ設定ユーティリティ（Windows / POSIX 対応）
    - portfolio/*: ポートフォリオ構築用の純粋関数群（候補選定、重み付け、セクター上限適用、ポジションサイズ計算）
    - research/factor_research.py（ファクター計算基盤の一部）：DuckDB 経由でモメンタム等を計算する設計開始
    - tools/paper_verification_report.py: ペーパートレード検証レポート生成ツール（稼働率・成功率・レイテンシ等の指標算出）
- 設定 / 環境変数の自動ロード機能を実装
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込み（OS 環境変数を上書きしない保護あり）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能
- Execution / Monitoring の DB 分離
  - run_execution: KABUSYS_ENV=paper_trading 時は PAPER_TRADING_SQLITE_PATH（data/paper_trading.db がデフォルト）を使用して本番 DB と完全分離
  - run_monitoring: 監視は環境にかかわらず本番の sqlite_path を使用する旨を明記（監視 DB を保証）
- ロギング
  - 共通の setup_logging(app_name, log_dir, level) を導入。コンソールは stdout を使い、ファイルは日次ローテーション（30日分保持）
  - ログディレクトリ作成に失敗した場合はコンソール出力にフォールバック
- プロセス優先度 & CPU アフィニティ
  - set_process_priority(level) で Windows/POSIX の差分を吸収して優先度（high/normal/low）を設定
  - set_cpu_affinity(cpu_count) で最初の N コアに固定するユーティリティを実装（権限不足や未対応環境では警告のみ）
- ポートフォリオ構築ロジック（純粋関数）
  - select_candidates, calc_equal_weights, calc_score_weights（候補選定・重み付け）
  - apply_sector_cap（セクター集中制限、"unknown" セクターは除外しない動作）
  - calc_regime_multiplier（レジームに基づく投下資金乗数、未知レジームは 1.0 にフォールバック）
  - calc_position_sizes（risk_based / equal / score の各配分方式、単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer 対応）
- ペーパートレード検証ツール
  - Paper Trading のログ（trade_logs, system_status, risk_logs 等）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を集計してレポートを出力
  - デフォルト基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し PASS/FAIL を判定
  - CLI 引数で期間指定（--from/--to）および DB パス指定（--db）に対応

### Changed
- N/A（初期リリースのため既存の変更履歴はなし）

### Fixed
- 設定読み込み・パースの堅牢化
  - .env パーサでクォート文字列内のバックスラッシュエスケープを正しく扱う実装
  - 非クォート文字列でのインラインコメント扱いをスペース前の `#` で判断する仕様
  - _get_poll_interval 相当の入力チェックで 0 以下や不正な数値に対してデフォルト 60 秒へフォールバック（警告出力）
- 安全な起動・終了処理
  - run_execution / run_monitoring 共に停止フラグ（data/stop_requested.flag 等）の検知で Graceful shutdown を行う
  - run_execution ではスレッド終了待機と最大待機タイムアウトを設け、DB 接続を finally で確実に閉じる
  - run_monitoring では monitor.check_once() の例外を捕捉してログに出力し、次ポーリングに回すようにしてサービスの継続性を確保

### Security
- シークレット取り扱い
  - config_setup のウィザードで J-Quants トークンや kabu API パスワード等はシークレットとしてマスク表示
  - .env ファイル生成時に「.env を絶対に Git にコミットしないこと」を明示

### Documentation / UX
- validate_config: 起動前に環境変数や config/*.yaml のチェックを行う CLI を追加（--strict フラグで警告を FAIL 扱い）
  - PyYAML が未インストールの場合は YAML 検証をスキップして警告を出す
  - 本番環境（KABUSYS_ENV=live）向けのガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の警告）を実装
- config_setup: 対話式ウィザードにより初回セットアップを補助し、既存 .env を読み込んで再利用可能
- ログ設定に関する設計方針と挙動をコメントに明記（stdout 使用理由、ファイルローテーションなど）

### Known issues / Notes
- research/factor_research.py は実装の途中（ファイル末尾に未完の箇所あり）。ファクター計算ロジックは設計に基づいているが一部未完。
- position_sizing の一部:
  - price が欠損（0.0）の場合、エクスポージャーやポジション計算が過少見積りになる可能性がある旨の TODO コメントあり（フォールバック価格の導入検討）。
- 一部機能は実行環境依存（psutil による優先度設定や CPU affinity）は権限不足や未対応 OS ではスキップされ、警告を出す実装になっている。
- run_monitoring は「監視は常に本番 sqlite_path を使う」と明記しているため、開発環境で監視 DB を分離したい場合は設定・コードの見直しが必要。

---

その他、リリースノートに追加したい点や各モジュールの詳細を個別に分けた CHANGELOG（例: portfolio の改善履、ツール追加履等）を作成することも可能です。必要であれば、用途別（運用者向け / 開発者向け）の簡易リリースノートも用意します。どの形式をご希望でしょうか？