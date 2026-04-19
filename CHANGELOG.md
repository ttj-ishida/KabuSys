CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and the entries are
in Japanese. Semantic Versioning を採用しています。

Unreleased
---------

- （なし）

0.1.0 - 2026-04-19
-----------------

Added
- 初回リリースを追加。
- 実行用エントリスクリプト:
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の MockBrokerClient と
      data/paper_trading.db を使用して本番 DB と完全に分離する挙動を実装。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。
    - 停止フラグ (data/stop_requested.flag) の監視、実行中スレッドの安全な停止、
      execution.pid に PID を記録する仕組みを実装。
    - RiskConfig のデフォルトパラメータ（max_position_pct、max_utilization、rate_limit_per_sec、
      circuit_breaker 等）を設定し、broker.get_available_cash() を初期ポートフォリオ値として使用。

  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV に依存しない）。
    - 停止フラグ (data/stop_requested.flag) 検出でループを終了。例外はログにトレースして次ポーリングへ継続。

- 設定管理・検証・ウィザード:
  - src/kabusys/config.py
    - .env 自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env/.env.local の読み込み順、OS 環境変数を保護する仕組みを実装。
    - .env パースの強化（export プレフィックスの対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い）。
    - Settings クラスを提供し、各種設定値（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、
      PAPER_FILL_MODE（バリデーションあり）、PAPER_TRADING_SQLITE_PATH、各種閾値、KABUSYS_ENV/LOG_LEVEL の検証）をプロパティで取得可能に。

  - src/kabusys/validate_config.py
    - 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、
      config/*.yaml の存在と YAML パースチェック（PyYAML 未導入時は警告）を実装。
    - --strict オプションで警告も失敗扱いにできる。

  - src/kabusys/config_setup.py
    - 対話式 .env 作成ウィザードを追加。
    - J-Quants / kabu ステーション / DB / ログ / Kill Switch 等の主要設定項目を対話で入力・保存可能。

- ポートフォリオ構築モジュール:
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバックし WARNING を出力。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を実行する apply_sector_cap を実装。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をサポート、未知はフォールバック）。

  - src/kabusys/portfolio/position_sizing.py
    - allocation_method に応じた発注株数計算 calc_position_sizes を実装。
    - risk_based / equal / score の各方式をサポートし、lot_size（単元）丸め、aggregate cap によるスケール調整、
      cost_buffer（手数料・スリッページ見積り）を考慮したロジックを搭載。

- ユーティリティ:
  - src/kabusys/utils/logging_setup.py
    - 標準化されたロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app>.log）を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベル・ログディレクトリの解決優先順を定義。

  - src/kabusys/utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定を行うユーティリティを追加。
    - CPU affinity を設定する set_cpu_affinity を提供。
    - psutil の権限不足や未実装例外を安全にハンドリングし、失敗時は警告を出力してスキップ。

- レポーティング / 検証ツール:
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレーディング検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計・判定し PASS/FAIL を出力。
    - CLI オプション --from/--to/--db をサポート。PAPER_TRADING_SQLITE_PATH 環境変数で DB パスを指定可能。
    - P95 計算や各種安全対策（DB が存在しない / テーブルがない場合のフォールバック）を実装。

- 研究用ファクターモジュール（一部実装）:
  - src/kabusys/research/factor_research.py
    - モメンタム等のファクター計算モジュールの骨組みを追加（DuckDB 接続を受け、prices_daily 等を参照してファクターを算出する設計）。
    - （ファイル末尾の関数が途中まで含まれています。以降の実装は今後の拡張を想定。）

Changed
- パッケージのバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

Fixed
- （初期リリースのため該当なし）

Security
- 環境変数ファイル (.env) は Git にコミットしないよう README/警告を .env 生成時に明示（config_setup がファイルヘッダーに警告を記載）。

Notes / Implementation details
- .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- PAPER_FILL_MODE の値検証や KABUSYS_ENV / LOG_LEVEL の値検証により、誤設定を早期に検出する設計。
- 多くの IO 操作（ログディレクトリ作成、DB パスの親ディレクトリ存在チェックなど）に対してフォールバックや警告を用意し、起動の堅牢性を重視。

Acknowledgements
- 初期設計は複数のサブモジュール（監視・実行・ポートフォリオ構築・ユーティリティ・検証ツール）を含むモノリポジトリ形式で構築されています。今後のリリースで API 仕様の明確化、ユニットテスト、ドキュメント整備（PortfolioConstruction.md 等の参照に基づく実装追従）を進めます。