# Changelog

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」準拠です。主にコードベース（src/）の現状から推測して記載しています。

すべての非破壊的な変更は将来のリリースで Unreleased セクションへ移動してください。

## [Unreleased]

- なし（初期リリース）

## [0.1.0] - 2026-04-20

初期公開リリース。システム全体の起動スクリプト、設定管理、検証ツール、ポートフォリオ構築ユーティリティ、発注エンジン起動周り、監視機能、各種ユーティリティ、およびペーパートレード検証レポート等を実装しています。

### Added

- 基本的なパッケージ構成を導入
  - パッケージ名: `kabusys`
  - バージョン: `0.1.0`（src/kabusys/__init__.py）

- 起動スクリプト
  - 実行エンジン起動スクリプト: `src/kabusys/run_execution.py`
    - KABUSYS_ENV により paper_trading 時は MockBrokerClient を使用して本番 DB と分離（デフォルトで `data/paper_trading.db`）。
    - スレッドで ExecutionEngine を起動し、`data/stop_requested.flag` による停止要求を監視。
    - 起動時にプロセス優先度を "high" に設定。
    - SQLite / DuckDB への接続管理とクリーンなクローズ処理。
  - 監視ループ起動スクリプト: `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループを提供。
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔上書き可能（デフォルト 60 秒）。
    - 停止フラグ検知でループを終了。
    - 監視 DB は環境に関わらず本番 sqlite_path を使用する設計（明示的に本番の監視を記録する挙動）。

- 設定管理
  - Settings クラス: `src/kabusys/config.py`
    - 環境変数をラップ。プロパティベースで各種設定を取得。
    - .env 自動読み込み機能を実装（プロジェクトルートの判定: `.git` または `pyproject.toml`）。
    - 読み込み順: OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロード無効化可能。
    - `.env` パースはクォート、エスケープ、インラインコメント等を考慮する堅牢な実装。
    - Paper Trading 関連設定（`PAPER_FILL_MODE`, `PAPER_TRADING_SQLITE_PATH`）をサポート。
    - 監視閾値（CPU/MEM/DISK）や PID / kill flag のパス等をプロパティで提供。

- 設定ウィザード / 検証
  - .env 対話式ウィザード: `src/kabusys/config_setup.py`
    - 対話形式で .env の作成・更新を支援。シークレット値はマスク表示。
    - 標準的な環境項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を定義。
  - 設定検証 CLI: `src/kabusys/validate_config.py`
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスや config/*.yaml の存在と YAML パース（PyYAML がインストールされていない場合はスキップ）を実施。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定 / 重み計算: `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定（score 降順、signal_rank によるタイブレーク）
    - 等金額配分、スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）
  - セクター集中制限・レジーム乗数: `src/kabusys/portfolio/risk_adjustment.py`
    - apply_sector_cap: 既存保有を考慮してセクター上限（max_sector_pct）を超える場合に新規候補を除外。`unknown` セクターは上限チェック対象外。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に対する乗数を返す（未知レジームは 1.0 でフォールバックし警告を出力）。
  - ポジションサイズ計算: `src/kabusys/portfolio/position_sizing.py`
    - allocation_method: `risk_based` / `equal` / `score` をサポート。
    - lot_size（単元株）丸め、1 銘柄上限（max_position_pct）、利用可能現金による aggregate cap、cost_buffer による保守的見積り、スケールダウンと残差の再配分ロジックを実装。

- Execution 関連コンポーネント組み立て（起動時）
  - BrokerClientFactory を経由したブローカークライアント生成（paper/live により分岐）
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の統合と起動フローを実装。
  - RiskManager のデフォルト設定例を Execution 起動時に指定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5 等）。

- 監視 DB 初期化ユーティリティ
  - monitoring_db の初期化関数 init_monitoring_db を起動シーケンスで呼び出し、監視テーブル存在を保証（冪等）。

- ロギングとプロセス優先度ユーティリティ
  - ログ設定ユーティリティ: `src/kabusys/utils/logging_setup.py`
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保存）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）を考慮。
  - プロセス優先度 / CPU affinity ユーティリティ: `src/kabusys/utils/process_priority.py`
    - Windows と POSIX を吸収して nice / priority を設定。エラー時は警告を出力してスキップ。
    - set_cpu_affinity を提供（利用可能なコア数チェック、例外ハンドリングあり）。

- ペーパートレード検証レポートツール
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading の SQLite データ (`data/paper_trading.db` デフォルト) からレポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
    - 合格基準（デフォルト）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタオプション（--from / --to）、--db で DB パス上書き可能。
    - P95 計算、欠損値の扱い（N/A 表示）を実装。

- リサーチ（ファクター計算）の土台
  - `src/kabusys/research/factor_research.py` にてモメンタムや移動平均、ATR 等を計算するためのスケルトンと定数群を実装。DuckDB 経由で prices_daily 等のテーブルを参照する設計。

### Changed

- （初版のため該当なし）  
  - 将来のリリースでの API 変更に備えて、各モジュールは純粋関数（ポートフォリオ等）と副作用のある起動処理（run_*）を明確に分離しています。

### Fixed

- （実装段階で意図的に対処済みと推測される点）
  - .env のパースでクォート・エスケープ・コメント処理に対応し、一般的な .env 書式による誤解釈を低減。
  - ロギング設定時、ログディレクトリ作成失敗時に落ちないようにしてコンソールログにフォールバック。

### Notes / Other

- 監視（monitoring）は「環境にかかわらず本番 sqlite_path を使う」仕様になっているため、開発環境で監視データを別 DB に分離したい場合は sqlite_path を上書きするか、monitoring の起動ロジックを調整してください。
- Paper Trading では DB を完全分離する設計になっており、誤って本番に影響を与えないよう配慮されています。
- 一部モジュール（研究系のファイル等）は今後さらに実装が追加される想定です（例: factor_research の残り実装）。

### Security

- .env を生成するスクリプト（config_setup）は `.env` を絶対に Git にコミットしないことを README/コメントで明示しているため、シークレット管理には注意してください。
- 環境変数読み込みでは OS 環境変数を保護する仕組み（protected set）を導入しています。

---

（この CHANGELOG は提示されたコード内容から推測して作成しています。実際のコミット履歴や開発ログに基づく正確な差分記録が必要な場合は、git の履歴から CHANGELOG を生成することを推奨します。）