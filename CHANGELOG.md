All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog 準拠（日本語）。コード内容から推測して記載しています。

Unreleased
---------
Added
- MONITOR_POLL_INTERVAL 環境変数による監視ポーリング間隔上書き機能（不正値はデフォルト 60 秒にフォールバックし、警告を出力）。
- SystemMonitor/monitoring 起動スクリプト（src/kabusys/run_monitoring.py）。停止フラグ、sqlite/duckdb 接続、例外ハンドリング、プロセス優先度の設定を実装。
- ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）。paper_trading 環境時の専用 DB 分離、BrokerClientFactory 経由のブローカ選択、スレッドでのエンジン実行と停止フラグ監視を実装。
- .env 対応設定管理（src/kabusys/config.py）：
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
  - .env / .env.local の自動ロード（OS 環境変数を保護）。
  - export 形式やクォート付き値、インラインコメントに対応したパーサ実装。
  - 各種設定プロパティ（DB パス、PID ファイル、しきい値、環境判定、paper_trading 用設定等）。
- 設定ウィザード CLI（src/kabusys/config_setup.py）：
  - 対話式で .env を作成・更新するウィザード（シークレット入力のマスク、既存値の再利用、保存確認）。
- 設定検証 CLI（src/kabusys/validate_config.py）：
  - 必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース検証。
  - --strict フラグで警告をエラー扱いにできる。
- ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）：
  - StreamHandler（stdout）＋日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
  - 既存ハンドラのクリア、LOG_DIR 指定、ファイルハンドラ作成失敗時のフォールバックを実装。
- プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）：
  - Windows / POSIX を吸収する set_process_priority、set_cpu_affinity を実装（権限不足や未対応 OS は警告でスキップ）。
- Paper Trading 検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）：
  - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定する CLI。
  - p95 計算・期間フィルタリング・DB 存在チェック・テーブル未存在時のフォールバック実装。
- ポートフォリオ構築関連（src/kabusys/portfolio/*）：
  - 銘柄選定・配分（select_candidates、calc_equal_weights、calc_score_weights）。
  - セクター集中制限・レジーム乗数（apply_sector_cap、calc_regime_multiplier）。
  - 株数決定・リスク制限・単元丸め・aggregate cap スケーリング（calc_position_sizes）。
  - 各関数は純粋関数で DB 参照なし、ドキュメント付。
- 研究用ファクター計算（src/kabusys/research/factor_research.py）：
  - DuckDB 経由でモメンタム等のファクターを計算する設計（モメンタム計算関数等の骨子実装）。
- DuckDB を分析用データベースとして統合（複数モジュールで使用）。
- PID / stop / kill フラグファイルを使ったプロセス制御（起動スクリプト側で検知・停止処理）。

Changed
- ログ出力が stderr ではなく stdout を使うように統一（cron/TaskScheduler などの運用を考慮）。
- .env 自動ロードの優先順位と保護ルールを整理（OS 環境変数は上書きされない）。

Fixed
- .env のパースにおけるクォート・エスケープ・コメント処理を強化し、実運用での .env 設定ミスを低減。

0.1.0 - 2026-04-19
---------
Added
- 初回公開: KabuSys のコアユーティリティと CLI を一通り実装。
  - 起動スクリプト: run_monitoring.py, run_execution.py
  - 設定管理: config.py, config_setup.py, validate_config.py
  - ロギング: utils/logging_setup.py
  - プロセス制御: utils/process_priority.py
  - ポートフォリオ構築: portfolio/（選定・重み・サイズ調整・リスク制御）
  - Execution 関連の骨格（BrokerClientFactory, ExecutionEngine, OrderManager 等の呼び出しを想定するコード統合）
  - 分析用 DuckDB 統合
  - Paper Trading 向け分離 DB サポート（paper_sqlite_path）
  - Paper Trading 検証ツール（tools/paper_verification_report.py）
  - 研究用ファクター計算モジュールの雛形（research/factor_research.py）

Changed
- ログ設定の初期化を一元化し、ハンドラの重複防止と日次ローテーションを導入。
- 起動時にプロセス優先度を "high" に設定する動作を導入（set_process_priority 呼び出し）。

Security
- .env ファイルの生成ウィザードで .env を明示的に作成するようにし、.env を誤ってコミットしないよう注意喚起を追加。

Notes（推測）
- コードベースの多くは実運用（本番・ペーパートレード）での安全性と運用性を重視しており、停止フラグ・PID ファイル・ログのローテーション・設定検証などの運用機能が整備されています。
- research/factor_research.py はファイル末尾が途中で切れている（snapshot の都合）ように見えるため、ファクター計算の実装は継続中の可能性があります。

未記載の変更点や日付に関する厳密な履歴は、ソース管理のコミットログを参照してください。コードから推測してまとめたため、実際のコミット単位の変更履歴とは差異がある場合があります。