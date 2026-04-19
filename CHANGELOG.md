# Changelog

すべての重要な変更を記録します。フォーマットは "Keep a Changelog" の慣習に準拠しています。  

現在のリリース履歴はコードベースから推測して作成したもので、実際のコミット履歴とは異なる場合があります。

全般
- 日付は本ファイル作成日（2026-04-19）で記載しています。

## [Unreleased]

(現時点での未リリース変更はありません。初期リリースは下記 0.1.0 を参照してください。)

## [0.1.0] - 2026-04-19

### Added
- 実行／監視用エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading 時は Mock クライアントおよび paper_trading 専用 SQLite（data/paper_trading.db）を使用する。停止フラグ（data/stop_requested.flag）/PID ファイル管理を組み込み、スレッドでエンジンを実行・安全停止する仕組みを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計。

- 環境設定・検証ツールを追加
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。必須項目／任意項目の定義と保存フォーマットを提供。
  - validate_config.py: .env と config/*.yaml を起動前に検証する CLI を追加。--strict モードで警告を FAIL 扱いにできる。本番向けの追加チェック（LINE 通知設定、kill-flag 設定等）を含む。

- 環境読み込み・設定管理機能を強化
  - config.py: .env 自動ロードをプロジェクトルート（.git または pyproject.toml を探索）ベースで行う機能を実装。自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を追加。環境変数パーサで export プレフィックス、クォート文字列内のバックスラッシュエスケープ、インラインコメントの扱いなどを正しく処理するよう拡張。Settings クラスに各種設定プロパティ（DB パス、PID/kill flag、paper trading 関連、閾値設定、env/log_level 判定など）を実装。

- ロギング／プロセス管理ユーティリティを追加
  - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30 日保持）を設定するユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップして安全にフォールバックする挙動を実装。
  - utils/process_priority.py: プロセス優先度設定（Windows / POSIX を吸収）および CPU affinity 設定機能を追加。アクセス権限不足や未対応プラットフォーム時の安全なフォールバック処理を実装。

- ポートフォリオ構築ライブラリを追加（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順）と等重・スコア加重の重み計算を実装。スコアが全て 0 の場合は等分配へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジーム時は警告とともにフォールバック。
  - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく株数算出ロジックを実装。単元株丸め（lot_size）、1銘柄上限、aggregate cap（available_cash 超過時のスケールダウン）や cost_buffer を考慮した安全な配分アルゴリズムを提供。

- Paper Trading 向けレポート生成ツールを追加
  - tools/paper_verification_report.py: paper_trading SQLite（デフォルト data/paper_trading.db）からシステム稼働率、注文成功率、送信率、レイテンシ（P95 を含む）などを集計・判定し、PASS/FAIL レポートを生成する CLI を実装。P95 計算、期間フィルタ、しきい値定義を含む。

- 研究用ファクター計算モジュールを追加（初期実装）
  - research/factor_research.py: Momentum / Value / Volatility / Liquidity などファクター群の計算設計を追加。DuckDB 接続を受け prices_daily / raw_financials テーブルを参照する方針で実装開始（モジュール内に定数・calc_momentum の基本構造を追加。実装は継続中）。

- パッケージ化・バージョン情報
  - __init__.py に __version__ = "0.1.0" を追加。

### Changed
- DB 初期化の冪等化
  - monitoring.monitoring_db.init_monitoring_db を実行前に呼ぶことで、monitoring テーブルの存在を保証（実行スクリプト両方で適用）。これにより初回起動時のテーブル欠如に対する安全弁を追加。

- ExecutionEngine / Monitoring の起動時処理強化
  - 両起動スクリプトで最初にプロセス優先度を "high" に設定するように変更（start-up sequence を統一）。また、停止フラグの存在検査を起動前・ループ内に組み込み、意図しない起動や迅速な終了をサポート。

- ログ出力の統一
  - 全起動スクリプトから setup_logging を呼び出すことでログ形式・ローテーションを統一。

### Fixed
- .env パーサの堅牢性向上（config._parse_env_line）
  - クォートされた値内のバックスラッシュエスケープ処理や export プレフィックス、インラインコメントの扱いを改善し、誤った解析による環境変数設定ミスを防止。

- ログハンドラ二重設定防止（logging_setup.setup_logging）
  - 既存ハンドラを flush/close の上でクリアしてから再設定するようにし、複数回呼び出した際の重複ログ出力を防止。

- process_priority の安全なフォールバック
  - サポート外 OS や権限不足（psutil.AccessDenied 等）発生時に警告ログを出して処理を継続するよう修正。

### Notes / Internal / TODO
- portfolio.position_sizing.calc_position_sizes:
  - price が欠損（0 や None）だと計算スキップする挙動を採用しているため、前日終値等のフォールバック取得を将来検討（TODO コメントあり）。
  - 銘柄ごとの単元サイズ（lot_size）の将来的な拡張設計に言及。

- research/factor_research.py:
  - calc_momentum の実装が途中で切れている（ファイル末尾に断片あり）。ファクター計算は設計方針・定数は整備済みだが、完全な実装は今後の作業。

- 設定自動ロード:
  - 自動ロードはデフォルトで有効。テストや特殊環境で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定する。

- Paper Trading と本番 DB の分離:
  - ExecutionEngine は paper_trading モード時に paper_trading 専用 SQLite を使用することで、本番データと完全に分離する設計を採用。

---

参照:
- 実装ファイル: src/kabusys/*（run_execution.py, run_monitoring.py, config.py, config_setup.py, validate_config.py, utils/*, portfolio/*, tools/paper_verification_report.py, research/factor_research.py など）