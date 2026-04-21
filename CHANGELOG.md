CHANGELOG
=========
All notable changes to this project will be documented in this file.
この CHANGELOG は "Keep a Changelog" の形式に準拠しています。
リリース日はパッケージの __version__ に基づきます。

フォーマット:
- Unreleased: 今後の変更（空の場合は省略可）
- 各リリースはバージョン番号と日付を記載

Unreleased
----------
（なし）

0.1.0 - 2026-04-21
-----------------
最初の公開リリース。以下の主要機能・CLI・ユーティリティを追加しました。

Added
- 基本アプリケーションとバージョン情報
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として追加。

- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。環境変数経由の設定取得、デフォルト値、バリデーションを提供。
  - 自動 .env ロード機能を実装。プロジェクトルートの検出（.git または pyproject.toml）を行い、.env → .env.local の順で読み込む。OS 環境変数は保護され上書きされない。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 設定で利用可能な主な環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABUSYS_ENV（development / paper_trading / live）
    - PAPER_FILL_MODE（paper_trading 時の挙動: instant / partial / never / reject）
    - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト: data/paper_trading.db）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（監視 DB のデフォルト: data/monitoring.db）
    - LOG_LEVEL, LOG_DIR, PID_FILE_PATH, KILL_FLAG_PATH など多数の設定をプロパティとして提供。

- 設定関連 CLI
  - 対話式設定ウィザード（src/kabusys/config_setup.py）を追加。.env の初期作成・更新を支援。使用例: python -m kabusys.config_setup
  - 設定検証ツール（src/kabusys/validate_config.py）を追加。必須環境変数や config/*.yaml の存在・パースチェックを実施。--strict オプションで警告をエラー扱いに可能。
  - validate_config は PyYAML が未インストールでも動作し、YAML 検証をスキップして警告を出力。

- 実行エンジンと監視
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を用いた停止制御に対応。
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視 DB は共通）。
    - 停止フラグ検知でループ終了。例外発生時はログ出力して次のポーリングへ継続。

- データベース & 分析基盤
  - DuckDB と SQLite を併用する設計。各起動スクリプトで duckdb / sqlite の接続を確立。
  - 監視テーブル初期化ユーティリティ（init_monitoring_db）を使用して冪等にテーブルを保証（両起動スクリプトで呼び出し）。

- ロギング / プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーへ設定。
    - ログディレクトリの自動作成。失敗時はファイル出力を無効化してコンソールのみで継続。
    - ログレベル解決順: 関数引数 > LOG_LEVEL 環境変数 > "INFO"。
  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows/Linux/macOS を透過して優先度を設定。set_cpu_affinity で最初の N コアにピン留め可能。
    - 権限不足や未対応環境では警告ログを出してスキップ。

- ポートフォリオ構築ライブラリ
  - 銘柄選定と重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N 件を選択。
    - calc_equal_weights, calc_score_weights を実装。スコアが全て 0 の場合は等配分にフォールバックして警告。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中上限 max_sector_pct を超える場合に当該セクターの新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: market_regime に基づく投下資金乗数（bull/neutral/bear を 1.0/0.7/0.3 にマップ）。未知レジームは 1.0 でフォールバックして警告。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応し、lot_size（単元）に丸めた発注株数を算出。
    - リスクベース算出、per-stock 上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer（手数料・スリッページ見積）対応、残差処理による追加配分ロジックを実装。

- Paper Trading 検証ツール
  - レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）を追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite から統計を集計。
    - 指標: 稼働率 (uptime), 注文成功率 (fill rate), 送信率 (send rate), P95 レイテンシ 等。
    - デフォルト閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）とし、PASS/FAIL 判定を出力。
    - 使用例:
      - python -m kabusys.tools.paper_verification_report
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- 研究用ファクター計算モジュール（骨格実装）
  - src/kabusys/research/factor_research.py を追加。DuckDB 接続を受け取り Momentum/Value/Volatility/Liquidity 等のファクターを計算する設計。
  - calc_momentum の実装を開始（関数のインターフェース、定数、設計方針を定義）。

Changed
- （初回リリースのため変更履歴はありません）

Fixed
- （初回リリースのため修正履歴はありません）

Notes / 注意事項
- 監視（run_monitoring.py）は KABUSYS_ENV に関係なく settings.sqlite_path（監視用本番パス）を使用します。監視 DB と発注 DB を意図的に分離したい場合は設定を見直してください。
- MONITOR_POLL_INTERVAL は環境変数でポーリング間隔（秒）を上書きできます。不正な値（非整数や 0 以下）は無視され、デフォルト 60 秒にフォールバックします。
- 起動時にプロセス優先度を "high" に設定しますが、権限が不足する環境では警告が出てスキップされます。
- .env ファイルはセキュリティ上 Git にコミットしないでください（config_setup でも同旨を注意喚起）。
- research/factor_research.py は今後の拡張対象です（calc_momentum 実装の続きや他ファクターの完全実装）。

既知の問題
- research/calc_momentum など一部研究用関数は実装途中の箇所が存在する可能性があります。研究モジュールは慎重に検証してから利用してください。
- price フォールバックに関する TODO が複数存在（price が欠損した場合の扱い等）。将来、前日終値などのフォールバックを追加予定。

開発者向けメモ
- 自動 .env ロードはテストなどで無効化可能: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- validate_config によって config/*.yaml の雛形生成 (scripts/generate_config.py) を案内しています。YAML のパースチェックには PyYAML が必要です。

以上。今後のリリースでは research モジュールの拡張、ExecutionEngine/Monitor の安定化（詳細なログやメトリクス追加）、Paper Trading の検証拡張を予定しています。