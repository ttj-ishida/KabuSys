CHANGELOG
=========

すべての重要な変更を記録します。フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 初期リリース。主要なモジュールおよび CLI を追加。
  - 環境設定・管理 (src/kabusys/config.py)
    - .env 自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を探索して決定）。
    - export 形式・クォート（シングル/ダブル）・バックスラッシュエスケープ・インラインコメントを考慮した堅牢な .env パーサを実装。
    - 環境変数取得用 Settings クラスを提供（各種パス、しきい値、環境判定ユーティリティ等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - 対話型設定ウィザード CLI (src/kabusys/config_setup.py)
    - .env の初期作成・編集を支援する対話ウィザードを追加。.env 保存機能を備える。
  - 設定検証 CLI (src/kabusys/validate_config.py)
    - 必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在とパースを検証するツールを追加。
    - --strict モードで警告を失敗扱いにできる。
  - 実行・監視スクリプト
    - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
      - プロセス優先度設定、SQLite/DuckDB 接続、ブローカー生成（paper_trading の場合は MockBrokerClient と専用 DB を使用）、OrderManager / RiskManager / Reconciler 組立て、ExecutionEngine 起動、停止フラグ・PID 管理、スレッド実行ループを実装。
      - paper_trading 環境時は data/paper_trading.db を利用して本番 DB と分離。
    - 監視ループ起動スクリプト (src/kabusys/run_monitoring.py)
      - SystemMonitor の初期化・ポーリングループ実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検知で安全に終了。
      - 監視では環境にかかわらず本番 sqlite_path を使用する設計。
  - ロギングユーティリティ (src/kabusys/utils/logging_setup.py)
    - StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定する共通設定関数を追加。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールログのみで継続するフォールバックを実装。
  - プロセス優先度・CPU affinity ユーティリティ (src/kabusys/utils/process_priority.py)
    - Windows / POSIX の差分を吸収して set_process_priority と set_cpu_affinity を提供。権限不足や未対応 OS に対しては警告を出して安全にスキップする。
  - ポートフォリオ構築関連 (src/kabusys/portfolio/*)
    - 候補選定・重み計算: select_candidates, calc_equal_weights, calc_score_weights を実装。
    - セクター集中制限・レジーム乗数: apply_sector_cap, calc_regime_multiplier を実装。
    - 株数決定・単元丸め: calc_position_sizes を実装（risk_based / equal / score 対応、lot_size 単位丸め、aggregate cap のスケーリングと端数処理ロジックを含む）。
  - 研究用ファクター計算（骨組み） (src/kabusys/research/factor_research.py)
    - Momentum / Value / Volatility / Liquidity を計算するための設計、モメンタム計算の骨組みを追加（DuckDB を用いた prices_daily 参照想定）。
  - ペーパートレード検証ツール (src/kabusys/tools/paper_verification_report.py)
    - ペーパートレード DB から稼働率、注文成功率、送信率、レイテンシ（P95 等）を集計して PASS/FAIL 判定を出力するレポート生成スクリプトを追加。閾値はソース内定義（例: 稼働率 >= 99% 等）。
  - パッケージメタ情報
    - バージョンを __version__ = "0.1.0" として設定（src/kabusys/__init__.py）。

Changed
- ロギング
  - StreamHandler は stdout を使用（stderr ではなく）。Task Scheduler / cron 等でのリダイレクトを意識した設計。
- .env 読み込みの優先順位
  - OS 環境変数 > .env.local > .env の順で上書き処理を行う（既存 OS 環境変数は保護される）。
- run_monitoring の設計決定
  - 監視側は KABUSYS_ENV に関わらず本番 sqlite_path を利用する仕様を明示。

Fixed / Improved
- .env パーサの堅牢化（クォートされた値のエスケープ処理、export プレフィックス、インラインコメントの扱いを改善）。
- calc_score_weights: 全銘柄のスコアが 0.0 の場合に等金額配分へフォールバックし、警告を出すようにした。
- apply_sector_cap: "unknown" セクターの扱いを明示（上限制約の対象外）。
- process_priority と set_cpu_affinity:
  - 権限不足・未サポート環境での例外を捕捉して安全にスキップし、警告ログを出すよう改善。
- logging_setup:
  - ログディレクトリ作成に失敗した場合はファイルハンドラの追加をスキップし、標準出力のみで継続するよう改善。
- run_execution / run_monitoring:
  - 起動時にプロセス優先度を設定する処理を追加（最初に実行）。停止フラグ（data/stop_requested.flag）検知で安全にシャットダウン。

Notes
- MONITOR_POLL_INTERVAL の不正な値（数値変換失敗や 0 以下）は警告してデフォルト（60 秒）にフォールバックします。
- Paper Trading と Live の DB/発注の分離を意識した設計（paper_trading 環境では専用 SQLite を使用）。
- factor_research.py は主要な計算方針と定数を含む骨組みを実装していますが、一部未完成の箇所があります（今後の拡張を想定）。

Acknowledgments
- 初期機能群の実装により、設定管理、起動・監視、発注ロジック、ポートフォリオ構築、検証ツール、ロギング/プロセス操作など自動売買システムの基盤が整いました。今後はテスト追加・ドキュメント整備・factor/strategy 実装の補完を予定しています。