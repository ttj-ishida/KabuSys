# Changelog

すべての変更は「Keep a Changelog」仕様に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース

### Added
- 基本アプリケーション情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` として定義。

- 設定管理
  - .env 自動読み込み機構を実装（`src/kabusys/config.py`）。
    - プロジェクトルート（.git または pyproject.toml を探索）を基準に .env / .env.local を読み込む。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化対応。
    - 複雑な .env 行（export プレフィックス、シングル/ダブルクォート、エスケープ、コメント）に対応する堅牢なパーサ実装。
  - Settings クラスを実装し、環境変数から各種設定値を取得・バリデーションするプロパティを提供（DB パス、API トークン、env/log レベル判定、paper trading 用設定等）。
  - `settings` シングルトンインスタンスをエクスポート。

- 設定関連 CLI
  - 対話式環境設定ウィザード（`.env` の初期作成・更新）を追加（`src/kabusys/config_setup.py`）。
    - 秘匿項目のマスク表示、選択肢・デフォルトのサポート、保存の確認ダイアログを実装。
  - 起動前設定検証ツールを追加（`src/kabusys/validate_config.py`）。
    - 必須環境変数のチェック、KABUSYS_ENV の妥当性確認、ログレベルチェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および PyYAML があればパース検証、`--strict` オプションで警告を失敗扱いにできる。

- 実行・監視起動スクリプト
  - ExecutionEngine 起動スクリプト（`src/kabusys/run_execution.py`）。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite（デフォルト `data/paper_trading.db`）を使用して本番 DB と分離する挙動を実装。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動するフローを提供。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル管理（data/execution.pid）に対応。停止フラグ検知時に安全にエンジン停止。
  - SystemMonitor ポーリングループ起動スクリプト（`src/kabusys/run_monitoring.py`）。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - Monitoring は環境にかかわらず本番の sqlite_path を使用する（稼働状況一元管理）。
    - 停止フラグ検知、例外発生時のロギングと継続動作。

- 監視 DB 初期化ユーティリティ
  - `init_monitoring_db`（監視用テーブル等の冪等初期化）を呼び出す導線を追加（`run_*` スクリプトで使用）。

- Paper trading / Broker 分離
  - BrokerClientFactory（ブローカークライアント生成の抽象）により paper_trading 時は MockBrokerClient を利用し DB を分離する設計を導入（`run_execution` での利用に準備）。

- ロギング & プロセス管理ユーティリティ
  - 統一的なログ設定ユーティリティ `setup_logging` を実装（`src/kabusys/utils/logging_setup.py`）。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log）を設定。
    - LOG_DIR / LOG_LEVEL / 引数での上書き対応、ハンドラの重複防止（既存ハンドラをクリア）。
  - プロセス優先度・CPU affinity ユーティリティ `set_process_priority` / `set_cpu_affinity` を実装（`src/kabusys/utils/process_priority.py`）。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収する抽象化、アクセス権限エラー時は警告を出してスキップ。

- ポートフォリオ構築モジュール（純粋関数）
  - 銘柄選定と重み計算（`src/kabusys/portfolio/portfolio_builder.py`）
    - `select_candidates`, `calc_equal_weights`, `calc_score_weights` を実装。
    - スコアが全て 0 の場合は等金額配分へフォールバックして警告。
  - セクター制限とレジーム乗数（`src/kabusys/portfolio/risk_adjustment.py`）
    - `apply_sector_cap`：セクター集中上限に基づく候補除外（unknown セクターは除外しない）。
    - `calc_regime_multiplier`："bull"/"neutral"/"bear" に対する投下資金乗数。未知レジームは警告の上 1.0 にフォールバック。
  - ポジションサイジング（`src/kabusys/portfolio/position_sizing.py`）
    - `calc_position_sizes`：`risk_based` / `equal` / `score` の割当方式に対応。
    - lot_size（単元）考慮、1 銘柄上限、aggregate cap（利用可能現金に合わせたスケールダウン）、cost_buffer（手数料・スリッページ見積）に基づく安全な丸め・配分ロジックを実装。

- リサーチ（ファクター計算）基盤
  - DuckDB 接続を受け取るファクター計算モジュール（`src/kabusys/research/factor_research.py`）。
    - Momentum / MA200 / ATR / Value / Liquidity 等を計画する実装方針と定数を定義（関数群の骨格を含む）。（ファイルは一部省略あり）

- ペーパートレード検証ツール
  - Paper Trading 向け検証レポート生成スクリプト（`src/kabusys/tools/paper_verification_report.py`）。
    - システム安定性（稼働率）、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシ等を SQLite の paper_trading DB から集計してレポート出力。
    - Pass/Fail 判定閾値を定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - コマンドライン引数 `--from` / `--to` / `--db` をサポート。

- パッケージ構成
  - portfolio モジュールのエクスポート（`src/kabusys/portfolio/__init__.py`）により主要関数を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env の読み込みで発生しうる複雑なケース（クォート内のエスケープ、inline コメント等）に対するパーサ強化を実施。これにより .env 設定ミスによる起動エラーを低減。

### Security
- シークレット値（J-Quants トークン、kabu API パスワード、LINE トークン等）は Settings 経由で必須チェックを行い、config_setup は対話式でマスク表示。`.env` を Git にコミットしない旨を明示。

### Notes / Implementation details
- Monitoring は設計上「稼働監視」を目的としており、`run_monitoring` は環境に依存せず本番の sqlite パスを利用する点に注意。
- Execution は paper_trading 時に DB を完全に分離するため、paper 環境での検証が本番 DB に影響を与えないようになっている。
- 一部機能（ファクター計算の細部、ブローカークライアントの具象実装など）は別モジュール（execution/*, monitoring/*, data/* 等）に分割されており、本リリースでは呼び出し側の統合フローとユーティリティ群を提供。

もし CHANGELOG に追記してほしい差分や、リリース日付/バージョン命名の要望があれば教えてください。