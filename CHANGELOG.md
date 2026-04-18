# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
この CHANGELOG は与えられたコードベースの内容から推測して作成したもので、実装上の注記・既知の挙動を含みます。

## [Unreleased]

### Added
- 初期リリース準備（ライブラリ構成・主要モジュールを追加）
  - アプリケーションのバージョンを `__version__ = "0.1.0"` として定義。
- 環境設定/管理機能
  - .env 自動読み込み機能（プロジェクトルートを .git / pyproject.toml で検出）。
  - .env ファイルの堅牢なパーサーを実装（`export ` プレフィックス対応、クォート内のエスケープ処理、インラインコメントの扱い等）。
  - Settings クラス (`kabusys.config.Settings`) による環境変数ラップとバリデーション（KABUSYS_ENV / LOG_LEVEL 等の許容値チェック、各種パスのデフォルト提供）。
  - 対話式環境設定ウィザード CLI（`kabusys.config_setup`）で .env の生成・更新を支援。
  - 設定検証 CLI（`kabusys.validate_config`）で必須環境変数、DB パス、config/*.yaml 等の検査を実行。
- 実行・監視ランナー
  - 実行エンジン起動スクリプト（`run_execution.py`）
    - 起動時にプロセス優先度を "high" に設定。
    - ペーパートレード環境時は専用 SQLite（`data/paper_trading.db` 等）を使用して本番 DB と分離。
    - Broker クライアントファクトリ、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てとスレッド駆動の実行制御を実装。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止機構。
  - 監視ポーリングループ起動スクリプト（`run_monitoring.py`）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視データを記録（設計上の意図として明示）。
    - SystemMonitor の単発チェックと例外サニタイズ（チェック中の例外はログ出力して次回ポーリングまで待機）。
- ロギング / プロセス管理ユーティリティ
  - 統一ロギング設定ユーティリティ（`kabusys.utils.logging_setup.setup_logging`）
    - stdout 出力用 StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app>.log）を設定。
    - 既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバック等に対応。
  - プロセス優先度・CPU affinity ユーティリティ（`kabusys.utils.process_priority`）
    - Windows / POSIX を吸収する set_process_priority と set_cpu_affinity を提供（psutil ベース）。
    - 権限不足や未対応プラットフォーム時は警告を出して安全にスキップ。
- ポートフォリオ構築関連モジュール
  - 候補選定・重み計算（`kabusys.portfolio.portfolio_builder`）
    - select_candidates, calc_equal_weights, calc_score_weights を実装。スコアが全て 0 の場合は等分配へフォールバック。
  - セクター上限・レジーム乗数（`kabusys.portfolio.risk_adjustment`）
    - apply_sector_cap によるセクター集中除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier によるレジーム別乗数（bull/neutral/bear のマップ、未知レジームは 1.0 にフォールバック）。
  - 株数決定・リスク制限（`kabusys.portfolio.position_sizing`）
    - calc_position_sizes により risk_based / equal / score の配分方式に対応。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap、cost_buffer による保守的見積もり、スケーリングと端数分配ロジックを実装。
- 解析・検証ツール
  - Paper Trading 検証レポート（`kabusys.tools.paper_verification_report`）
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を計算して PASS/FAIL 判定（しきい値はソースに定義）。
    - 日付フィルタ指定、DB パス引数 / 環境変数対応。
- DuckDB を用いたリサーチ基盤（`kabusys.research.factor_research`）
  - prices_daily / raw_financials を前提にモメンタム等のファクター計算関数（calc_momentum 等）の実装を開始（DuckDB 接続を受け取る設計）。

### Changed
- .env 読み込みの挙動を明確化
  - 読み込み優先順位は OS 環境変数 > .env.local > .env（`KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化オプションあり）。
  - 読み込み時は既存の OS 環境変数を保護（protected set）して上書きを制御。
- ロギング挙動の改善
  - コンソールは stdout を使用（cron 等で stdout/stderr を一本化する運用に対応）。
  - ハンドラ重複を防ぐため既存ハンドラを明示的に削除してから再設定。
- 実行/監視起動フローの明文化
  - 起動直後にプロセス優先度を上げる仕組みを共通化。
  - 監視は監視用 DB テーブルの初期化（冪等）を保証するよう init_monitoring_db を呼び出し。

### Fixed
- 環境変数パーサーの不具合修正（想定）
  - 引用符付き値内のバックスラッシュエスケープと対応する閉じクォート検出を正しく扱うよう修正。
  - クォートなし値の inline コメント判定を改善（`#` の直前がスペース/タブである場合のみコメントとみなす）。
- ロギングファイルハンドラ作成失敗時のフォールバックと警告出力を強化。

## [0.1.0] - 2026-04-18

初回の明示的バージョン（パッケージメタに合わせたスナップショット）。上記の機能群を含みます。

- 主要機能
  - 環境管理（.env 読み込み、Settings）、対話式 config ウィザード、設定検証ツール。
  - 実行エンジンと監視ループの起動スクリプト（プロセス優先度・停止フラグ対応）。
  - ロギングとプロセス制御ユーティリティ。
  - ポートフォリオ構築（候補選定・重み計算・リスク調整・ポジションサイズ算出）。
  - Paper Trading 向け検証レポート生成ツール。
  - DuckDB 経由のファクター計算の下地（モメンタム等）。

- 安全性／運用
  - paper_trading 環境での DB 分離（本番 DB と完全に分けてペーパートレードを記録）。
  - 起動時のプロセス優先度設定や停止フラグの検出により、運用時の停止/優先度設定をサポート。
  - 本番環境向けのいくつかのガード（validate_config による LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告等）。

---

注記:
- 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴や意図した変更履歴と差分がある可能性があります。必要であれば実コミットログ（git）に基づく正確な CHANGELOG へ更新してください。