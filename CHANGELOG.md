# Changelog

すべての重要な変更を記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

- 今後の作業（例）
  - research.factor_research.calc_momentum の実装完了・拡張（現在ファイル途中まで実装済）
  - テスト・ドキュメントの追加

---

## [0.1.0] - 2026-04-21

初回公開リリース。本リリースでは、自動売買システムのコアユーティリティ、環境設定ツール、実行/監視の起動スクリプト、ポートフォリオ構築ロジック、ペーパートレード検証ツールなどを実装しています。

### Added

- 基本パッケージ情報
  - パッケージバージョンを設定: kabusys.__version__ = "0.1.0"
  - パッケージエクスポート定義を追加（kabusys.__all__）

- 環境変数／設定管理
  - kabusys.config: Settings クラスによる環境変数アクセスラッパーを実装
    - .env の自動ロード（プロジェクトルート検出: .git または pyproject.toml）
    - .env のパース機能（クォート、export プレフィックス、コメントの扱い、エスケープ対応）
    - 必須環境変数取得ヘルパー _require()
    - 各種設定プロパティ（J-Quants／kabu API／DBパス／paper trading 設定／監視閾値など）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能

- 環境設定ウィザード CLI
  - kabusys.config_setup: 対話式ウィザードで .env を作成・更新するツールを追加
    - 複数の設定項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 関連など）
    - 既存 .env 読み込み、シークレットマスク表示、保存確認
    - .env ファイル書き込みロジック（テンプレート形式）

- 設定検証 CLI
  - kabusys.validate_config: 起動前チェックツールを実装
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック
    - DUCKDB/SQLite パスの親ディレクトリ存在チェック
    - config/*.yaml の有無・パースチェック（PyYAML 未インストール時はスキップ）
    - KABUSYS_ENV=live 時の追加ガード（LINE通知設定や KILL_FLAG_CLEAR_ON_START の警告）
    - --strict モード（警告も失敗扱い）

- 実行・監視プロセス起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine の起動ロジックを追加
    - 起動時にプロセス優先度を high に設定
    - paper_trading 環境時は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し本番 DB と分離
    - BrokerClientFactory 経由でブローカクライアント生成（Paper 用の MockBroker を想定）
    - OrderRepository, OrderManager, RiskManager, Reconciler 組み立て、ExecutionEngine 実行スレッド管理
    - 停止フラグ（data/stop_requested.flag）の検知による安全終了、PID ファイル管理
  - src/kabusys/run_monitoring.py
    - SystemMonitor の起動ループを追加
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）
    - 監視は本番 sqlite_path を参照（環境に依らず本番監視 DB を使用する仕様）
    - 停止フラグによるループ終了、例外ログと継続動作

- ロギング／プロセス制御ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定
    - 既存ハンドラをクリアして重複を防止
    - LOG_LEVEL / LOG_DIR 環境変数および引数からの解決、ログディレクトリ作成失敗時のフォールバック
  - src/kabusys/utils/process_priority.py
    - psutil を使ったクロスプラットフォーム（Windows / POSIX）なプロセス優先度設定
    - set_cpu_affinity による CPU 固定機能（安全に失敗をハンドル）

- ポートフォリオ構築ロジック（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: シグナルのスコア順ソートと上位抽出（タイブレークに signal_rank 使用）
    - calc_equal_weights / calc_score_weights: 等配分・スコア重み配分（全スコアが0なら等配分にフォールバック）
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮し上限超過セクターの新規候補を除外）
    - calc_regime_multiplier: マーケットレジームに応じた投下資金乗数（bull/neutral/bear マップ、未知レジームはフォールバック）
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の割当方式に対応した株数決定ロジック
    - 単元株( lot_size ) 丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケールダウン、cost_buffer 考慮、残差処理による追加配分

- ペーパートレード解析ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用 SQLite (デフォルト: data/paper_trading.db) から指標を集計しレポートを出力
    - 指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシ、リスク却下数
    - 閾値による PASS/FAIL 判定、期間指定（--from/--to）と DB パス指定（--db）に対応

- 研究用ファクターモジュール（下地）
  - src/kabusys/research/factor_research.py
    - モメンタム／ボラティリティ等の計算方針と定数群を実装
    - calc_momentum の関数シグネチャとドキュメントを追加（実装途中でファイルは途中まで）

- DB 初期化ユーティリティ連携
  - monitoring_db.init_monitoring_db を複数箇所で呼び出し、監視テーブル存在を保守（冪等化）

### Changed

- （初回リリースのため該当なし）

### Fixed

- （初回リリースのため該当なし）

### Notes / Implementation details

- .env パーサはシングル/ダブルクォート内のバックスラッシュエスケープや、export プレフィックス、行中コメントの取り扱いをサポートします。
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようとしますが、権限やプラットフォームにより設定に失敗した場合は警告ログを出して処理を継続します。
- logging_setup はログディレクトリ作成に失敗した場合、ファイルハンドラの作成をスキップしコンソールログのみで継続する安全設計です。
- Paper Trading は本番データベースと完全分離する設計（settings.is_paper に応じて paper_sqlite_path を使用）。
- 一部モジュール（例: factor_research の一部）は実装途中のため、今後の拡張予定です。

---

今後の予定（例）
- research.factor_research の完実装（各種ファクター計算、正規化）
- ExecutionEngine および Broker クライアントの追加ユニットテスト強化
- CLI ドキュメント、運用ガイドの充実

（以上）