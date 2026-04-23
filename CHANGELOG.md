# Changelog

すべての注目すべき変更点を記録します。  
このプロジェクトは「Keep a Changelog」仕様に準拠します。  

## [Unreleased]
- 今後のリリースに向けた軽微な改善・テストの追加予定
  - research.calc_momentum の続き実装、その他ファクター計算の完成
  - ロギングや監視の運用テストに基づく微調整

---

## [0.1.0] - 2026-04-23

最初の公開バージョン。自動売買システム KabuSys のコア機能群を含む初期リリースです。

### Added
- 基本ライブラリ・モジュール
  - kabusys.config: 環境変数/.env 読み込みと Settings 抽象化
    - プロジェクトルート探索による自動 .env ロード（.env / .env.local、OS 環境変数保護機能付き）
    - 必須環境変数取得ヘルパーと各種設定プロパティ（DB パス、Paper Trading 設定、監視閾値など）
  - kabusys.utils.logging_setup: 統一ロギング設定ユーティリティ
    - stdout 出力（StreamHandler）と日次ローテーションファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定
    - ログディレクトリ作成のフォールバック（失敗時はコンソールのみで継続）
  - kabusys.utils.process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
    - Windows / POSIX の差分吸収、権限エラー時の安全なフォールバック
  - kabusys.portfolio: ポートフォリオ構築関連の純粋関数群
    - portfolio_builder: 候補選定（select_candidates）、重み計算（calc_equal_weights, calc_score_weights）
    - risk_adjustment: セクター上限適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）
    - position_sizing: 発注株数決定ロジック（calc_position_sizes） — risk_based / equal / score 配分、集計キャップ、lot 単位丸め等を実装
  - kabusys.research.factor_research: ファクター計算モジュール（モメンタム等の設計と一部実装）
  - kabusys.tools.paper_verification_report: Paper Trading 検証レポート生成スクリプト
    - 稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（P95 など）を集計・判定してレポート出力
  - kabusys.monitoring / monitoring 起動スクリプト（run_monitoring.py）
    - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイルによる安全停止、監視用 DB 初期化を行う（本番 sqlite_path を使用）
  - kabusys.execution / 実行エンジン起動スクリプト（run_execution.py）
    - ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し、MockBroker を動作させる設計。
    - ブローカーの抽象化（BrokerClientFactory）、OrderManager、RiskManager、Reconciler の組立てと実行スレッド管理
  - CLI サポート
    - kabusys.config_setup: 対話式 .env ウィザード（.env の初期作成・更新を支援、シークレットはマスク表示）
    - kabusys.validate_config: 起動前設定検証ツール（必須/任意環境変数、DB パス、config/*.yaml の存在と YAML パース検証等）
      - --strict による警告を失敗扱いにするオプション

### Changed
- （初版リリースのため該当なし）

### Fixed / Robustness
- .env パーサーの挙動を丁寧に実装
  - export プレフィックス対応、クォート文字列とエスケープ処理、コメントの取り扱いに対応
  - .env の上書き制御（OS 環境変数保護）や .env.local の優先読み込みを実装
- ロギング設定の二重設定防止（既存ハンドラを flush/close してから再設定）
- process_priority / set_cpu_affinity:
  - 未対応 OS や権限不足時に安全にスキップして警告出力する実装
- DB 接続の取り扱い改善
  - monitoring 実行時に monitoring DB の初期化を行う init_monitoring_db 呼び出し（冪等）
  - Execution スクリプトは paper_trading 環境では別 sqlite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離
- 実行制御用の停止フラグ / PID ファイルの取り扱いを統一
  - stop_requested.flag による安全停止検知、ExecutionEngine はスレッド監視で停止を伝播

### Security / Ops
- config_setup による .env 生成でシークレットは画面上はマスク表示。注意書きとして .env を Git に絶対にコミットしない旨を記載。
- validate_config による事前チェックで本番環境（KABUSYS_ENV=live）の設定漏れを警告

### Documentation / UX
- 各スクリプト・モジュールに詳細な docstring / 使用例を追加
  - run_monitoring, run_execution, config_setup, validate_config, paper_verification_report, portfolio モジュール等に利用方法や設計方針を明記

### Removed
- （初版リリースのため該当なし）

---

未記載のバグや改善点が見つかった場合、次回以降のリリースで詳細を追記します。