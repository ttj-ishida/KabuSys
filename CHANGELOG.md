CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています（日本語）。

Unreleased
----------
- なし

[0.1.0] - 2026-04-19
-------------------
Added（追加）
- 基本アプリケーション構成
  - パッケージ初期バージョンを導入（__version__ = "0.1.0"）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、高優先度での起動、ExecutionEngine をバックグラウンドスレッドで実行し、data/stop_requested.flag による停止をサポート。paper_trading モードでは専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関係なく本番 sqlite_path を使用する設計。
- 設定・環境管理
  - config.py: 環境変数ラッパー（Settings クラス）を実装。.env / .env.local の自動読み込み、プロジェクトルート自動検出（.git または pyproject.toml）、堅牢な .env 行パーサを提供。必須項目取得用の _require() や各種プロパティ（J-Quants、kabu API、DB パス、paper_trading 用パス・fill モード、各種閾値、環境判定プロパティ等）を実装。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。シークレットのマスク表示や既存 .env の読み込み、保存処理をサポート。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在およびパース（PyYAML があれば実施）を検証。 --strict モードで警告を FAIL 扱いに可能。
- ポートフォリオ構築関連（純関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア重み（calc_score_weights）を実装。スコア全ゼロ時は等分配へフォールバックする警告を出力。
  - portfolio/risk_adjustment.py: セクター集中制限を行う apply_sector_cap と市場レジームに基づく資金乗数 calc_regime_multiplier を実装。未知レジーム時はフォールバック動作を定義。
  - portfolio/position_sizing.py: 複数配分方式（risk_based, equal, score）に対応した株数計算ロジックを実装。単元株（lot_size）、1 銘柄上限、aggregate cap（available_cash に対するスケーリング）、手数料/スリッページを考慮する cost_buffer、残差処理によるロット単位の追加配分ロジック等を提供。
- ユーティリティ
  - utils/logging_setup.py: アプリ共通のロギング設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーに設定。ログディレクトリ自動作成と作成失敗時のフォールバックを実装。LOG_LEVEL / LOG_DIR の優先解決や app_name 指定でログファイル名を制御。
  - utils/process_priority.py: psutil を用いたプロセス優先度設定（Windows の priority class / POSIX の nice 値）と CPU affinity 固定のヘルパーを追加。対応 OS の差分吸収と権限不足時の安全ハンドリングを実装。
- モニタリング DB 初期化
  - monitoring/monitoring_db への初期化呼び出しを run_monitoring/run_execution で行うことで、監視テーブルの存在を保証（冪等）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite DB を読み、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数などを集計するレポート生成スクリプトを追加。期間フィルタ、PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションに対応。デフォルトの判定閾値（稼働率 99%、注文成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し、PASS/FAIL を出力。
- 研究用ファクター計算（着手）
  - research/factor_research.py: DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 系ファクターを計算する設計の導入。モメンタム計算のための定数や関数シグネチャを定義（calc_momentum 等）。（注: 大きな処理は導入段階）

Changed（変更）
- なし（初回リリース）

Fixed（修正）
- なし（初回リリース）

Security（セキュリティ）
- .env の取り扱いについて注意書きを config_setup の出力に追加（.env を絶対に Git にコミットしない旨を明記）。

Notes（備考）
- 設計方針として「DB 参照を伴わない純粋関数（ポートフォリオ・位置決め等）」「DuckDB を分析用に利用」「実環境（live）と paper_trading のデータ分離」を取っているため、本番と検証環境の混同を避ける構成になっています。
- run_* スクリプトは stop_flag（data/stop_requested.flag）や PID ファイル、kill/kill_clear 周りの環境変数を参照してプロセス管理を行います。KILL_FLAG_CLEAR_ON_START による自動クリア動作など、運用時の注意点があります。
- 一部モジュール（research の詳細実装など）は導入段階であり、今後の実装・テストで機能拡張が予定されています。

---
この CHANGELOG はコードベースの現状から推測して作成しています。必要であれば、リリース日やエントリの粒度をプロジェクトの実際のコミット履歴に合わせて調整してください。