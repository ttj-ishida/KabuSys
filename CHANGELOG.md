CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
リリース日: 2026-04-18

Unreleased
----------

なし

0.1.0 - 2026-04-18
-----------------

Added
- 初期リリースを追加しました。システム全体の起動スクリプト、設定管理、ユーティリティ、ポートフォリオ構築ロジック、紙トレード検証ツールなどを含みます。
  - 起動スクリプト
    - 実行エンジン起動スクリプトを追加（run_execution.py）。（src/kabusys/run_execution.py）
      - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用して本番 DB と分離。
      - 停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を利用して安全に停止/管理。
      - BrokerClientFactory、ExecutionEngine、OrderManager、RiskManager、Reconciler の組み立てと起動処理を実装。
      - RiskManager の既定設定（max_position_pct 等）を実装。
    - 監視ポーリングループ起動スクリプトを追加（run_monitoring.py）。（src/kabusys/run_monitoring.py）
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用して初期化。
      - 停止フラグ検知でループ終了、例外発生時はログ記録して次回ポーリングへ（冪等・堅牢な設計）。
  - 設定管理
    - Settings クラスを実装し、.env / 環境変数から設定を読み込む仕組みを追加（src/kabusys/config.py）。
      - 自動 .env ロード（.env, .env.local）機能。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
      - 必須/任意の設定、デフォルト値、入力値検証を備えた多くのプロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグ関連、CPU/MEM/DISK 閾値等）。
      - settings のシングルトン提供。
  - 設定ツール / 検証
    - 対話式 .env 作成ウィザードを追加（config_setup.py）。デフォルト・既存値の再利用、シークレット扱いなどをサポート。（src/kabusys/config_setup.py）
    - 設定検証 CLI を追加（validate_config.py）。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML のパース検証（PyYAML がある場合）等をチェック。--strict オプションで警告を失敗扱いに可能。（src/kabusys/validate_config.py）
  - ログ / プロセス管理ユーティリティ
    - 統一的ロギング設定ユーティリティを追加（setup_logging）。stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler、30 日分保持）をルートロガーに設定。LOG_LEVEL / LOG_DIR の解決順を実装し、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで動作。（src/kabusys/utils/logging_setup.py）
    - プロセス優先度・CPU affinity 設定ユーティリティを追加（set_process_priority / set_cpu_affinity）。Windows / POSIX の差分を吸収し、権限不足時は警告のみでスキップ。（src/kabusys/utils/process_priority.py）
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - 候補選定・重み計算（portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights）。スコアが全て 0 の場合のフォールバック挙動も実装。（src/kabusys/portfolio/portfolio_builder.py）
    - セクター集中制限・レジーム乗数（risk_adjustment: apply_sector_cap, calc_regime_multiplier）。既存保有考慮や unknown セクター扱いの方針を実装。（src/kabusys/portfolio/risk_adjustment.py）
    - 株数決定・リスク制限・単元丸め（position_sizing: calc_position_sizes）。risk_based / equal / score 配分方式、lot_size による丸め、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ想定）等を実装。（src/kabusys/portfolio/position_sizing.py）
    - パッケージレベルのエクスポートを整備（src/kabusys/portfolio/__init__.py）
  - ツール
    - Paper Trading 検証レポート生成スクリプトを追加（tools/paper_verification_report.py）。
      - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を計算し、PASS/FAIL 判定する閾値を定義。
      - CLI オプション --from / --to / --db をサポート。PAPER_TRADING_SQLITE_PATH 環境変数により DB を指定可能。（src/kabusys/tools/paper_verification_report.py）
  - リサーチ（骨格）
    - ファクター計算モジュールの骨格を追加（research/factor_research.py）。モメンタムなどの計算設計（DuckDB 参照）を準備。将来的なファクター実装の下地。（src/kabusys/research/factor_research.py）
  - パッケージ情報
    - パッケージバージョンを設定（src/kabusys/__init__.py: __version__ = "0.1.0"）。

Changed
- ログ出力の振る舞いを明確化
  - StreamHandler は stdout を使用（stderr ではなく）し、Task Scheduler/cron 等での出力の一貫性を考慮。（src/kabusys/utils/logging_setup.py）
  - ログディレクトリ作成失敗時にファイルハンドラをスキップしても起動継続する耐障害設計を適用。
- 環境ファイル (.env) のロード順を明記
  - OS 環境変数 > .env.local > .env の優先度で自動ロードを実装。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。（src/kabusys/config.py）

Fixed
- process_priority / logging_setup 等で予期せぬ例外が発生してもサービス全体が落ちないように例外捕捉と警告ログを追加。（src/kabusys/utils/process_priority.py, src/kabusys/utils/logging_setup.py）
- run_monitoring/run_execution の終了時に使用した DB コネクションを確実にクローズするように finally ブロックで閉じる実装を保証。（src/kabusys/run_monitoring.py, src/kabusys/run_execution.py）

Security
- シークレット値（トークンやパスワード）は対話式ウィザードでマスク表示し、.env ファイル内に平文で保存するよう注意喚起（.env を絶対に Git にコミットしない旨を README ヘッダ風に記載）。（src/kabusys/config_setup.py）

Notes / Usage highlights
- 主要な環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD (必須)
  - KABUSYS_ENV (development | paper_trading | live)
  - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
  - LOG_LEVEL, LOG_DIR
  - MONITOR_POLL_INTERVAL (監視ポーリング間隔、秒。デフォルト 60)
  - PAPER_FILL_MODE (paper_trading 時の約定モード: instant/partial/never/reject)
  - KILL_FLAG_CLEAR_ON_START (本番での自動クリアを防ぐためデフォルト 0 推奨)
- 実行
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - 実行エンジン起動: python -m kabusys.run_execution
  - 監視起動: python -m kabusys.run_monitoring
  - 紙トレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

Acknowledgements
- 本リリースはプロジェクトの初期実装群を含み、将来的な拡張（ファクター計算の完成、エージェントやブローカー連携の詳細、単体テストの追加等）を想定しています。既知の制約や TODO はソース内コメント（TODO）として残しています。