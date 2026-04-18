# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

なお以下のリリース内容は、与えられたコードベースから推測して作成しています。

## [Unreleased]

- 小さな改善やドキュメント更新を予定

## [0.1.0] - 2026-04-18

初回リリース。本リリースでは自動売買システム KabuSys のコアユーティリティ、実行・監視ランナー、設定管理、ポートフォリオ構築、各種補助ツール群を含む以下の機能を導入します。

### Added
- 実行ランナー
  - `src/kabusys/run_execution.py`
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBroker（paper trading 用 DB へ完全分離）を使用する挙動をサポート。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、PID ファイル管理、スレッドでの実行管理を実装。
- 監視ランナー
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する実装（監視 DB の一貫性を確保）。
    - 停止フラグ検出、例外のログ記録とポーリング継続の安全な取り扱いを実装。
- 設定管理
  - `src/kabusys/config.py`
    - Settings クラスを導入し、環境変数経由の設定参照を統一。
    - プロジェクトルート自動探索（`.git` または `pyproject.toml`）に基づく `.env` / `.env.local` の自動読み込み機能を追加（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可）。
    - `.env` パースの堅牢化（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱い）。
    - 各種設定プロパティ（DB パス、PID/KILL フラグ、しきい値、ログレベル、環境判定メソッド等）を提供。
- 設定ウィザード CLI
  - `src/kabusys/config_setup.py`
    - 対話式ウィザードで `.env` の初期作成・更新を支援する CLI を追加。
    - 秘密値のマスク表示、選択肢、既存値の読み込み、保存の確認フローを実装。
- 設定検証 CLI
  - `src/kabusys/validate_config.py`
    - `.env` および `config/*.yaml` の基本的な整合性チェックを行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML があれば）などを実装。
    - `--strict` オプションで警告を FAIL 扱いにするモードを提供。
- ロギング
  - `src/kabusys/utils/logging_setup.py`
    - ルートロガーに対する統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でのファイル出力（デフォルト logs/）を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続するフェールセーフ。
- プロセス優先度 / CPU アフィニティ
  - `src/kabusys/utils/process_priority.py`
    - Windows と POSIX(Linux/macOS/FreeBSD) を吸収するプロセス優先度設定機能を追加（`set_process_priority`）。
    - CPU affinity を最初 N コアに固定する `set_cpu_affinity` を実装。
    - 権限不足や未対応 OS の場合に警告を出して安全にスキップする実装。
- ポートフォリオ構築（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - シグナル選定（スコア順ソート）、等金額配分、スコア加重配分を提供。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - `src/kabusys/portfolio/position_sizing.py`
    - 発注株数計算ロジック（risk_based / equal / score）を実装。
    - 単元株（lot_size）での丸め、1銘柄上限、aggregate cap（利用可能現金に応じたスケーリング）、手数料/スリッページ見積り（cost_buffer）を考慮。
    - スケーリング時の残差処理（lot 単位での再配分）を実装。
  - `src/kabusys/portfolio/__init__.py` で上記関数群を公開。
- Paper Trading 検証レポート
  - `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード用 SQLite DB を解析して稼働率、注文成功率、送信率、レイテンシ指標（平均/最大/P95）などを出力するレポート生成ツールを追加。
    - コマンドライン引数 `--from` / `--to` / `--db` をサポート。
    - デフォルト閾値（稼働率 99%、成功率 90% 等）を定義し、PASS/FAIL を判定。
- リサーチ（ファクター計算）: 基盤実装の追加
  - `src/kabusys/research/factor_research.py`
    - Momentum 等のファクター計算モジュールの骨組みを追加（DuckDB を用いる設計）。
    - 定数・設計方針を定義（モメンタム期間、ATR 期間など）。（実装途中の関数あり）
- パッケージ情報
  - `src/kabusys/__init__.py`
    - バージョンを `0.1.0` に設定。

### Changed
- なし（初回リリースのため該当なし）

### Fixed
- なし（初回リリースのため該当なし）

### Security
- 環境変数の初期化や `.env` 取り扱いに注意喚起（`.env` を Git にコミットしない旨のコメントを config_setup に明記）。

### Notes / Implementation details（重要な挙動）
- 設定の自動読み込みはプロジェクトルートの検出に依存しているため、配布後やインストール環境でルートが見つからない場合は自動ロードをスキップします。
- `run_monitoring` は監視 DB として常に `Settings.sqlite_path`（本番 DB 想定）を使います。環境に依らず監視用 DB が統一される設計です。
- `run_execution` は Paper Trading 時に `paper_sqlite_path` を使用して本番 DB と完全に分離することで、発注ロジックの検証を行えるようにしています。
- プロセス優先度やログディレクトリ作成など、環境依存で失敗する可能性がある処理は警告を記録してフォールバックする実装になっています（堅牢性重視）。
- ポートフォリオ / 発注サイズ算出ロジックは数値的な丸めや上限判定に細かな安全弁（lot_size 単位の丸め、_max_per_stock、aggregate cap の再配分）を組み込んでいます。

---

今後の予定（推測）
- factor_research の完全実装（ファクター計算・正規化）
- ExecutionEngine / BrokerClient の詳細実装と統合テスト、監視・アラートの拡充
- ドキュメント整備、および追加の CLI / 管理ツール

(この CHANGELOG はコードの内容から推測して作成したものであり、実際の履歴やコミットログとは一致しない場合があります。)