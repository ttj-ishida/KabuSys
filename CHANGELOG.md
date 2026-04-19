CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記録しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 初回リリース
最初の公開リリース。システム監視・実行エンジン・設定管理・ポートフォリオ構築など、自動売買システム KabuSys の基盤機能を実装。

### 追加 (Added)
- 全体
  - パッケージバージョンを 0.1.0 として定義（src/kabusys/__init__.py）。
  - プロジェクトルートの検出と .env 自動読み込み機能を実装（src/kabusys/config.py）。
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動で読み込む。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の各行に対して export 形式・クォート・インラインコメント等に対応する堅牢なパーサを実装。
  - Settings クラスを実装し、環境変数の型・妥当性チェックや便利プロパティを提供（DB パス、環境モード、ログレベル、Paper Trading 設定など）。
  - 設定ウィザード CLI を追加（python -m kabusys.config_setup）。
    - 対話式で .env を作成・更新する run_wizard と書き込みロジック（.env のテンプレート）を提供。
  - 設定検証 CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV／LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検査（PyYAML がある場合）などを行う。
    - --strict モードで警告を失敗扱いにできる。
  - 実行エントリスクリプトを追加
    - run_execution.py: ExecutionEngine の起動ロジック、Paper Trading 時に専用の SQLite を利用する分離、および BrokerClientFactory を使った broker の生成。停止フラグ / PID 管理、スレッドでのエンジン実行制御を含む。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔上書き、停止フラグ検知ロジックを実装。監視用 DB は環境に関わらず本番 sqlite_path を用いる設計。
  - ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーに一元設定。デフォルト logs/ ディレクトリ、日次ローテーション & 30 日分保持。
    - LOG_DIR 指定や環境変数 LOG_LEVEL によるレベル解決。既存ハンドラの二重追加防止のためクリアしてから再設定。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収して set_process_priority(), set_cpu_affinity() を提供。権限・未対応 OS は警告でフォールバック。
  - ポートフォリオ構築関連の純粋関数群を追加（src/kabusys/portfolio/*）
    - portfolio_builder.py: シグナルの候補選定 select_candidates(), 等金額 calc_equal_weights(), スコア加重 calc_score_weights()。
    - risk_adjustment.py: apply_sector_cap()（セクター集中制限）と calc_regime_multiplier()（市場レジームに基づく投下資金乗数）。
    - position_sizing.py: calc_position_sizes()（allocation_method: risk_based / equal / score に対応、lot_size 単元丸め、aggregate cap スケーリング、cost_buffer 対応）。
    - portfolio パッケージから上記関数をエクスポート。
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）
    - データベース（PAPER_TRADING_SQLITE_PATH または指定された DB）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し PASS/FAIL を判定。閾値はファイル内定義（稼働率 99% 等）。
  - research/factor_research.py の骨格実装を追加
    - Momentum 等のファクター定義、DuckDB 接続を受け取る設計、計算用定数（期間）を実装。ファクター計算のための設計方針コメントを含む。

### 変更 (Changed)
- 実行・監視起動時に最初にプロセス優先度を "high" に設定するように統一（run_execution, run_monitoring）。
- 実行/監視共に DuckDB を分析用途に接続（duckdb パスは Settings で決定）。
- run_execution:
  - Paper Trading モードでは settings.paper_sqlite_path を使用して発注ログ等を本番 DB と分離。
  - 起動時に監視テーブルの存在を保証するため init_monitoring_db() を呼び出す（冪等）。
- run_monitoring:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御。無効値または 0/負値はデフォルト 60 秒にフォールバック。
  - 停止フラグ（data/stop_requested.flag）でループを終了する仕組みを採用。
- ロギング:
  - コンソール出力は stdout を使用（cron 等で stdout/stderr を一本化する運用に配慮）。
  - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
- 設定パース:
  - .env のパースは引用符・エスケープ・コメント規則に細かく対応（複数のケースを許容・安全に処理）。

### 修正 (Fixed)
- DB/接続後のクリーンアップを確実に行うため、run_monitoring と run_execution で finally ブロックにて sqlite3 と duckdb の接続を close() するように実装。
- position_sizing のスケールダウンロジックにおいて、残余キャッシュを用いた端数処理（lot_size 単位）を実装し、再現性のため同一 frac 時の順序安定化を確保。

### 既知の問題 / 注意事項 (Known issues / Notes)
- apply_sector_cap 内で price が 0.0 の場合にエクスポージャーが過少見積もりされ得る点を TODO コメントで明示。将来的に前日終値や取得原価でのフォールバックを検討する旨の記載あり。
- calc_regime_multiplier は未知のレジームに対して 1.0 でフォールバックし、警告を出力する挙動。
- research/factor_research.py はファイル末尾が未完（このリリースでは骨格・定数・設計方針を含むが、完全な実装は今後追加予定）。
- process_priority/set_cpu_affinity は権限不足や未対応プラットフォームでは動作せず、警告でスキップされる。
- validate_config の YAML 検査は PyYAML がインストールされていない場合はスキップされる（警告出力）。
- Paper Trading 検証レポートは DB スキーマ（system_status, trade_logs, risk_logs 等）に依存する。対象テーブルが存在しない場合は個別に例外処理してデフォルト値で出力する。

### 開発上のメモ / 将来の改善案
- position_sizing: 銘柄毎の単元（lot_size）を stocks マスタに持たせる設計への拡張を予定（現在は全銘柄共通の lot_size を使用）。
- apply_sector_cap: 価格欠損時のフォールバックロジック、"unknown" セクター扱いのポリシー再検討。
- research モジュール: ファクター計算の完全実装とユニットテスト整備。
- ログと監視のさらなるメトリクス収集・アラート統合（LINE 通知など）の強化。
- テスト容易性向上のため設定のモック化・依存注入ポイントの整理。

-----------
（以上）