# Changelog

すべての重要な変更を記録します。  
このファイルはソースコード（src/配下）の内容から推測して作成しています。実際のコミット履歴と差異がある可能性があります。

フォーマット: Keep a Changelog 準拠

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-18
初回リリース（コードベースから推測してまとめた主要な機能群と改善点）。

### Added
- 基本的なアプリケーション構成と起動スクリプトを追加
  - 実行エンジン起動スクリプト: `src/kabusys/run_execution.py`
    - KABUSYS_ENV が `paper_trading` のときは paper 専用 SQLite（data/paper_trading.db）を使用し、MockBrokerClient を介した分離されたテスト実行をサポート。
    - エンジンの PID 管理（`data/execution.pid`）と停止フラグ（`data/stop_requested.flag`）による安全停止対応。
    - ExecutionEngine を別スレッドで実行し、停止フラグ検知で安全に停止するループを実装。
  - 監視ループ起動スクリプト: `src/kabusys/run_monitoring.py`
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用して起動する実装（監視専用 DB 初期化呼び出しを含む）。
- 環境設定管理
  - `.env` 自動読み込み機能（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）を実装（`src/kabusys/config.py`）。
  - `.env` のパースは引用符付き値、エスケープ、インラインコメント、`export KEY=...` 形式に対応。
  - `Settings` クラスを提供し、アプリで必要な設定値（DB パス、API トークン、閾値、環境種別等）をプロパティ経由で取得可能。
- 環境設定ウィザード CLI: `src/kabusys/config_setup.py`
  - 対話式で `.env` を作成/更新するウィザードを提供。
  - 既存値の読み込み、シークレットマスク表示、保存前確認などのユーザーフレンドリな UX を実装。
- 設定検証 CLI: `src/kabusys/validate_config.py`
  - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL 等の妥当性チェック、DB パスや config/*.yaml の存在チェックを実装。
  - `--strict` オプションで警告を失敗扱いにできる。
- ロギングユーティリティ: `src/kabusys/utils/logging_setup.py`
  - コンソール（stdout）出力と日次ローテートのファイル出力を統一的に設定する `setup_logging()` を追加。
  - ログ出力ディレクトリの自動作成、作成失敗時のフォールバック（コンソールのみ）を実装。
- プロセス優先度 / CPU affinity ユーティリティ: `src/kabusys/utils/process_priority.py`
  - Windows / POSIX の差分を吸収してプロセス優先度を設定する `set_process_priority()` を実装。
  - `set_cpu_affinity()` により最初の N コアにピン留めする機能を提供（未指定時は変更しない）。
  - 権限不足などで設定に失敗した場合は警告ログでスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - 候補選定・配分: `src/kabusys/portfolio/portfolio_builder.py`
    - シグナルのソート、等金額／スコア加重配分ロジックを実装。
  - セクター制約・レジーム乗数: `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中上限チェック（既存保有を考慮）とレジームに応じた投下比率乗数を実装。
  - 発注株数決定・リスク制限: `src/kabusys/portfolio/position_sizing.py`
    - risk_based / equal / score の割当方式、単元株丸め、aggregate cap によるスケーリングロジックを実装。
- 研究用ファクター計算モジュール（骨格）: `src/kabusys/research/factor_research.py`
  - モメンタム（1M/3M/6M）、MA200乖離、ATR、流動性などを計算する設計方針と定数群を導入。
  - DuckDB 接続を受けて prices_daily / raw_financials を参照する想定。
- Paper Trading 検証レポート: `src/kabusys/tools/paper_verification_report.py`
  - paper_trading DB を参照して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数を集計・判定する CLI。
  - 合否判定基準（稼働率 99%、Fill 90%、Send 95%、P95 ≤ 200ms）を定義。
- パッケージ情報: `src/kabusys/__init__.py` にバージョン `0.1.0` を追加。

### Changed
- DB 周りの分離設計
  - 実行（Execution）は paper_trading モード時に専用 SQLite を使うことで本番 DB と完全分離する設計を採用。
  - 監視（Monitoring）は常に監視用 sqlite_path を使う仕様（一貫した監視データ保存先）。
- ログ設定の既定挙動を明確化
  - 環境変数 `LOG_LEVEL` / `LOG_DIR` を尊重し、ファイル出力に失敗した場合はコンソール出力のみで継続。
- .env 自動ロードの安全性向上
  - OS 環境変数を保護する `protected` 機構を導入し、`.env.local` の上書き処理等を制御。

### Fixed
- 環境変数パースの堅牢化
  - `_parse_env_line()` が引用符・エスケープ・コメントを正しく処理するよう改善（複雑な .env の値にも対応）。
- ポーリング間隔の不正値対策
  - `MONITOR_POLL_INTERVAL` が 0 以下や数値以外のときにデフォルトへフォールバックするロジックを追加し、`time.sleep` に渡す不正値による例外発生を防止。
- リソースクリーンアップ強化
  - 起動スクリプトで DB 接続（sqlite3 / duckdb）を finally で必ずクローズするようにしてリソースリークを防止。
- 監視 DB 初期化の冪等性
  - `init_monitoring_db()` を起動時に呼び出して監視テーブルの存在を保証（既に存在する場合は問題なくスキップ）。
- ExecutionEngine の停止/タイムアウト処理の堅牢化
  - スレッド終了待ちや停止フラグ検知時のエンジン停止処理、最大 join timeout の設定などで安全停止を強化。

### Security
- 秘密情報の扱い
  - 設定ウィザードおよび .env の取り扱いに関して README 等で `.env` をコミットしない旨を注記するテンプレートを生成（`config_setup.py` の出力コメントに記載）。

### Notes / Implementation details
- 多くの CLI やユーティリティは docstring に使い方が記載されており、運用ガイドに沿った使い方を想定している。
- 一部モジュール（research 等）は計算ロジックの骨格が中心で、一部未実装箇所（コメントや TODO）を含む可能性がある。
- 実際の外部依存（kabu ステーション、J-Quants、psutil、duckdb、PyYAML 等）はランタイムで必要。`validate_config` は PyYAML 未インストール時に YAML チェックをスキップする処理を含む。

---

メンテナンスやリリース履歴の正確な反映には実際のコミットログ（git HISTORY）が必要です。本 CHANGELOG はコード内容からの推測に基づく要約である点をご承知ください。必要ならば、リポジトリのコミット履歴を元に正式な CHANGELOG を生成するお手伝いをします。