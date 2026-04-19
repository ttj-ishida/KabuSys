Keep a Changelog
================

すべての重要な変更はこのファイルで管理します。  
フォーマットは Keep a Changelog に準拠しています。

[0.1.0] - 2026-04-19
--------------------

### 追加
- プロジェクト初期リリース: パッケージバージョンを __version__ = "0.1.0" として公開。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用する挙動（data/paper_trading.db をデフォルト）を実装。MockBrokerClient 利用想定をドキュメント化。
    - 停止用フラグ file (data/stop_requested.flag) と実行 pid ファイル (data/execution.pid) を用いた停止制御を実装。
    - ExecutionEngine の依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立ててバックグラウンドスレッドで run_session を実行。
  - run_monitoring.py
    - SystemMonitor 用ポーリング起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様を明記。
    - 停止フラグ file によりループを終了する仕組みを実装。
- 設定関連
  - config.py
    - .env 自動読込機構を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 行ごとの .env パーサーを実装（export 形式、クォート、エスケープ、インラインコメントを考慮）。
    - Settings クラスを実装し、アプリケーション設定をプロパティ経由で取得可能に（DB パス、PaperTrading 設定、監視閾値、環境判定など）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - config_setup.py
    - 対話式 .env ウィザードを実装。主要設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL 等）を対話で生成・更新可能。
    - .env の読み書きロジック（既存値の再利用・シークレットマスク表示）を提供。
  - validate_config.py
    - 起動前の構成検証 CLI を実装（必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証など）。
    - PyYAML 未インストール時には YAML 検証をスキップする挙動と警告を実装。
    - --strict オプションで警告を FAIL 扱いにする機能を追加。
- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
    - LOG_LEVEL, LOG_DIR, app_name による設定をサポート。
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加（Windows と POSIX の差を吸収）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。アクセス権限不足や未サポート環境は警告でスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap) と市場レジームに応じた乗数 (calc_regime_multiplier) を実装。
  - portfolio/position_sizing.py
    - position sizing（risk_based / equal / score）を実装。ロット丸め、per-stock 上限、aggregate cap のスケーリングロジック、cost_buffer を考慮した保守的見積りを実装。
  - portfolio/__init__.py
    - 上記関数群をパッケージエクスポート。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を集計・表示し、閾値による PASS/FAIL 判定を行う。
    - デフォルト DB は data/paper_trading.db。--from/--to/--db オプションをサポート。
- データベース / 分析
  - duckdb 統合: 複数モジュールで duckdb 接続を利用（Execution/Monitoring/研究用）。
- 研究用モジュール
  - research/factor_research.py
    - ファクター計算モジュールを追加（Momentum/Value/Volatility/Liquidity を想定）。DuckDB 接続を受け取り SQL + Python で計算する設計。関数インターフェース設計と定数を追加（計算窓・スキャン範囲など）。
    - 注: ファイルは途中までの実装（calc_momentum の先頭まで）であり、完全実装は今後の作業。

### 変更
- 監視 / 実行起動処理
  - 起動時にプロセス優先度を "high" に設定する呼び出しを run_monitoring/run_execution の先頭に追加し、スケジューラ環境での安定稼働を狙う設計。
  - monitoring 用 DB 初期化 init_monitoring_db をどちらのスクリプトでも呼び出し、監視テーブルの存在を冪等に保証。

### 修正
- .env パーサーの堅牢化
  - export プレフィックス、シングル/ダブルクォート中のバックスラッシュエスケープ、インラインコメント規則（クォートなしでは '#' の直前がスペース/タブのときのみコメントと扱う）に対応し、より多様な .env フォーマットを受け入れるよう改善。

### 既知の制限（注意事項）
- research/factor_research.py は初期実装の途中であり、完全実装は未完了。今後の追加作業が必要。
- position_sizing の price の欠損（0.0）時の挙動に関する TODO コメントあり（現状では過少見積りによるブロック漏れの可能性）。将来的にフォールバック価格（前日終値など）を採用することを検討。
- 一部の機能（例: BrokerClientFactory の Mock 実装や ExecutionEngine の詳細）はこのリリースのスナップショットで示されているが、外部依存や完全検証は別途必要。
- ログディレクトリ作成やプロセス優先度設定は環境依存で失敗する可能性があります（失敗時は警告ログを出し、処理を継続します）。

### 削除
- なし

### セキュリティ
- なし

---
注: 上記は提供されたソースコードから推測可能な変更点・挙動をまとめたものであり、実際のコミット履歴や意図とは差異がある場合があります。