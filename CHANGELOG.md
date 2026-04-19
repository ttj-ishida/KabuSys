CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
形式は「Keep a Changelog」に準拠します。

[Unreleased]: https://example.com/kabusys/compare/HEAD...v0.1.0

## [0.1.0] - 2026-04-19

Added
-----
- 基本アプリケーション骨組みを追加（初回リリース相当）。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。
- 起動スクリプト / 実行エントリを追加。
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（data/paper_trading.db のデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、ExecutionEngine のスレッド起動、停止フラグ（data/stop_requested.flag）検出による安全停止。
    - PID ファイル出力（data/execution.pid など）に対応。
  - 監視ループ起動スクリプト: src/kabusys/run_monitoring.py
    - SystemMonitor を用いたポーリングループを実装。デフォルトポーリング間隔 60 秒、環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（不正値はデフォルトにフォールバック）。
    - 監視は環境に依らず本番用 sqlite_path を使用する設計。
- 環境設定・検証用 CLI を追加。
  - 環境設定ウィザード: src/kabusys/config_setup.py
    - 対話式で .env を生成・更新するウィザードを実装（秘密値のマスク表示、デフォルト提示、保存確認）。
  - 設定検証ツール: src/kabusys/validate_config.py
    - 必須環境変数確認、KABUSYS_ENV/LOG_LEVEL 等の妥当性チェック、DB パス/設定ファイル存在確認、`--strict` オプションをサポート。
- 環境変数読み込みロジックを強化（src/kabusys/config.py）。
  - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を自動読み込み（OS 環境変数は保護）。
  - .env パーサを実装: export 構文、引用符エスケープ、インラインコメント処理などに対応。
  - 各種設定プロパティを提供（DB パス、PID/kill フラグ、paper_trading 用設定、しきい値等）。
  - PAPER_FILL_MODE の検証や KABUSYS_ENV/LOG_LEVEL の妥当性チェックを実装。
- ポートフォリオ構築モジュールを追加（純粋関数群）。
  - 候補選定と重み計算: src/kabusys/portfolio/portfolio_builder.py
    - select_candidates(), calc_equal_weights(), calc_score_weights()（スコア全ゼロ時に等金額にフォールバック）。
  - セクター制約・レジーム乗数: src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap()（既存保有を踏まえたセクター上限除外、unknown セクターは無視）、calc_regime_multiplier()（bull/neutral/bear マッピング、未知レジームはログ警告とフォールバック）。
  - 銘柄ごとの株数決定ロジック: src/kabusys/portfolio/position_sizing.py
    - risk_based / equal / score の allocation_method をサポート。lot_size（単元）丸め、per-stock 上限・aggregate cap スケーリング、cost_buffer を考慮した保守的見積り、残差処理による lot 単位の再配分を実装。
  - 上記をまとめて package export（src/kabusys/portfolio/__init__.py）。
- 監視・発注ログ用 DB 初期化呼び出しユーティリティを参照（init_monitoring_db を起動スクリプトで呼び出し、テーブル存在を保証）。
- ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
  - stdout 出力の StreamHandler（stdout を使用）と日次ローテーションする TimedRotatingFileHandler をルートロガーに設定。
  - LOG_DIR/LOG_LEVEL 解決順を実装。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
- プロセス優先度 / CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
  - Windows / POSIX の差分を吸収して set_process_priority(level)（high/normal/low）を実装。set_cpu_affinity() により先頭 N コアへ固定可能。psutil の例外（権限不足等）は警告でスキップ。
- Paper Trading 向け検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
  - 稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計・表示。しきい値を定義して PASS/FAIL 判定を出力。期間指定と DB パス指定の CLI オプションを提供。
- リサーチ（ファクター計算）基盤を追加（部分実装）。
  - src/kabusys/research/factor_research.py にモメンタム・MA200・ATR 等の計算方針と定数を追加（calc_momentum の実装が途中まで含まれる）。

Changed
-------
- なし（初回リリース）

Fixed
-----
- なし（初回リリース）

Security
--------
- なし

Notes / Implementation details
------------------------------
- 監視（monitoring）は KABUSYS_ENV に関係なく監視用 sqlite_path を用いる設計になっています（run_monitoring.py）。
- run_execution.py は paper_trading 環境時に paper_sqlite_path を使用し、本番 DB と完全分離するように配慮しています。
- .env の自動読み込みは必要に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能です（テスト用途を想定）。
- 未完成箇所:
  - research/factor_research.py の calc_momentum 実装が途中で切れているため、ファクター計算の完全実装は今後の作業になります。

関連ファイル（主要）
-------------------
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/config_setup.py
- src/kabusys/validate_config.py
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py
- src/kabusys/portfolio/*.py
- src/kabusys/utils/logging_setup.py
- src/kabusys/utils/process_priority.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/research/factor_research.py

今後の予定（提案）
-----------------
- factor_research の完全実装（DuckDB を用いたファクター計算の SQL 実装完了）。
- テストカバレッジ追加（ユニットテスト、CI）。
- Engine / Broker の統合テスト、Paper Trading のシミュレーション検証。