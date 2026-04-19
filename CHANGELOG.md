# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。日付や分類は、リポジトリ内のソースコード（モジュール名・コメント・実装内容）から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 基本アプリケーションパッケージを実装
  - パッケージメタ情報: kabusys.__version__ = 0.1.0
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。以下の特徴を含む:
    - 起動時にプロセス優先度を "high" に設定
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離
    - BrokerClientFactory によるブローカークライアント生成をサポート
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立てて実行（エンジンは別スレッドで実行）
    - 停止フラグファイル（data/stop_requested.flag）および PID ファイル（data/execution.pid）に対応し、停止要求を検知して安全に停止
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。以下の特徴を含む:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告ログ出力
    - 監視は環境にかかわらず本番用 sqlite_path を使用する実装（監視 DB の独立性確保）
    - 停止フラグファイルを検知してループを終了、KeyboardInterrupt に対応
- 設定管理
  - config.py:
    - .env 自動読み込み機能（プロジェクトルートの特定: .git または pyproject.toml を探索）
    - .env, .env.local の読み込み順や上書きルール実装（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）
    - .env の行パーサ実装（export プレフィックス、クォート処理、インラインコメント対応など）
    - Settings クラスで環境変数をラップし、型変換・妥当性検査（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を提供
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE などをサポート
- 設定ユーティリティ CLI
  - config_setup.py:
    - 対話式ウィザードによる .env の作成・更新機能を追加
    - 各種設定項目（KABUSYS_ENV/JQUANTS_REFRESH_TOKEN/KABU_API_PASSWORD/DUCKDB_PATH/SQLITE_PATH/LINE_*/LOG_LEVEL/KILL_FLAG_CLEAR_ON_START）を扱う
  - validate_config.py:
    - 起動前チェック CLI を追加（必須環境変数・KABUSYS_ENV・LOG_LEVEL・DB パス・config/*.yaml の存在とパース）
    - PyYAML 未インストール時には YAML 検証をスキップして警告を出す
    - --strict オプションで警告を FAIL 扱いにする機能
- ログ周りユーティリティ
  - utils/logging_setup.py:
    - ルートロガーへ StreamHandler (stdout) と 日次ローテーションの TimedRotatingFileHandler を統一設定
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続
    - LOG_LEVEL / LOG_DIR / 引数でのオーバーライド対応、既存ハンドラのクリーンアップ実装
- プロセス制御ユーティリティ
  - utils/process_priority.py:
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定機能を実装（psutil ベース）
    - CPU affinity 設定の補助関数 set_cpu_affinity を提供
    - アクセス拒否や未サポート環境への耐性（例外を警告に変換）
- ポートフォリオ構築ロジック（純関数群）
  - portfolio/portfolio_builder.py:
    - 候補選定関数 select_candidates（スコア降順、signal_rank によるタイブレーク）
    - 重み計算: calc_equal_weights, calc_score_weights（スコア全ゼロ時は等分配へフォールバック）
  - portfolio/risk_adjustment.py:
    - セクター集中上限を適用する apply_sector_cap（既存ポジションからのセクターエクスポージャ計算、"unknown" セクターは除外）
    - 市場レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームはフォールバック）
  - portfolio/position_sizing.py:
    - position sizing 実装（allocation_method: "risk_based" / "equal" / "score"）
    - lot_size（単元株）対応、リスクベースの許容リスク率・損切り率採用
    - aggregate cap（利用可能現金を超える場合のスケーリング）と端数処理（lot 単位での再配分）
    - cost_buffer（手数料・スリッページ考慮）を用いた保守的コスト見積り
  - portfolio/__init__.py で上記関数をエクスポート
- ペーパートレード検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加
    - system_status / trade_logs / risk_logs テーブルを参照して稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを集計
    - パス/フェイル閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）
    - 日付フィルタ (--from / --to) と DB パスの指定 (--db / 環境変数) をサポート
    - P95 計算ユーティリティを実装
- 研究用モジュール（未完成を含む）
  - research/factor_research.py:
    - ファクター計算の枠組みを追加（Momentum/Value/Volatility/Liquidity の方針、DuckDB 接続利用）
    - calc_momentum の骨子実装（ターゲット日を基準とした各種モメンタム指標の計算）を開始（ファイル末尾に未完の箇所あり）

### 変更 (Changed)
- なし（初回リリースとしての初期実装を反映）

### 修正 (Fixed)
- なし（初回リリースとしての初期実装を反映）

### 削除 (Removed)
- なし

### 注意点 / 既知の制限 (Notes / Known Issues)
- research/factor_research.py の calc_momentum 実装が途中で終わっている（ファイル末尾が切れているため完全実装を要する）。
- 一部コンポーネント（SystemMonitor, ExecutionEngine の詳細実装、BrokerClient 実装、monitoring_db スキーマ等）はこの差分に含まれる呼び出し元のみ提示されており、内部実装が別ファイルに依存しているため統合テストが必要。
- process_priority と CPU affinity は psutil の機能に依存しており、プラットフォームや実行権限による制限で設定がスキップされることがある（ログで警告される）。
- .env の自動読み込みはプロジェクトルート特定に依存する（.git または pyproject.toml）。ルートが特定できない場合は自動ロードをスキップする。

---

この CHANGELOG はソースコード中のコメントと実装から推測して作成しています。実際のリリース手順やバージョン運用ポリシーに合わせて日付・分類・詳細を調整してください。