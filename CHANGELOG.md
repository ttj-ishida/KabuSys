# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルは、主要な機能追加・変更点・修正点をリリース単位で記録します。

注: コードベースから推測して作成しています。実装の詳細は該当ソースを参照してください。

## [Unreleased]

（次回リリースに向けた未リリースの変更をここに記載します）

---

## [0.1.0] - 2026-04-19

Added
- 基本アプリケーション構成を追加
  - パッケージ名: `kabusys`。バージョンは `0.1.0` に設定。
- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動用スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全にループを終了。
    - 監視は環境（KABUSYS_ENV）に関係なく本番の `sqlite_path` を使用する設計。
  - run_execution: ExecutionEngine 起動用スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、`data/paper_trading.db` に記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定、停止フラグ・PID 管理を実装。
- 設定関連
  - `kabusys.config.Settings` を追加し、環境変数（.env）から各種設定を取得する統一インタフェースを提供。
    - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索し `.env` を自動読み込み（`.env.local` は上書き）。
    - `.env` の自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `PAPER_FILL_MODE` のバリデーション（有効値: "instant", "partial", "never", "reject"）。
    - データベースパス、PID/kill flag 周り、閾値などをプロパティとして提供。
- 設定ユーティリティ CLI
  - `validate_config` CLI を追加: .env と config/*.yaml の起動前検証を行う（`--strict` で警告も失敗扱い）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パース検証（PyYAML がない場合はスキップして警告）。
    - 本番環境用の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険設定検出）。
  - `config_setup` 対話ウィザードを追加: `.env` の初期作成・更新を対話的に支援。シークレット項目はマスク表示し、最終的に `.env` を保存。
- ログ・プロセスユーティリティ
  - `utils.logging_setup.setup_logging` を追加
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。
    - LOG_DIR が作成できない場合はファイル出力をスキップしてコンソール出力のみでフォールバック。
  - `utils.process_priority` を追加
    - `set_process_priority(level)` で Windows / POSIX を吸収してプロセス優先度を設定。
    - `set_cpu_affinity(cpu_count)` でカレントプロセスの CPU affinity を設定（可能な場合）。権限不足や未対応 OS では警告を出してフォールバック。
- ポートフォリオ構築（純粋関数群）
  - `portfolio.portfolio_builder`
    - buy シグナルの上位抽出（score 降順、signal_rank によるタイブレーク）。
    - 等金額配分 `calc_equal_weights`、スコア重み `calc_score_weights`（全スコアが 0 の場合は等比率へフォールバック）。
  - `portfolio.risk_adjustment`
    - セクター集中除外ロジック `apply_sector_cap`（既存ポジションからセクター別エクスポージャを計算し上限を超えるセクターの候補を除外）。
    - レジームに応じた投下倍率 `calc_regime_multiplier`（"bull"/"neutral"/"bear" をサポート、未知レジームは警告して 1.0 へフォールバック）。
  - `portfolio.position_sizing`
    - ポジションサイズ計算 `calc_position_sizes` を追加。
      - allocation_method: "risk_based" | "equal" | "score" をサポート。
      - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）によるスケールダウン。cost_buffer を考慮した保守的見積もり。
      - スケールダウン後に残余キャッシュで端数を lot_size 単位で補正するロジックを実装。
- Paper Trading 検証ツール
  - `tools.paper_verification_report` を追加
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）からの集計でシステム稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を算出して PASS/FAIL 判定を出力。
    - P95 計算実装、しきい値定義（稼働率 99%、成功率 90% 等）。
    - コマンドラインオプションで期間指定（--from/--to）と DB パス指定（--db）。
- 研究用モジュール（未完の一部を含む）
  - `research.factor_research` を追加（Momentum など複数ファクターの計算を想定、DuckDB 接続を受ける設計）。一部実装が途中まで存在。

Changed
- なし（初期リリースのため新規追加が中心）。

Fixed
- なし（初期リリースのため修正履歴なし）。

Notes / 実装上の注意
- run_monitoring は環境変数 KABUSYS_ENV に関わらず監視用 DB として Settings.sqlite_path（本番想定）を使用する仕様になっています。モニタリング DB を環境ごとに分離したい場合は設定や起動スクリプトを調整してください。
- run_execution は paper_trading 環境時に `paper_sqlite_path` を利用して本番 DB とデータ分離を行います。
- .env のパーサーは export プレフィックス、クォート（'"/バックスラッシュエスケープ）およびコメントをかなり柔軟に解釈しますが、複雑なエスケープや特殊ケースは想定外の振る舞いとなる可能性があります。
- logging_setup はログディレクトリ作成に失敗した場合、ファイル出力を行わず標準出力のみで継続します（実運用ではログディレクトリの権限設定を確認してください）。
- process_priority / set_cpu_affinity は実行環境の権限に依存します。権限がない場合は警告を出してスキップします。
- validate_config の YAML 検証は PyYAML に依存します。インストールされていない場合は YAML 検証をスキップして警告を表示します。
- portfolio モジュールは純粋関数として設計され、DB に依存しないため単体テストが容易です。将来的な拡張（銘柄別 lot_size 等）を想定した TODO コメントがあります。

詳しい利用方法や API（関数引数など）の仕様は各モジュールのドキュメント文字列（docstring）およびソースコードを参照してください。