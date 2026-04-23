# Changelog

すべての重要な変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。セマンティックバージョニングを採用します。

## [Unreleased]

---

## [0.1.0] - 2026-04-23

初回リリース。以下の主要機能・ユーティリティ・CLI を含みます。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 環境設定管理
  - Settings クラスによる環境変数ラッパーを実装（src/kabusys/config.py）。
    - J-Quants、kabuステーション、LINE、DBパス、監視閾値などの設定プロパティを提供。
    - KABUSYS_ENV の妥当性チェック（development / paper_trading / live）。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH などペーパートレード向け設定に対応。
  - 自動 .env ロード機能を実装。プロジェクトルート（.git または pyproject.toml）を探索し、`.env` / `.env.local` を読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。

- .env ウィザード CLI
  - 対話式ウィザードで .env を作成/更新するツール（src/kabusys/config_setup.py）。
    - 項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DBパス等）。
    - シークレット値は表示をマスクし、保存前に確認プロンプトを実施。
    - .env の書式と注意書きを含む出力。

- 設定検証 CLI
  - 起動前に .env と config/*.yaml の妥当性を検証するツール（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DBパスの親ディレクトリ確認、YAML パースチェック（PyYAML がない場合はスキップ）。
    - `--strict` オプションで警告を失敗扱いにするモード。
    - 本番環境用の追加ガード（LINE 通知未設定や Kill Switch 設定等）を実施。

- 起動スクリプト
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）でポーリング間隔を上書き可能。
    - 監視は環境に関わらず本番用 sqlite_path を使用する仕様。
    - 停止はプロジェクト直下の `data/stop_requested.flag` によるフラグ検知で行う。
    - SystemMonitor の一回実行は例外をログに記録して継続。
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）。
    - `KABUSYS_ENV=paper_trading` の場合は専用の paper_trading DB を使用し、本番 DB と分離。
    - BrokerClientFactory を通じてブローカークライアントを作成（モック含む）。
    - ExecutionEngine をスレッドで起動し、`data/stop_requested.flag` による停止制御を実装。PID ファイル管理 (data/execution.pid)。

- 監視 DB 初期化フック
  - `init_monitoring_db` の呼び出しにより、監視テーブルの存在を保証（冪等）。

- ロギングおよびプロセス制御ユーティリティ
  - 統一ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）をルートロガーへ設定。
    - 環境変数/引数でログディレクトリ・ログレベルを指定可能。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX (Linux, macOS, FreeBSD) に対応した優先度設定を提供（psutil 利用）。
    - CPU affinity 固定機能（最初の N コアにピン留め）を提供。
    - 権限不足等で失敗した場合は警告ログでスキップ。

- Portfolio 構築ライブラリ
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates: スコア降順 + signal_rank によるタイブレーク。
    - calc_equal_weights / calc_score_weights: スコアが全て 0 の場合は等金額配分にフォールバック（警告）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: 既存ポジションをもとにセクターごとの時価比率を算出し、閾値超で当該セクターの新規候補を除外（unknown セクターは除外しない）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知レジームはフォールバックして 1.0）。
  - 株数決定ロジック（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method に応じたサイズ計算（risk_based / equal / score）。
    - 単元（lot_size）丸め、per-stock 上限(max_position_pct)、aggregate cap（available_cash） に基づくスケーリング / 再配分ロジックを実装。
    - cost_buffer による手数料・スリッページの保守的見積りをサポート。

- Paper Trading 検証レポートツール
  - Paper Trading の SQLite を解析して検証レポートを生成する CLI（src/kabusys/tools/paper_verification_report.py）。
    - 指標: 稼働率、注文成功率（fill rate）、送信率、P95 レイテンシ 等。
    - デフォルト閾値を定義し、PASS/FAIL 判定を出力。
    - `--from` / `--to` / `--db` オプション対応。PAPER_TRADING_SQLITE_PATH 環境変数を参照。

- 研究用ファクター計算（初期実装）
  - DuckDB を利用したファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum、Value、Volatility、Liquidity を想定した設計・定数を定義。
    - calc_momentum の実装を開始（ファイル末尾で未完の部分あり）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / Implementation details / Warnings
- 環境変数自動ロード
  - OS 環境変数が優先され、.env.local は .env の上書き（ただし OS 環境変数は保護される）。
  - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Paper Trading と Live の完全分離
  - paper_trading モードでは paper 用 SQLite（デフォルト data/paper_trading.db）を使用し、本番の monitoring DB と分離します。
- 監視と実行の停止制御
  - 停止制御はファイルフラグ（data/stop_requested.flag）と PID ファイルを利用します。運用時はこれらファイルの扱いに注意してください。
- 未完成 / 今後の作業
  - research/factor_research.py は calc_momentum 実装の途中（ファイル末尾に未完のコード断片あり）。ファクター群全体の完成とテストを推奨します。

---

（この CHANGELOG はソースコードから推測して作成しています。実際のリリースノートとして公開する前に内容の確認・加筆をお願いします。）