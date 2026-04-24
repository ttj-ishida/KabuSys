# CHANGELOG

すべての注目すべき変更はここに記録します。フォーマットは "Keep a Changelog" に準拠します。  

## [0.1.0] - 2026-04-24

初回リリース。自動売買システム KabuSys の基礎機能と運用ユーティリティを実装しました。主な追加点・挙動は以下の通りです。

### Added（追加）
- 実行用エントリスクリプトを追加
  - src/kabusys/run_execution.py
    - ExecutionEngine を立ち上げる起動スクリプトを実装。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンを起動。
    - 停止フラグ (data/stop_requested.flag) と実行 PID 管理 (data/execution.pid) をサポート。
    - プロセス優先度を `high` に設定する処理を最初に呼び出す。

- 監視用エントリスクリプトを追加
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを実行するスクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視は環境に関わらず本番用 sqlite_path を使用して監視 DB を初期化（init_monitoring_db）。
    - 停止フラグ (data/stop_requested.flag) によるループ終了をサポート。

- 設定管理モジュールを追加／強化
  - src/kabusys/config.py
    - .env 自動読み込み機能を実装（プロジェクトルート（.git または pyproject.toml）を検出して .env/.env.local を読み込む）。
    - .env パースの堅牢化（`export KEY=val`、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメントの考慮など）。
    - Settings クラスを実装し、J-Quants / kabuAPI / LINE / DB パス / 監視しきい値 / 環境判定等のプロパティを提供。
    - Paper Trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）をサポート。

- 設定ウィザード CLI を追加
  - src/kabusys/config_setup.py
    - 対話式で .env を作成・更新するウィザードを実装。
    - 各項目の説明、デフォルト値、シークレットマスク表示、保存確認などの機能を提供。
    - .env 書き込みはテンプレート形式で行い、重要な注意書きを含める。

- 設定検証 CLI を追加
  - src/kabusys/validate_config.py
    - .env と config/*.yaml の起動前チェックを行うツールを実装。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ存在確認、YAML パースチェック（PyYAML が存在する場合）などを実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- 運用ツールを追加
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを実装。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（平均/最大/P95）を算出して PASS/FAIL 判定を行う。
    - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH（未指定時 data/paper_trading.db）。
    - レポート期間指定（--from / --to）に対応。

- ポートフォリオ構築・リスク調整・ポジションサイジング関数群を追加
  - src/kabusys/portfolio/
    - portfolio_builder.py
      - シグナルから候補抽出 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - risk_adjustment.py
      - セクター集中上限の適用 (apply_sector_cap)、マーケットレジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。
    - position_sizing.py
      - risk_based / equal / score の配分方法に対応した発注株数計算を実装。
      - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer を用いた保守的コスト見積り、端数配分アルゴリズムを実装。

- ロギング・プロセス制御ユーティリティを追加
  - src/kabusys/utils/logging_setup.py
    - 全アプリ共通のロギング設定ユーティリティを実装。StreamHandler（stdout）と日次ローテートファイル（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR の自動作成、作成失敗時のフォールバック、既存ハンドラのクリーンアップを実装。
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを実装。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供。
    - 権限不足や非対応 OS の場合は警告を出して安全にスキップ。

- リサーチ用ファクター算出モジュール（基礎）を追加
  - src/kabusys/research/factor_research.py
    - Momentum / Value / Volatility / Liquidity などのファクター計算方針と定数を実装。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計（calc_momentum の実装開始を含む）。

- パッケージメタ情報
  - src/kabusys/__init__.py にバージョン 0.1.0 を追加。

### Changed（変更）
- DB ハンドリング方針の明示
  - 監視（run_monitoring）は環境にかかわらず本番の sqlite_path を使用して監視テーブルを一元化する方針を明記。
  - 実行（run_execution）は paper_trading 環境時に専用 DB を利用する実装で本番 DB から分離。

- .env 自動ロードの挙動
  - プロジェクトルート探索を行い、OS 環境変数 > .env.local > .env の優先順位で読み込む。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを抑止可能（テスト等で利用）。

- ログ出力の標準化
  - stdout を StreamHandler に利用することで cron / Task Scheduler との統合を考慮。

### Fixed（修正／改善）
- .env のパース耐性を強化
  - クォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメントの扱いなどを改善し実運用での .env 設定ミスを低減。

- ポジションサイズ算出の現実運用向け改善
  - 単元株（lot_size）丸め・aggregate スケールダウン・端数配分ロジックを追加して発注株数の安定性を向上。
  - price 欠損時のスキップやログ出力で診断可能に。

- 監視ループの堅牢化
  - check_once() 内で発生した例外を捕捉してログに残し、次のポーリングに継続するように実装。

### Documentation（ドキュメント）
- 各モジュールに docstring を追加し、設計意図・使用法・引数説明を明記（特に portfolio / research / utils / CLI スクリプト）。

### Known issues / Notes（既知の注意点）
- research/factor_research.py の calc_momentum 実装は途中（ファイル末尾が途切れた状態）。完全実装は今後の作業予定。
- 一部 TODO（例: position_sizing の将来的な銘柄別 lot_size サポート、price 欠損時の価格フォールバックなど）が存在する。
- set_process_priority / set_cpu_affinity は権限・プラットフォームに依存するため、失敗した場合は警告ログでスキップされる挙動となります。
- config_setup による .env の生成はセキュリティ上 .env を Git にコミットしない旨を強く推奨。

---

今後のリリースでは、factor_research の完全実装、Strategy モジュール（シグナル生成）、ExecutionEngine の細部実装やテストカバレッジの強化、運用監視アラート（LINE 通知等）の実装・統合を予定しています。README や運用ドキュメントの追加も検討中です。