CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に準拠します。
フォーマット: https://keepachangelog.com/ja/1.0.0/

v0.1.0 - 2026-04-18
-------------------

Added
- 基本リリース: KabuSys の初期実装を追加しました。主要なコンポーネント・ユーティリティを含みます。
  - パッケージ情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - 起動スクリプト
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db など）を使用し、本番 DB と分離して動作します。
      - 停止フラグ（data/stop_requested.flag）で安全に終了可能。PID ファイル管理、スレッドでのエンジン実行/停止制御を実装。
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。
      - 監視は環境に関わらず本番 sqlite_path を参照して初期化します。
  - 設定関連
    - src/kabusys/config.py
      - .env 自動ロード機能（プロジェクトルートを .git または pyproject.toml で探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env 解析の強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理など）。
      - Settings クラスを提供し、J-Quants / kabu API / DB パス /監視閾値 等のプロパティと検証を定義。
      - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等 Paper Trading 向け設定を提供。
  - 設定支援ツール・検証
    - src/kabusys/config_setup.py
      - 対話式ウィザードで .env を作成・更新する CLI を追加。複数の項目定義（秘密値マスク、選択肢、デフォルト値）をサポート。
    - src/kabusys/validate_config.py
      - 起動前に環境変数・config/*.yaml の整合性をチェックする CLI を追加。--strict オプションで警告を失敗扱いにできます。
  - Paper Trading 検証ツール
    - src/kabusys/tools/paper_verification_report.py
      - ペーパートレード用 SQLite から稼働率・注文成功率・送信率・レイテンシ（P95 等）を集計し、PASS/FAIL 判定付きレポートを出力する CLI を追加。
      - --from / --to / --db オプションをサポート。デフォルト DB パスは data/paper_trading.db。
  - ポートフォリオ構築モジュール（純粋関数）
    - src/kabusys/portfolio/portfolio_builder.py
      - 対象銘柄選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
      - スコア全体が 0 の場合は等配分へフォールバック。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限の適用（apply_sector_cap）、市場レジームに基づく乗数（calc_regime_multiplier）を実装。
      - unknown セクターはセクター上限の対象外にする挙動。
      - 未知レジームは警告を出して 1.0 にフォールバック。
    - src/kabusys/portfolio/position_sizing.py
      - 発注株数計算（calc_position_sizes）を実装。risk_based / equal / score の配分方式をサポートし、単元株（lot_size）丸め、最大ポジション上限、aggregate cap（available_cash によるスケール）、cost_buffer を用いた保守的見積もり等を実装。
  - ユーティリティ
    - src/kabusys/utils/logging_setup.py
      - 統一的なログ設定ユーティリティを追加。stdout 出力（StreamHandler）と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ自動作成、ファイル出力作成失敗時はコンソールのみで継続。デフォルトログディレクトリは logs/、30 日分バックアップ。
    - src/kabusys/utils/process_priority.py
      - プロセス優先度（nice / Windows 優先度）と CPU affinity 設定ユーティリティを追加。Windows と POSIX (Linux / Darwin / FreeBSD) を吸収し、アクセス権限がない場合は警告を出してスキップ。
  - 研究用ファクターモジュール（骨格）
    - src/kabusys/research/factor_research.py
      - Momentum などファクター計算の設計・一部実装（定数・インターフェース）。（実装途中）

Changed
- 監視・実行系の挙動整理
  - run_monitoring: MONITOR_POLL_INTERVAL 環境変数からポーリング間隔取得時に不正値を検出するとデフォルト（60 秒）へフォールバックし、警告を出すように改善。
  - run_execution: Paper Trading 環境時は専用 SQLite を使用して本番 DB と完全分離するよう明確化。
- .env の自動読み込み順序は OS 環境変数 > .env.local > .env として明確化。既存 OS 環境変数は保護（上書き防止）されます。
- logging_setup: デフォルトで stdout を StreamHandler に使用（stderr ではない）し、ログの一本化を意図した挙動に変更。

Fixed
- 設定周りの堅牢化
  - .env 解析での quoted 値内のバックスラッシュエスケープ対応、export プレフィックス対応、インラインコメントの取り扱いを改善し、より実運用に耐えるパーサーにしました。
  - Settings の各プロパティで入力検証を追加（PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV / LOG_LEVEL の検証など）。不正値時は明確な例外を送出するようにしています。
- utils/process_priority.py:
  - 未サポート OS や権限不足時に例外でプロセスを落とさないよう例外を捕捉し、警告してスキップするようにしました。

Notes
- このリリースは「初期実装」として、多くの機能を CLI/ユーティリティ・純粋関数として提供しますが、実稼働前に以下を推奨します:
  - python -m kabusys.config_setup による .env 作成後、python -m kabusys.validate_config で設定検証を行ってください。
  - 本番運用前に KABUSYS_ENV=live の設定を慎重に確認してください（validate_config による追加警告あり）。
  - Paper Trading の動作確認は専用 DB（PAPER_TRADING_SQLITE_PATH）で行ってください。本番 DB とデータ分離されています。
- research/factor_research.py は実装途中のため、ファクター計算の完全実装は今後のリリースで追加予定です。

Acknowledgements
- 初回リリースにあたり、構成・設計方針（ログ管理、設定管理、Paper Trading と本番の分離、ポートフォリオ構築の純粋関数化）を優先して整備しました。今後はテスト・ドキュメント・欠落機能の追加を進めます。