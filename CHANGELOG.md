# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このプロジェクトのバージョンは src/kabusys/__init__.py にて `0.1.0` として定義されています。

## [0.1.0] - 2026-04-20

初回リリース。主要な機能追加・ユーティリティ群を実装しました。

### 追加 (Added)
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用し、本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）を監視して安全に停止可能。
    - PID ファイル管理（data/execution.pid）をサポート。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下は検出してデフォルトにフォールバック）。
    - Monitoring は環境に関係なく本番用 sqlite_path（Settings.sqlite_path）を使用してデータを記録。
    - 停止フラグ（data/stop_requested.flag）を検出してループ終了。
    - DuckDB 接続（分析用）も初期化して利用。

- 設定関連
  - config.py
    - .env / .env.local の自動ロード機能を実装（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
    - .env パース機能を強化（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理などに対応）。
    - Settings クラスを実装し、環境変数からの設定取得と妥当性チェック API を提供（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE などの検証を含む）。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE 等の設定をサポート。
    - 監視閾値（CPU/MEM/DISK）や PID / kill flag の設定取得を提供。

  - config_setup.py
    - インタラクティブな .env 作成・更新ウィザードを追加（対話式プロンプトで必須/任意項目を設定、.env を出力）。
    - 既存 .env 読み取り・既存値の再利用、シークレット値のマスク表示、保存前確認を実装。

  - validate_config.py
    - 起動前設定検証 CLI を追加（必須環境変数、KABUSYS_ENV 値、LOG_LEVEL、DB パス、config/*.yaml の存在チェック等）。
    - --strict オプションで警告を FAIL 扱いにできる。
    - 本番（live）環境向けの追加警告（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を実装。

- ポートフォリオ構築（pure functions）
  - portfolio/portfolio_builder.py
    - シグナルから候補選定（スコア降順、同点は signal_rank でブレーク）を実装。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）を実装。全スコアが 0 の場合は等分配にフォールバック（警告ログ）。

  - portfolio/risk_adjustment.py
    - セクター集中上限適用（apply_sector_cap）：既存ポジションのセクター割合を計算し、上限超過セクターの新規候補を除外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマップ、未知レジームはフォールバックしてログ警告）。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出（allocation_method: "risk_based" / "equal" / "score"）。
    - リスクベース算出（risk_pct, stop_loss_pct に基づく算出）、単元株丸め(lot_size)、1銘柄上限、aggregate cap（利用可能現金を超える場合はスケーリングと残差処理）を実装。
    - cost_buffer（手数料・スリッページ見積）を考慮した保守的推定に対応。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。
    - stdout 出力（StreamHandler）および日次ローテーションするファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL の環境変数対応、ハンドラ二重設定防止、ログディレクトリ作成失敗時のフォールバック対応を実装。
    - ファイル出力に失敗した場合はコンソールのみで継続。

  - utils/process_priority.py
    - プロセス優先度設定ユーティリティ（Windows / POSIX の差分吸収、psutil ベース）を追加。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や未サポート環境ではログ警告でスキップ。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成スクリプトを追加。SQLite（paper_trading DB）からシステム安定性（稼働率）、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出して PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db、--db オプションおよび環境変数 PAPER_TRADING_SQLITE_PATH により上書き可能。
    - 判定閾値（稼働率、成功率、P95 レイテンシ等）はソース内定数で調整可能。

- データ分析基盤接続
  - DuckDB 接続を複数モジュールで利用する設計を採用（research/factor_research.py、Execution/monitoring ログの分析用途など）。

- パッケージ情報
  - src/kabusys/__init__.py にバージョン定義 __version__ = "0.1.0" を追加。

### 変更 (Changed)
- なし（初回リリースのため既存仕様変更はありません）。

### 修正 (Fixed)
- なし（初回リリース）。

### 既知の制限・注意点 (Known issues / Notes)
- research/factor_research.py はモメンタム等のファクター計算を実装中（ファイル末尾が途中で切れているため未完の関数あり）。今後のリリースで完成予定。
- process_priority の適用は OS 権限に依存するため、アクセス権限がない環境では設定がスキップされる（警告ログ）。
- apply_sector_cap の価格欠損時の挙動に関する TODO コメントあり（価格が 0.0 の場合にエクスポージャーが過少見積りされる可能性）。将来的にフォールバック価格の導入を検討。

---

今後のリリースでは、research モジュールの完成、ExecutionEngine / Broker クライアントの詳細実装・テスト強化、監視・レポーティング機能の拡張を予定しています。