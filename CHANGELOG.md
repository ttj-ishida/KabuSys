# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" 準拠です。

<!-- 既知のリリース: 初期バージョン 0.1.0 をコードベースから推測して作成しています -->

## [0.1.0] - 2026-04-19

### Added
- 初期リリースとして以下の主要機能を追加。
  - 実行系 / 監視系エントリポイント
    - run_execution.py: ExecutionEngine を起動するスクリプト。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）へ記録する。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）により外部から停止可能。
  - 環境設定 / 検証 CLI
    - config_setup.py: 対話式ウィザードで .env を初期作成 / 更新する CLI（python -m kabusys.config_setup）。
    - validate_config.py: .env と config/*.yaml の起動前検証 CLI。--strict オプションで警告を FAIL 扱いにできる（python -m kabusys.validate_config）。
  - 設定管理モジュール
    - config.py: 環境変数読み込み、自動 .env ロード（プロジェクトルート検出）、必須変数チェック、各種設定プロパティ（DB パス、ログレベル、環境判定フラグ、paper_trading 用設定等）。
      - 自動ロードは .env → .env.local の順で行い、OS 環境変数は保護（上書きされない）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可。
      - .env ファイルの行パースは export プレフィックスやクォート、インラインコメントをサポート。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio.portfolio_builder: 候補選定 (select_candidates)、等重配分 (calc_equal_weights)、スコア重み配分 (calc_score_weights)。
    - portfolio.risk_adjustment: セクター集中制限の apply_sector_cap、レジーム乗数 calc_regime_multiplier。
    - portfolio.position_sizing: position sizes 計算ロジック (risk_based / equal / score)、単元株丸め、aggregate cap のスケーリング処理（残差配分ロジック含む）。
  - ユーティリティ
    - utils/logging_setup.py: 統一ログ設定ユーティリティ（stdout StreamHandler + 日次ローテーションのファイルハンドラ）。LOG_DIR / LOG_LEVEL の解決、ログディレクトリ作成失敗時のフォールバック。
    - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定と CPU affinity 設定（psutil ベース）。set_process_priority, set_cpu_affinity を提供。
  - 監視 / モニタリング補助
    - monitoring_db 初期化呼び出しポイント（run_* 側で init_monitoring_db を呼ぶことで監視テーブルを保証）。
  - ツール
    - tools/paper_verification_report.py: ペーパートレード用検証レポート生成スクリプト。期間指定（--from / --to）や DB 指定（--db）に対応。稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定する。デフォルト閾値（稼働率 99%、成立率 90% 等）を定義。
  - リサーチ
    - research/factor_research.py: ファクター計算モジュール（Momentum / Value / Volatility / Liquidity の設計、DuckDB 経由の計算を想定）。（コードは部分実装／続きあり）

### Changed
- 設計上の重要な挙動
  - run_monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path（Settings.sqlite_path）を使用して監視データを記録する仕様になっている点を明示。
  - run_execution は paper_trading 環境時に DB を完全に分離（paper_sqlite_path を使用）することでペーパートレードと本番 DB を混在させない設計。
  - logging_setup のデフォルトは logs/ ディレクトリ、日次ローテーションで 30 日分保持。ディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続する（頑健性の向上）。
  - config.py の自動環境変数ロードはプロジェクトルートの検出（.git または pyproject.toml 基準）に依存し、CWD に依存しない動作を提供。

### Fixed / Robustness improvements
- 環境変数パーサ (_parse_env_line) の強化
  - export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、インラインコメントの取り扱い、空行やコメント行を無視する等の堅牢化を実装。
- process_priority / set_cpu_affinity は権限不足や未実装 OS を安全に扱い、失敗時に警告を出してスキップするように改善（例外を直接上げない）。
- run_monitoring / run_execution は停止フラグ（data/stop_requested.flag）や pid ファイルの扱いを組み込み、外部からの安全な停止制御をサポート。
- paper_verification_report: DB が存在しない場合のエラーメッセージや、テーブル欠如時の例外ハンドリング（OperationalError をキャッチしてデフォルト値で継続）を追加。

### Documentation / Messages
- 各モジュールに詳細な docstring と実装上の注記（PortfolioConstruction.md / StrategyModel.md 等への参照）を追加し、内部アルゴリズムや設計意図を明確化。
- config_setup の出力テンプレートに .env を絶対に Git にコミットしない旨を明記。

### Known limitations / TODOs
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に欠損（price が 0.0）の場合にエクスポージャーが過少評価される可能性がある旨の注記あり（将来的に前日終値や取得原価でフォールバックすることを検討）。
- position_sizing:
  - 単元株数 (lot_size) は現状グローバル共通。将来的に銘柄毎の lot_map を受け取る拡張予定（コメントで TODO 記載）。
- research/factor_research.py は部分実装で末尾が未完（関数の続きが存在する想定）。完全なファクター計算ロジックは引き続き実装が必要。
- monitoring_db の実体ファイルはこのスナップショットに含まれていない（init_monitoring_db の存在を仮定して呼び出している）。

### Security
- 機密情報（J-Quants トークン、Kabu API パスワード、LINE トークン等）は .env に格納する想定。config_setup ではシークレット項目はマスク表示するが、.env を Git にコミットしない旨を明確に注意喚起。

---

今後のリリースでは以下を検討すると良い点（例）:
- research/factor_research の完成・テスト追加
- 単体テスト・統合テストの充実（特に position sizing のスケーリング挙動）
- monitoring_db 実装の明示・マイグレーション／スキーマ管理
- 銘柄毎 lot_size 対応や価格フォールバックロジックの実装
- ドキュメント（README・操作手順）の追加・整備

（この CHANGELOG は与えられたコードの内容から推測して作成しました。実際の変更履歴や過去バージョンとの差分に基づく正式な CHANGELOG が存在する場合はそちらを優先してください。）