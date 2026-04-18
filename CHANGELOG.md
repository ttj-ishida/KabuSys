# CHANGELOG

All notable changes to this project will be documented in this file.
フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーションパッケージを追加。
  - パッケージバージョン: `__version__ = "0.1.0"`
- 設定管理
  - 環境変数および .env/.env.local の自動読み込み（プロジェクトルート検出）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロード無効化可能。
  - robust な .env パーサ (`kabusys.config._parse_env_line`) を実装（クォート/エスケープ/コメント対応、`export KEY=val` 形式対応）。
  - Settings クラスを追加し、J-Quants / kabuステーション / DB / 監視 / システム設定等をプロパティで取得可能。
  - Paper Trading 用設定（`PAPER_TRADING_SQLITE_PATH`, `PAPER_FILL_MODE` 等）をサポート。
- 環境セットアップ & 検証 CLI
  - 対話式ウィザード `kabusys.config_setup`（`.env` の作成・更新を支援）。
  - 設定検証ツール `kabusys.validate_config`（必須環境変数、KABUSYS_ENV 検証、DB パス・config YAML の存在チェック、production 用ガードチェック等）。`--strict` で警告を失敗扱いにできる。
- 実行 / 監視ランナー
  - `run_execution.py`: ExecutionEngine 起動スクリプト。`KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を用い、paper_trading 用 SQLite（デフォルト `data/paper_trading.db`）に記録して本番 DB と分離する。
  - `run_monitoring.py`: SystemMonitor のポーリングループ起動スクリプト。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。監視用 DB 初期化を保証。
  - 両スクリプトとも停止フラグファイル（`data/stop_requested.flag` など）を検知して安全に停止する仕組みを持つ。Execution は `data/execution.pid` に PID を出力する想定。
- ロギング & プロセスユーティリティ
  - 統一的ログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト `logs/<app_name>.log`、30 日分保持）を設定。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続。
  - プロセス優先度・CPU affinity 設定ユーティリティ `kabusys.utils.process_priority` を追加（Windows/Linux/macOS 等を吸収）。`set_process_priority("high"|"normal"|"low")`、`set_cpu_affinity(n)` を提供。権限不足や未サポート環境では警告を出してスキップ。
- ポートフォリオ構築モジュール（純粋関数群、DB 非依存）
  - 候補選定 / 重み計算: `select_candidates`, `calc_equal_weights`, `calc_score_weights`（スコア合計が 0 の場合は等配分にフォールバックして警告）。
  - セクター集中制限 / レジーム乗数: `apply_sector_cap`, `calc_regime_multiplier`（"bull"/"neutral"/"bear" をマップ、未知レジームはフォールバックして警告）。
  - ポジションサイジング: `calc_position_sizes`（`risk_based`, `equal`, `score` の各方式をサポート、単元（lot_size）で丸め、aggregate cap によりスケーリング、cost_buffer を考慮した保守的見積り。残差を lot 単位で配分するアルゴリズムを実装）。
- リサーチ / ファクター計算
  - DuckDB 接続を受け取り価格・財務テーブルからファクターを計算するための骨組みを実装（モメンタムや ATR 等の定義・スキャン長を含む）。（注: 実装ファイル `kabusys.research.factor_research` に計算関数の一部が含まれる）
- ツール
  - Paper Trading 検証レポート生成スクリプト `kabusys.tools.paper_verification_report` を追加。
    - 稼働率、注文成功率、送信率、API レイテンシ（平均/最大/P95）などを算出し PASS/FAIL 判定（デフォルト閾値: 稼働率 >=99%、成功率/送信率 >=90%/95%、P95 <=200ms）。
    - 日付フィルタ（--from/--to）および --db オプションをサポート。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Known issues / Notes / TODO
- risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価等のフォールバックを用いることが TODO コメントに記載されている。
- position_sizing.calc_position_sizes:
  - 将来的に銘柄ごとの単元株数 (lot_size) をサポートするための拡張（stocks マスタに lot_size を持たせる等）が TODO。
- research.factor_research:
  - ソース中に処理が途中で切れている箇所が存在（ファイル末尾の関数実装断片）。追加の実装が必要。
- ログディレクトリ作成やプロセス優先度設定は環境により失敗することがある。失敗時は警告を出してフォールバック（ファイル出力の無効化や処理スキップ）する設計。
- run_monitoring は「監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」する仕様になっている点に注意（意図的な設計）。paper_trading 実行ロジックは run_execution 側で専用 DB を使うことで分離している。
- .env パーサは多くのケースに対応しているが、非常に特殊なフォーマットの .env 行は想定外の動作をする可能性あり。

### CLI / 使い方のまとめ
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

今後のリリースでは、research モジュールの完了、各種 TODO の解消、および追加のテスト／ドキュメント整備を予定しています。