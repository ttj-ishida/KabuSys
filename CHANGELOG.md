# Changelog

すべての変更は Keep a Changelog の形式に従って記載します。  
このファイルはコードベースから推測して生成したリリースノートです。

## [Unreleased]

- （現時点で手元のコードスナップショットはバージョン 0.1.0 の内容を含んでいます。次回リリース向けの差分はここに記載します。）

## [0.1.0] - 2026-04-18

初回公開リリース（推測） — 日本株自動売買フレームワークの基本機能を実装。

### Added
- 全体
  - パッケージの初期バージョンを `__version__ = "0.1.0"` として導入。
  - DuckDB と SQLite を組み合わせたデータ基盤を採用（duckdb/SQLite ファイルパスを設定可能）。
  - .env 自動読み込み機構を実装（プロジェクトルートを .git / pyproject.toml で検出）。
  - 環境変数読み書きの CLI ウィザード `kabusys.config_setup` を追加（対話式で .env を生成・更新）。
  - 設定検証 CLI `kabusys.validate_config` を追加（必須環境変数、パス、YAML ファイルの存在/パース等をチェック）。
  - ログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を追加。コンソール（stdout）と日次ローテーションファイル（TimedRotatingFileHandler）を統一設定。
  - プロセス優先度設定ユーティリティ `kabusys.utils.process_priority` を追加。Windows / POSIX を吸収して優先度（high/normal/low）と CPU affinity を設定可能。
  - Execution エンジン起動スクリプト `run_execution.py` を追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper-trading SQLite DB（data/paper_trading.db を想定）を使用して本番 DB と分離する設計。
    - BrokerClientFactory によるブローカークライアント抽象化を導入（実運用/モックの切替え想定）。
    - 実行中の PID ファイル管理、停止フラグ（data/stop_requested.flag）によるグレースフルな停止処理に対応。
    - RiskManager / OrderManager / Reconciler を組み合わせた ExecutionEngine を起動。
  - Monitoring 起動スクリプト `run_monitoring.py` を追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用（状態監視テーブルの初期化を行う）。
    - 停止フラグ検知・例外を捕捉してポーリング継続する耐障害性を実装。
  - Paper Trading の検証レポート生成ツール `kabusys.tools.paper_verification_report` を追加。
    - 稼働率、注文成功率、送信率、レイテンシ（P95）などの指標を計算し PASS/FAIL 判定を表示。
    - デフォルト DB は `data/paper_trading.db`。オプションで期間・DB を指定可能。
  - ポートフォリオ構築モジュール `kabusys.portfolio` を追加（純粋関数群）。
    - 候補選定: select_candidates（スコア降順、タイブレークに signal_rank）。
    - 重み算出: calc_equal_weights（等金額）、calc_score_weights（スコア比率、スコア合計が 0 の場合は等金額にフォールバック）。
    - リスク調整: apply_sector_cap（セクター集中上限による候補除外。unknown セクターは除外しない）、calc_regime_multiplier（レジームに応じた投下資金乗数）。
    - 口数決定: calc_position_sizes（risk_based / equal / score に対応、lot_size（単元）丸め、aggregate cap のスケールダウン、cost_buffer を用いた保守的推計）。
  - 研究用モジュール `kabusys.research.factor_research`（ファクター計算基盤の骨格）を追加。Momentum / ATR 等の計算方針を実装する設計になっている（DuckDB を利用）。
  - 設定 API `kabusys.config.Settings` を導入。
    - J-Quants / kabu ステーション / LINE / DB パス / 監視しきい値 / 環境種別 等のプロパティを提供。
    - `paper_fill_mode`（PAPER_FILL_MODE）を導入し、paper_trading 時の執行挙動（instant/partial/never/reject）を管理。
    - `paper_sqlite_path`（PAPER_TRADING_SQLITE_PATH）で paper_trading 用 DB を分離可能。
    - env 判定（development/paper_trading/live）とログレベル妥当性チェックを実装。
  - 監視用 DB 初期化ユーティリティ（init_monitoring_db への呼び出し箇所が複数）を統一的に使用。
  - .env パーサー: クォート内のバックスラッシュエスケープ対応、"export " プレフィックス対応、インラインコメント扱いの仕様（直前がスペース/タブの '#' をコメントとみなす）など堅牢化。

### Changed
- ロギング
  - StreamHandler を stdout に出力するように明示（cron/Task Scheduler 等で stdout/stderr をリダイレクトする運用を想定）。
  - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続するフェイルセーフを追加。
- .env 自動ロード
  - OS 環境変数を保護するための protected キーセットを導入し、.env.local が OS 環境を上書きする際の保護動作を明確化。
  - プロジェクトルートが特定できない場合は自動ロードをスキップするように変更（パッケージ配布後の安全性向上）。
- Execution / Monitoring
  - 監視スクリプトは MONITOR_POLL_INTERVAL の 0 以下の不正値を検出しデフォルトにフォールバックする安全弁を追加。
  - ExecutionEngine の起動フローを明確化（停止フラグ検査、スレッド起動→停止フラグで Engine.stop() 実行 → join）。
- ポートフォリオ・ポジションサイズ
  - aggregate cap 適用時のスケーリングロジックを追加（小数端数の分配に残差（fractional_remainder）順で lot 単位の補正）。
  - 価格欠損（0 または None）の場合は該当銘柄をスキップしてログにデバッグ情報を出力。

### Fixed
- .env 読み込み時のエラー報告を警告（warnings.warn）にて出力するようにし、読み込み失敗時も処理を継続するように改善。
- process_priority のプラットフォーム差分での Import / 定数未定義時の例外を回避するため getattr を利用してフォールバックする実装に修正。
- validate_config: YAML 検証のための PyYAML 未インストール判定を行い、未インストール時は YAML 検証をスキップして警告を出すように変更（依存性がない環境でも CLI を実行可能に）。

### Security
- .env ファイル生成テンプレートに「.env は絶対に Git にコミットしないこと」の注意を明記。

### Documentation / UX
- config_setup の対話ウィザードでシークレット項目をマスク表示、Enter で既存値再利用、入力のキャンセル（EOF/KeyboardInterrupt）を安全に扱う UI を提供。
- validate_config の `--strict` オプションを追加（警告を FAIL 扱いにできる）。
- paper_verification_report にコマンドラインオプション（--from/--to/--db）を追加し、期間や DB を指定可能にした。

### Notes / Known limitations
- research.factor_research の一部実装は骨格（コメント・定数・API）まで実装されているが、関数の途中や未完の箇所がある可能性がある（本スナップショットは途中で切れている箇所が確認される）。
- position_sizing 等で価格が欠損（0.0）だとエクスポージャーが過小見積もられる点は TODO コメントで将来拡張（前日終値等のフォールバック）を示している。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム未対応の際は警告を出して処理をスキップする。運用環境によっては期待する効果が得られない場合がある。
- Monitoring は「環境にかかわらず本番 sqlite_path を使用する」設計となっているため、テスト時は注意が必要。

---

この CHANGELOG はコードベースの静的解析およびコメントから推測して作成しています。実際のコミット履歴がある場合はそちらに基づく正確な差分ログへの置換を推奨します。