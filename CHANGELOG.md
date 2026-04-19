# CHANGELOG

すべての変更点を記録します。フォーマットは Keep a Changelog に準拠します。  
この変更履歴は提示されたコードベースから実装内容を推測して作成したものです。

## [Unreleased]

- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-04-11

最初の公開リリース。本リポジトリは日本株自動売買システム「KabuSys」のコアユーティリティ群、実行/監視エントリポイント、設定ツール、ポートフォリオ構築ロジック、分析ユーティリティなどを提供します。

### Added

- コアパッケージ初期実装
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 実行系エントリポイント
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - 環境に応じて Paper Trading 用 DB と Mock ブローカークライアントを利用する（KABUSYS_ENV=paper_trading 時）。
    - 停止フラグ（data/stop_requested.flag）や PID ファイル管理をサポート。
    - 依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立てる。

- 監視系エントリポイント
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグを監視して安全にループを終了。
    - 監視データは本番用 sqlite_path を参照（環境にかかわらず本番監視 DB を使用する仕様）。

- 設定管理
  - config.py
    - Settings クラスで環境変数をラップして提供。
    - .env 自動ロード機能（プロジェクトルートが検出される場合）を実装。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - .env ファイルの堅牢なパース（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理）。
    - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等の値検証を行うプロパティを提供。
    - paper_trading 用の専用 sqlite パス、各種閾値（CPU/MEM/DISK）や監視関連パスを設定可能。

- 設定ツール
  - config_setup.py
    - 対話式ウィザードで .env の作成・更新を支援。
    - 項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、LOG_LEVEL、Kill Flag 動作など）を提供。
    - 既存値の読み込み、シークレット値のマスク表示、保存確認を実装。

- 設定検証 CLI
  - validate_config.py
    - 起動前に必須環境変数や config/*.yaml の存在・パースを検証する CLI。
    - `--strict` オプションで警告を失敗扱いにできる。
    - 本番 (KABUSYS_ENV=live) 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 警告）を実装。
    - PyYAML 未インストール時には YAML 検証をスキップし警告出力。

- ロギングユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30世代）を設定。
    - LOG_LEVEL / LOG_DIR の解決ルールを実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - 既存ハンドラのクリーンアップ（flush/close）を行うことで二重登録を防止。

- プロセス優先度ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX の差異を吸収して優先度（high/normal/low）を設定。
    - CPU アフィニティを最初の N コアに固定するヘルパーを提供。
    - 権限不足や未対応 OS を考慮した安全なフォールバックを実装。

- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順・タイブレーク）、等金額配分、スコア比率配分（スコアが全て 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）: 既存ポジションを基にセクター上限を判定し、候補を除外。
    - レジーム乗数（calc_regime_multiplier）: market レジームに応じた投下資金乗数を返却（bull/neutral/bear、未知は 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method による株数算出（risk_based / equal / score）。
    - risk_based: 許容リスク率、損切り率に基づく株数計算。
    - 上限（1 銘柄の max_position_pct、aggregate の max_utilization）と単元（lot_size）丸めを考慮。
    - cost_buffer を考慮した保守的なコスト見積りと、available_cash を超過する場合のスケーリング（端数調整を残差順で配分）を実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB（デフォルト data/paper_trading.db）からレポートを生成。
    - システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出。
    - 閾値を用いた PASS/FAIL 判定を出力（デフォルトの閾値をコード内に定義）。
    - P95 計算、日付フィルタリング、DB 存在チェック、OperationalError に対する耐性を実装。

- 研究用ファクター計算（骨格）
  - research/factor_research.py
    - DuckDB を利用したモメンタム、ボラティリティ、バリュー等のファクター計算設計。（calc_momentum 等の関数骨格を含む。）
    - DuckDB を前提とした外部 API 非依存の設計方針。

### Changed

- なし（初回リリース）

### Fixed

- なし（初回リリース）

### Deprecated

- なし

### Removed

- なし

### Security

- 環境変数やシークレット情報は .env ファイルに記載し、.env を絶対に Git にコミットしない旨の注意喚起を config_setup の出力に記載。

---

注:
- 上記はソースコード中に見える仕様や実装から推測した変更点と初回リリースノートです。実際のコミット履歴やリリース日に基づくものではありません。必要であれば実際の変更差分（git log/commit）を元により正確な CHANGELOG を生成できます。