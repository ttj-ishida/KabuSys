CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- 変更はセマンティックバージョニングに従います。
- 各リリースにはカテゴリ (Added, Changed, Fixed, Deprecated, Removed, Security) を付与します。

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-04-18
-------------------

Added
- 初期リリースを公開。
- コア機能／モジュールを追加:
  - kabusys パッケージの基本構成（__version__ = 0.1.0）。
  - 実行系:
    - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時に paper_trading 用 DB を使用し MockBrokerClient を利用する分離設計。
    - ExecutionEngine を補助するコンポーネント群（OrderRepository, OrderManager, Reconciler, RiskManager, BrokerClientFactory の組み立てロジック）。
    - 実行エンジンはデーモンスレッドで起動し、停止フラグ（data/stop_requested.flag）や PID ファイルを扱う。
  - 監視系:
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB 初期化（init_monitoring_db）と DuckDB 連携を行う。
  - 設定関連:
    - config.py: 環境変数/.env の自動読み込み・Settings クラスによる集中管理。PAPER_FILL_MODE のバリデーション、paper_trading 用 DB パスやしきい値等のプロパティを提供。
    - config_setup.py: .env を対話式に作成・更新するウィザード CLI。複数の設定項目（J-Quants トークン、kabu API パスワード、DB パス、LOG_LEVEL 等）をサポート。
    - validate_config.py: .env と config/*.yaml の簡易検証 CLI。必須環境変数のチェック、KABUSYS_ENV の妥当性、YAML のパースチェック（PyYAML 利用可の場合）や本番環境特有のガードチェックを実装。
  - ポートフォリオ構築（純関数群）:
    - portfolio.portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights を提供（スコア基準や同点のタイブレークを実装）。
    - portfolio.risk_adjustment: apply_sector_cap（セクター上限ロジック）、calc_regime_multiplier（市場レジームに応じた乗数）を実装。
    - portfolio.position_sizing: calc_position_sizes（risk_based / equal / score の配分方式、単元株丸め、aggregate cap スケーリング、cost_buffer を考慮した安全な割付）を実装。
    - portfolio.__init__ で上記関数を公開。
  - リサーチ／分析:
    - research.factor_research（モメンタム等のファクター計算。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。モジュールにモメンタム計算関数のスケルトンを提供 — 大規模分析は DuckDB 上で実行）。
  - ツール:
    - tools.paper_verification_report.py: Paper Trading 用検証レポート生成スクリプト。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して PASS/FAIL を判定。PAPER_TRADING_SQLITE_PATH 環境変数や --db オプションで DB パスを指定可能。
  - ユーティリティ:
    - utils.logging_setup: stdout 出力 + 日次ローテートファイルハンドラをルートロガーに設定。ログディレクトリ自動作成、LOG_LEVEL 解決ロジック、既存ハンドラのクリーンアップを実装。
    - utils.process_priority: psutil を用いたクロスプラットフォームのプロセス優先度設定（Windows の優先度クラス、POSIX の nice 値を吸収）。CPU affinity 設定ユーティリティも提供（利用数を指定して最初の N コアにピン留め）。
    - monitoring.monitoring_db / monitoring.system_monitor（監視 DB 初期化や SystemMonitor ロジックへの接続用フック）を想定した初期整備。
- .env 読み込みの強化:
  - .env 自動ロードでプロジェクトルート（.git または pyproject.toml）を探索して読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの取り扱いなどに対応。

Changed
- 設計上の重要な決定点を文書化:
  - 分析用途は DuckDB（duckdb ファイル）を使用し、ランタイム監視やペーパートレードのトランザクションは SQLite に保持して用途を明確に分離。
  - run_monitoring は KABUSYS_ENV にかかわらず監視用の（本番）sqlite_path を参照して監視データを一元管理する設計。
  - run_execution は KABUSYS_ENV=paper_trading のときに paper_trading 専用の SQLite を使用して本番 DB と完全分離する設計。
- ロギング:
  - 初期化時に既存ハンドラを安全にクローズしてから再設定することで多重設定を防止。
  - ログディレクトリの作成に失敗した場合はファイル出力を無効化して stdout のみで継続するフェイルセーフを導入。
- 設定検証:
  - validate_config で --strict モードを追加（警告を FAIL 扱いにする）。

Fixed
- 複数の実行時失敗を想定した保護ロジックを追加:
  - process_priority の設定が権限不足や未サポート OS だった場合に警告を出してスキップするようにした。
  - run_monitoring / run_execution の終了処理で DB 接続を確実にクローズする finally ブロックを使用。
  - paper_verification_report の P95 算出が空データに対して None を返すようにして例外を回避。

Security
- .env の扱いについて注意書きを追加:
  - config_setup で生成される .env に機密情報が含まれることを明記し、絶対に Git 等にコミットしないことを強調。

Notes / Known limitations
- 一部のモジュールは外部コンポーネント（BrokerClient 等）に依存しており、テストやローカル実行ではモック実装が必要。
- price 欠損時のエクスポージャー評価（apply_sector_cap の TODO）や銘柄ごとの lot_size 対応など将来的な改善点をコード中に注記。
- research.factor_research はモメンタム計算の骨組みを含むが、外部データスキャン範囲等の最適化は今後の作業対象。

（この CHANGELOG はコードベースの内容を元に推測して作成しています。実際のリリースノート作成時にはリリース担当者による確認・追記を推奨します。）