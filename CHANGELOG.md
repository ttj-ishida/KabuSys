CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-23
--------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークの基本機能を実装。
  - パッケージエントリポイントとバージョンを追加
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - 起動用スクリプト
    - run_execution: ExecutionEngine 起動スクリプトを追加。環境変数 KABUSYS_ENV による paper_trading モードの分離（専用 SQLite DB）をサポート。停止フラグ (data/stop_requested.flag) と PID ファイル管理を実装。
      - ファイル: src/kabusys/run_execution.py
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は常に本番用 sqlite_path を使用する設計。
      - ファイル: src/kabusys/run_monitoring.py
  - 環境設定関連
    - Settings クラスにより環境変数の集中管理を実装（デフォルト値・バリデーション付き）。
      - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、KABUSYS_ENV などをサポート。
      - ファイル: src/kabusys/config.py
    - 対話式 .env 作成ウィザードを実装（python -m kabusys.config_setup）。
      - ファイル: src/kabusys/config_setup.py
    - 設定検証 CLI を追加（python -m kabusys.validate_config）。必須環境変数、パス、YAML ファイル存在および本番環境向けガードをチェック。
      - ファイル: src/kabusys/validate_config.py
  - ロギング / プロセスユーティリティ
    - 統一ロギングセットアップユーティリティを追加。Stream (stdout) と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
      - ファイル: src/kabusys/utils/logging_setup.py
    - プロセス優先度・CPU affinity 設定ユーティリティを追加（Windows/Linux/Mac を吸収）。
      - set_process_priority / set_cpu_affinity を提供。
      - ファイル: src/kabusys/utils/process_priority.py
  - ポートフォリオ構築（純粋関数群）
    - 候補選定・重み計算: select_candidates, calc_equal_weights, calc_score_weights
      - ファイル: src/kabusys/portfolio/portfolio_builder.py
    - セクター集中制限・レジーム乗数: apply_sector_cap, calc_regime_multiplier
      - ファイル: src/kabusys/portfolio/risk_adjustment.py
    - 株数決定・丸め・資金配分ロジック: calc_position_sizes（risk_based / equal / score）
      - ファイル: src/kabusys/portfolio/position_sizing.py
    - ポートフォリオ API のエクスポートを追加（kabusys.portfolio）。
      - ファイル: src/kabusys/portfolio/__init__.py
  - リサーチ / ファクター計算（骨格）
    - DuckDB 接続を受け取ってモメンタム等のファクターを計算するモジュールを追加（calc_momentum などのインターフェース設計）。
      - ファイル: src/kabusys/research/factor_research.py（モジュール実装の一部）
  - Paper Trading ツール
    - ペーパートレード検証レポート生成ツールを追加（コマンドラインから期間を指定して SQLite DB を解析、稼働率/成功率/レイテンシ等を出力）。
      - ファイル: src/kabusys/tools/paper_verification_report.py

Changed
- 設定読み込みの自動化（デフォルト動作）
  - プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動読み込みする仕組みを追加。既存 OS 環境変数は保護され、.env.local は .env を上書き可能。
    - ファイル: src/kabusys/config.py
- ログ出力先の挙動
  - StreamHandler は stderr ではなく stdout を使用（cron/task scheduler で stdout/stderr の一本化がしやすくなるため）。
    - ファイル: src/kabusys/utils/logging_setup.py

Fixed
- 環境変数パースの堅牢化
  - .env の各行パースロジックを改善（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理など）。
    - ファイル: src/kabusys/config.py
- ポジションサイズ計算におけるスケールダウンの端数処理
  - aggregate cap 適用時に lot_size 単位で再配分するアルゴリズムを実装し、再現性を確保（残差の大きい順に配分）。
    - ファイル: src/kabusys/portfolio/position_sizing.py
- セクターキャップの扱い
  - sector_map に存在しない銘柄は "unknown" 扱いとし、セクター上限の除外対象から除外することで不必要なブロックを防止。
    - ファイル: src/kabusys/portfolio/risk_adjustment.py
- Execution 起動時の DB 初期化
  - monitoring 用テーブルが存在することを起動時に保証する init_monitoring_db 呼び出しを追加（冪等）。
    - ファイル: src/kabusys/run_execution.py, src/kabusys/run_monitoring.py

Internal
- 例外ハンドリング強化
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を投げた場合にログ出力して継続するように変更（監視のロバスト化）。
    - ファイル: src/kabusys/run_monitoring.py
- 各種デフォルト値・しきい値を設定
  - Paper 検証レポートでの基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
    - ファイル: src/kabusys/tools/paper_verification_report.py
  - process_priority のデフォルト使用箇所は "high" に設定（起動直後に呼び出す実装）。
    - ファイル: src/kabusys/run_execution.py, src/kabusys/run_monitoring.py
- DuckDB / SQLite の共存設計
  - 実行エンジン・監視ともに DuckDB を分析用に、SQLite を監視/トランザクション記録用に使い分ける設計を採用（接続確立処理を統一）。

Notes / Migration
- 環境変数の自動ロード:
  - デフォルトではプロジェクトルートを検出して .env / .env.local を自動で読み込みします。テストや特殊環境で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_TRADING:
  - paper_trading モードは paper 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用して本番 DB と分離します。ペーパートレードの振る舞いは PAPER_FILL_MODE で制御されます（instant/partial/never/reject）。
- ログディレクトリ:
  - デフォルトは logs/。環境変数 LOG_DIR や setup_logging の引数で変更可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみでログを出力します。

Acknowledgements / TODO
- factor_research モジュールは関数の骨格／設計を含むが、いくつかの実装が途中（ファイル途中で切れている）。今後の実装で DuckDB を用いたファクター計算を完成予定。
- 将来的に単元株数 lot_size を銘柄別で持たせる拡張（stocks マスタの導入）を想定。
- さらに細かなエラー監視・アラート（LINE 通知連携など）は既に設定変数やガードを用意済み。運用フェーズで調整予定。

--- 

この CHANGELOG はコードベースの内容から推測して作成しています。リリースノートに追記・修正が必要な点があれば教えてください。