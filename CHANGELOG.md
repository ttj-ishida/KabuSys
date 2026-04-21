# CHANGELOG

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。  
ここに記載した内容はソースコードから推測してまとめたものであり、実際のコミット履歴ではありません。

現在: 0.1.0

## [Unreleased]
- なし

## [0.1.0] - 2026-04-21
初回リリース。以下の主要機能・ユーティリティを含みます。

### 追加 (Added)
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。スレッドでセッションを実行し、停止フラグ (data/stop_requested.flag) による安全停止をサポート。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper trading 用 SQLite（デフォルト: data/paper_trading.db）を使用する設計を導入。BrokerClientFactory により本番/モックの切替えを行う想定。
    - 起動時にプロセス優先度を "high" に設定するフローを導入。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ検知、例外時のログ出力、SQLite / DuckDB の接続およびクローズ処理を実装。
- 設定管理/支援
  - config.py
    - Settings クラスで環境変数をラッピングし、型変換・バリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を実施。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等の既定値と Path 返却を提供。
    - 自動 .env 読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env のパース（クォートやエスケープ、コメント、export プレフィックス対応）を実装。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI。必須/任意項目、シークレット入力、確認プロンプトを備える。
  - validate_config.py
    - 起動前の設定検証 CLI。必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在／パース検査（PyYAML がある場合）を行う。
    - --strict オプションで警告を失敗扱いにできる。本番環境向けの追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通に使えるログ設定ユーティリティを追加。stdout 出力（StreamHandler）および日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決ロジック、既存ハンドラのクリア、ファイル作成失敗時のフォールバックなどに対応。
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームなプロセス優先度設定と CPU affinity 設定関数を追加。Windows と POSIX (Linux/macOS/FreeBSD) を考慮したフォールバック処理と例外ハンドリングあり。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全ゼロ時に等分配へフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap、マーケットレジームに基づく資金乗数 calc_regime_multiplier を実装。未知レジームのフォールバック挙動を定義。
  - portfolio/position_sizing.py
    - position sizing を担当する calc_position_sizes を実装。リスクベース、等配分／スコア配分の両方式をサポートし、単元株（lot_size）丸め、max_position_pct、max_utilization、コストバッファを考慮した集約キャップ（スケールダウン処理）を行う。
  - portfolio/__init__.py で公開 API を整理。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite の集計レポート生成ツール。システム安定性（稼働率）、注文成功率・送信率、リスク却下数、API レイテンシ（P95 計算）を集計し PASS/FAIL を判定する。
    - デフォルト DB パスは data/paper_trading.db。期間フィルタ (--from/--to) をサポート。
- DuckDB / SQLite 連携
  - 監視・実行スクリプトで DuckDB 接続（分析用 DB）と SQLite 接続（監視/履歴 DB）を確立する構成を採用。monitoring_db 初期化処理を起動時に呼び出してテーブルの存在を保証する設計。

### 変更 (Changed)
- パッケージ情報
  - src/kabusys/__init__.py に __version__="0.1.0" を設定し、主要サブパッケージを __all__ でエクスポート。

### 修正 (Fixed)
- 設定読み込みの堅牢化
  - .env 行パーサーでクォート内のバックサッシュエスケープ、export プレフィックス、インラインコメントの取り扱いを改善。無効行のスキップを明確化。

### ドキュメント/注記 (Documentation/Notes)
- 設定・運用に関する注意点をコード内 docstring や CLI 出力で明示。
  - .env は絶対に Git にコミットしない等の注意書きが config_setup に含まれる。
  - Paper Trading は本番 DB と完全分離される設計であることを明示。
  - process_priority / logging_setup は権限不足やファイル作成失敗時に警告を出して安全にフォールバックすることを記述。

### 既知の制限 / TODO（コード内コメントより）
- position_sizing: 銘柄別単元株（lot_size）将来の拡張、価格欠損時のフォールバック（前日終値や取得原価など）について TODO が残る。
- research/factor_research.py は複数のファクター計算を意図しているがファイル末尾で未完成部分（切り取り）あり。実装完了が必要。
- 一部の外部依存（psutil、duckdb、PyYAML）が存在し、環境によっては機能制約（YAML 検証スキップ等）がある。

### 破壊的変更 (Breaking Changes)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 特別なセキュリティ修正は含まれていません。運用時に .env の管理、シークレットの保護を行ってください。

---

この CHANGELOG はソースコードの内容から推測して作成した要約です。より正確な変更履歴は実際のコミットログを参照してください。