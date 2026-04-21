CHANGELOG
=========

すべての注目すべき変更を記載します。本ファイルは "Keep a Changelog" の形式に準拠します。

フォーマット:
- 変更はセマンティックバージョニングに従って記載しています。
- 日付はリリース日を示します。

Unreleased
----------
（現在なし）

0.1.0 — 2026-04-21
-----------------
初回公開リリース

Added
- 基本アーキテクチャとコアユーティリティを実装
  - プロジェクトパッケージ: kabusys（__version__ = 0.1.0）
  - ログ設定ユーティリティ (kabusys.utils.logging_setup)
    - stdout 出力および日次ローテーションファイル出力 (TimedRotatingFileHandler)
    - デフォルトログディレクトリ: logs/
    - ログローテーション保持期間: 30日
    - 環境変数 / 引数からログレベル・ログディレクトリを解決
  - プロセス優先度 / CPU affinity ユーティリティ (kabusys.utils.process_priority)
    - Windows / POSIX を吸収し、"high"/"normal"/"low" 等の抽象レベルで設定可能
    - CPU affinity を最初の N コアに固定する関数を提供
  - 環境設定管理 (kabusys.config)
    - .env 自動読み込み (.env / .env.local)、OS環境変数の保護機構
    - 柔軟な .env パーサ（export 形式、クォート、コメント対応）
    - Settings クラスで主要設定をプロパティとして取得（DBパス、API トークン、環境種別等）
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START 等の設定をサポート
  - 環境設定ウィザード CLI (kabusys.config_setup)
    - 対話式に .env を生成・更新
    - 保存前の確認とシークレットのマスク表示
  - 設定検証ツール CLI (kabusys.validate_config)
    - 必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パースチェック
    - --strict モード: 警告も失敗として扱う
    - PyYAML 未インストール時は YAML 検証をスキップして警告を出力
  - 実行エンジン起動スクリプト (kabusys.run_execution)
    - ExecutionEngine の起動フロー（プロセス優先度設定、DB接続、BrokerClientFactory の利用）
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用し、本番 DB と分離
    - 実行停止制御: data/stop_requested.flag と PID ファイル (data/execution.pid)
    - RiskManager 初期設定（レートリミット、サーキットブレーカー、最大ドローダウン等）
  - 監視ポーリング起動スクリプト (kabusys.run_monitoring)
    - SystemMonitor のポーリングループ起動
    - 環境にかかわらず監視は本番 sqlite_path を使用（監視テーブル初期化含む）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）
    - 停止フラグ検出で安全にループ終了
  - Portfolio 構築関連モジュール (kabusys.portfolio)
    - portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)
    - risk_adjustment: セクター上限適用 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier)
      - 未知レジームは警告を出して 1.0 にフォールバック
      - TODO コメントで価格欠損時のフォールバック改善を示唆
    - position_sizing: 発注株数算出 (calc_position_sizes)
      - risk_based / equal / score の配分方式をサポート
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金でのスケールダウン）、コストバッファ考慮
      - 将来拡張のための TODO（銘柄別 lot_size 等）
  - Paper Trading 検証レポートツール (kabusys.tools.paper_verification_report)
    - ペーパートレード DB（デフォルト: data/paper_trading.db）から集計してレポート出力
    - 指標: 稼働率 (uptime)、注文成功率、送信率、リスク却下数、APIレイテンシ（平均/最大/P95）
    - P95 計算、日付フィルタ (--from / --to)、閾値による PASS/FAIL 判定（デフォルト閾値をコード内で定義）
      - デフォルト閾値例: 稼働率 >= 99.0%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms
  - 研究用ファクタ計算モジュール (kabusys.research.factor_research)
    - Momentum / Value / Volatility / Liquidity に関する計算方針の実装構想を含む（DuckDB を利用した計算を想定）

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし）

Notes / Operational details
- DB:
  - DuckDB デフォルトパス: data/kabusys.duckdb
  - SQLite 監視 DB デフォルトパス: data/monitoring.db
  - Paper Trading 用 SQLite デフォルトパス: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
- 環境変数・設定:
  - 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能
  - 環境変数の保護: OS 環境変数は .env で上書きされない（.env.local は override=True だが protected で保護）
  - PAPER_FILL_MODE の有効値: "instant" | "partial" | "never" | "reject"（デフォルト: "instant"）
  - KILL_FLAG_CLEAR_ON_START のデフォルト: "0"（本番での自動クリアは危険であり警告）
- ログ:
  - 既存ハンドラをクリアしてから再設定するため、二重登録を防止
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続
- プロセス制御:
  - 起動スクリプトは起動直後にプロセス優先度を "high" に設定しようとする（失敗時は警告を出して続行）
  - 停止フラグ (data/stop_requested.flag) により安全に起動コンポーネントを停止可能

Known issues / TODO
- risk_adjustment.apply_sector_cap:
  - price が欠損 (0.0) の場合にエクスポージャーが過少評価される可能性がある旨の TODO コメントあり。将来的に前日終値等のフォールバックを検討。
- position_sizing:
  - 銘柄ごとの lot_size を将来的にサポートする旨の TODO コメントあり。
- research.factor_research:
  - ファイル末尾が実装途中の形跡（コメント・設計方針はあるが一部実装が継続中の可能性あり）。必要に応じて追加実装・テストが必要。

参考: 主要 CLI
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

以上。