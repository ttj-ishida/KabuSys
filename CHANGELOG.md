CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン番号は src/kabusys/__init__.py の __version__ に合わせています。

Unreleased
----------

- （現在の差分はありません）

0.1.0 - 2026-04-19
------------------

Added
- 基本アプリケーション構成を追加
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - ExecutionEngine をスレッドで起動・監視し、data/stop_requested.flag による外部停止に対応。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアントの抽象化。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine に注入。
    - PID ファイル管理（data/execution.pid）と優先度設定（高優先度）をサポート。
  - システム監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor を使った単一ポーリング（monitor.check_once()）ループ。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - data/stop_requested.flag による停止検知、KeyboardInterrupt のグレースフル終了、SQLite / DuckDB 接続の確実なクローズ。
    - Monitoring 用 DB は環境に関係なく本番 sqlite_path を使用する設計。
- 設定管理
  - 環境変数 / .env ローディング機能を追加（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env/.env.local を読み込む（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパースはシングル/ダブルクォート、エスケープ、コメント、export プレフィックスに対応。
    - 各種設定プロパティ（DB パス、API トークン、KABUSYS_ENV、ログレベル、Paper Trading 設定等）をラップして提供。
    - 必須項目不足時は明示的に例外を投げる _require() を提供。
- 設定検証・セットアップ CLI
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数や KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在や YAML のパースを検証。
    - --strict オプションで警告を失敗として扱う挙動を提供。
  - 環境設定ウィザードを追加（src/kabusys/config_setup.py）。
    - 対話式に .env を生成・更新するウィザード（項目の説明、デフォルト、シークレットマスク等）。
    - 既存 .env の読み込み・編集・確認・保存機能を提供。
- ロギング・プロセス管理ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - コンソール出力（stdout）用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 環境変数 LOG_LEVEL / LOG_DIR を優先する動作。
  - プロセス優先度 / CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux/Mac/FreeBSD）に対応した優先度設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合はログ警告を出してスキップする安全設計。
- ポートフォリオ構築ライブラリ
  - 候補選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順とタイブレークルールによる候補抽出。
    - calc_equal_weights / calc_score_weights: 等金額・スコア重み配分。全スコアが 0 の場合は等金額にフォールバック。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率を計算し、上限超過セクターの新規候補を除外（unknown セクターは除外しない）。
    - calc_regime_multiplier: regime（bull/neutral/bear）に応じた投下資金乗数を返却（既定値: bull=1.0, neutral=0.7, bear=0.3）。
  - ポジションサイズ決定（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の allocation_method に対応した株数計算。
    - 単元株（lot_size）丸め、1銘柄上限・Aggregate cap（available_cash）によるスケーリング、cost_buffer を用いた保守的コスト見積もり、残余を用いた再配分ロジックを実装。
- リサーチ（解析）基盤（下書き）
  - ファクター計算モジュールの骨子を追加（src/kabusys/research/factor_research.py）。
    - Momentum, Value, Volatility, Liquidity 等を想定した定数とインターフェース設計。DuckDB 接続を用いた prices_daily/raw_financials 参照方針。
    - （注）ファイル末尾で calc_momentum 実装が途中で途切れているため、今後の実装拡張予定。
- ツール
  - Paper Trading 検証レポートスクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを集計し、PASS/FAIL 判定を行う。
    - デフォルト DB は data/paper_trading.db。--db オプションや PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能。
    - 判定基準（稼働率、成功率、送信率、P95 レイテンシ）のしきい値を定義。
- 監視テーブル初期化ユーティリティ参照
  - init_monitoring_db を run_monitoring/run_execution から呼び出して監視テーブルの存在を保証（冪等処理）。

Changed
- N/A（初回リリースのため変更はありません）

Fixed
- N/A（初回リリースのためバグ修正履歴はありません）

Deprecated
- N/A

Removed
- N/A

Security
- N/A

Notes / 実装上の注意
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布後や特殊な環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑制できます。
- process_priority の設定は権限や OS に依存し、失敗した場合は警告を出して継続します（動作保証はされません）。
- research/factor_research.py の一部は未完（calc_momentum の後半が途切れています）。ファクター計算の完成は今後のタスクです。
- Paper Trading と本番 DB は明確に分離される設計ですが、運用時は .env の設定（PAPER_TRADING_SQLITE_PATH 等）を必ず確認してください。

今後の予定（例）
- research ファクター計算の完成とユニットテスト追加
- ExecutionEngine / RiskManager の単体テスト強化
- ドキュメント（README / API 仕様）の拡充
- CI による静的解析・型チェック・テスト自動化

----