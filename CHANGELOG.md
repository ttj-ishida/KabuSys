# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

※ バージョンはパッケージの __version__=0.1.0 を基に作成しています。

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーション構成とユーティリティを実装
  - src/kabusys/__init__.py にパッケージ情報（__version__ = 0.1.0）。
  - 環境変数・設定管理: src/kabusys/config.py
    - .env の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
    - export 形式やシングル/ダブルクォート、インラインコメント等に対応した堅牢な .env パーサ。
    - Settings クラスに各種プロパティ（DBパス、KABUSYS_ENV、PAPER_FILL_MODE の検証など）。
    - paper_trading 用の専用 SQLite パス（paper_sqlite_path）をサポート。
  - 環境設定ウィザード CLI: src/kabusys/config_setup.py
    - 対話的に .env を作成・更新可能。シークレット値のマスク表示、確認メッセージ、.env の書き出し機能を実装。
  - 設定検証 CLI: src/kabusys/validate_config.py
    - 必須/任意環境変数チェック、KABUSYS_ENV と LOG_LEVEL 検証、DBパス（ディレクトリ存在チェック）、config/*.yaml の存在と（PyYAML があれば）パース検証。
    - --strict オプションで警告を失敗扱いにできる。
  - ログ設定ユーティリティ: src/kabusys/utils/logging_setup.py
    - stdout 出力用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに統一設定。
    - LOG_DIR / LOG_LEVEL の解決順を実装。既存ハンドラをクリアして重複を防止。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度/CPU affinity ユーティリティ: src/kabusys/utils/process_priority.py
    - Windows/Linux/macOS を吸収する set_process_priority(level) と set_cpu_affinity(cpu_count) を実装（psutil 利用、権限不足時は警告でスキップ）。
  - 実行系起動スクリプト: src/kabusys/run_execution.py
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV に応じて paper_trading 時は専用 DB（data/paper_trading.db）を使用し、本番 DB と分離して運用（MockBrokerClient を利用）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動。
    - RiskConfig の初期値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。initial_portfolio_value を broker.get_available_cash() から取得。
    - ストップフラグ（data/stop_requested.flag）検知でエンジンを安全停止。PID ファイル管理。
  - 監視系起動スクリプト: src/kabusys/run_monitoring.py
    - プロセス優先度を "high" に設定し、監視ポーリングループを開始。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に依らず本番 sqlite_path を使用して monitoring DB を初期化。
    - 停止フラグ検知でループ終了。check_once() 呼び出し時の例外をキャッチして次サイクルへ継続。
  - ポートフォリオ構築モジュール: src/kabusys/portfolio/
    - portfolio_builder.py: select_candidates（スコア降順＋タイブレーク）、calc_equal_weights、calc_score_weights（全銘柄スコア 0 の場合は等配分にフォールバック）。
    - risk_adjustment.py: apply_sector_cap（既存保有を考慮したセクター上限フィルタ）、calc_regime_multiplier（レジームに応じた投下資金乗数、未知レジームはフォールバックで 1.0）。
    - position_sizing.py: calc_position_sizes（allocation_method="risk_based" / "equal" / "score" をサポート）、lot_size（単元）丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り、端数処理ロジック。
    - モジュール __init__ で主要関数を公開。
  - Paper Trading 検証レポート生成ツール: src/kabusys/tools/paper_verification_report.py
    - SQLite（デフォルト: data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）を集計してレポート出力。
    - PASS/FAIL 判定用の閾値定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - 日付フィルタ（--from / --to）、--db オプションをサポート。DB が存在しない場合のエラーメッセージを出力。
  - 研究用ファクター計算（骨格・モメンタム実装開始）: src/kabusys/research/factor_research.py
    - Momentum 計算のための定数と calc_momentum 関数の骨格（prices_daily テーブルを用いる設計、移動平均や各種ホライズンのリターン計算を想定）。

### Changed
- 主要起動スクリプト（run_execution/run_monitoring）で起動直後にプロセス優先度を High に設定するように統一。
- ロギング設定は stdout を基本とし、ファイル出力はログディレクトリ作成が成功した場合のみ有効化する挙動に統一。

### Fixed / Behavior
- .env 読み込み:
  - export KEY=val 形式やクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いを改善。無効行は無視。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑制可能。プロジェクトルートが特定できない場合は自動ロードをスキップ。
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出してデフォルトにフォールバックし、time.sleep の例外回避を実現。
- process_priority/set_cpu_affinity: 権限不足や未対応プラットフォームで例外を握りつぶし適切に警告することで起動の安定性を向上。
- validate_config:
  - PyYAML がインストールされていない場合は YAML 検証をスキップし、警告を出すように変更。
  - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。

### Notes / Security
- .env ファイルは絶対に Git 等へコミットしない旨の注意を config_setup の出力に明記。
- paper_trading は本番 DB と完全分離する設計（paper_trading 用 DB にのみ記録）を採用。

---

（今後のリリースでは各サブモジュール（ExecutionEngine、SystemMonitor、BrokerClient 等）の振る舞いに関する詳細な変更点をバージョンごとに追記してください。）