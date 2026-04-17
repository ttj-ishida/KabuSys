# CHANGELOG

すべての注記は Keep a Changelog の形式に準拠しています。  
このファイルは、コードベースから推測できる機能追加・変更点・修正点をまとめたものです。

履歴フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

## [Unreleased]

## [0.1.0] - 2026-04-17

### Added
- 基本アプリケーションパッケージ `kabusys` を初期リリース。
  - バージョン: `__version__ = "0.1.0"`。
- 環境設定 / ユーティリティ
  - Settings クラス (`kabusys.config.Settings`) による環境変数ベースの設定管理を実装。
    - 自動 .env 読み込み機能（プロジェクトルートの検出: `.git` または `pyproject.toml` を基準）。
    - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 主要な設定項目:
      - J-Quants, kabuステーション API（`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `KABU_API_BASE_URL`）
      - データベースパス（`DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH`）
      - Paper Trading の挙動（`PAPER_FILL_MODE`）
      - 監視/プロセス制御（`PID_FILE_PATH`, `KILL_FLAG_PATH`, `KILL_FLAG_CLEAR_ON_START`）
      - システム閾値（`CPU_THRESHOLD_PCT`, `MEMORY_THRESHOLD_PCT`, `DISK_THRESHOLD_PCT`）
      - 実行環境識別（`KABUSYS_ENV`: `development`/`paper_trading`/`live`）
- .env 対話式ウィザード CLI
  - `kabusys.config_setup` により `.env` の初期作成・更新を対話的に支援。
  - 主要項目のプロンプト、既存値の再利用、シークレット値のマスク表示、ファイル書き込み機能を提供。
- 設定検証 CLI
  - `kabusys.validate_config` により起動前に環境変数や `config/*.yaml` の存在・簡易整合性を検証。
  - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベルの妥当性、DB パスの親ディレクトリチェック、YAML のパース検証（PyYAML が存在する場合）、本番環境向けの追加ガードを実装。
  - `--strict` オプションで警告を失敗扱いにできる。
- 実行 & 監視用起動スクリプト
  - `kabusys.run_execution`:
    - ExecutionEngine 起動スクリプト。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を用い、Paper Trading 用 DB（`data/paper_trading.db` デフォルト）を使用して本番 DB から分離。
    - 停止制御: プロジェクト内 `data/stop_requested.flag` を監視し、安全に停止。
    - 実行時 PID ファイル (`data/execution.pid`) 出力をサポート。
    - 依存コンポーネント（BrokerFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）の組み立ておよびセッションスレッド管理を実装。
  - `kabusys.run_monitoring`:
    - SystemMonitor ポーリングループの起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして安全に処理。
    - 監視は環境にかかわらず本番 sqlite_path（`Settings.sqlite_path`）を使用する設計。
    - 停止フラグ検知でループ終了。
- モニタリング DB 初期化ユーティリティ（`kabusys.monitoring.monitoring_db.init_monitoring_db` を各スクリプトで呼び出し、監視テーブルの存在を保証）
- プロセス管理ユーティリティ
  - `kabusys.utils.process_priority`:
    - プラットフォーム差を吸収するプロセス優先度設定 (`set_process_priority`)。
    - CPU affinity 固定機能 (`set_cpu_affinity`)。
    - Windows / POSIX の適切なフォールバックとエラーハンドリング（アクセス権不足を警告してスキップ）。
- Portfolio 構築モジュール
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 (`select_candidates`)、等金額配分 (`calc_equal_weights`)、スコア加重配分 (`calc_score_weights`) を実装。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限適用 (`apply_sector_cap`)。
    - 市場レジームに応じた投下資金乗数 (`calc_regime_multiplier`)。
  - `kabusys.portfolio.position_sizing`:
    - 株数算出ロジック (`calc_position_sizes`)。リスクベース/等分/スコアベースの配分、単元株丸め、aggregate cap スケーリング、コストバッファ考慮などを実装。
- リサーチ / ファクター計算
  - `kabusys.research.factor_research`:
    - DuckDB の prices_daily / raw_financials を用いたモメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR）、流動性指標等の計算実装。
    - SQL とウィンドウ関数を組み合わせた実装で大量データ処理を想定。
- ツール: Paper Trading 検証レポート
  - `kabusys.tools.paper_verification_report`:
    - ペーパートレード用 SQLite DB を解析して、稼働率、注文成功率、送信率、P95 レイテンシ等を算出する CLI ツールを提供。
    - デフォルト基準値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）による PASS/FAIL 判定を出力。
    - `--from` / `--to` / `--db` オプションをサポート。
- パッケージエクスポート
  - `kabusys.portfolio.__init__` で主要関数をまとめてエクスポート。

### Changed
- .env 読み込みの堅牢化
  - `_parse_env_line` においてシングル/ダブルクォート内のエスケープ処理、コメント判定ロジック、`export KEY=val` 形式のサポートを追加し、より実用的な .env パースを実現。
  - `.env.local` を `.env` 上書きとして読み込む際、OS 環境変数を保護する仕組み（protected set）を導入。
- DB パスの既定値と振る舞いを明確化
  - `DUCKDB_PATH` と `SQLITE_PATH` のデフォルトを `data/kabusys.duckdb` / `data/monitoring.db` として一貫化。
  - `run_execution` は `paper_trading` 環境時に `PAPER_TRADING_SQLITE_PATH` を使用して本番 DB と分離。

### Fixed
- ポーリング間隔の安全なフォールバック
  - `MONITOR_POLL_INTERVAL` に不正（非数値や 0 以下）が与えられても、ログ警告を出してデフォルト 60 秒にフォールバックするように修正。
- DuckDB / SQLite の接続ライフサイクルの明確化
  - 起動スクリプトでの接続閉鎖を finally ブロックで保証（例: run_monitoring/run_execution）。

### Deprecated
- なし（初期リリース）

### Removed
- なし（初期リリース）

### Security
- 本番稼働時の注意喚起を実装
  - `validate_config` に本番環境 (`KABUSYS_ENV=live`) 向けのガードを追加（LINE通知設定の未設定、`KILL_FLAG_CLEAR_ON_START` の危険設定の警告など）。
- シークレット値の取り扱い
  - `config_setup` の表示ではシークレット項目をマスクして表示（.env に直接書き込む際の注意を明記）。

---

注記:
- 上記はソースコードの現在の実装内容から推測して作成した変更履歴です。実際のリリース手続きやリリースノートでは、テスト状況、既知の制限、マイグレーション手順などを併記することを推奨します。