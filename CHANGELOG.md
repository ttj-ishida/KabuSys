# Changelog

すべての重要な変更をここに記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  
<https://keepachangelog.com/ja/1.0.0/>

※ 表記は日本語です。

## [0.1.0] - 2026-04-24

### Added
- パッケージ初期リリース。以下の主要コンポーネントを追加。
  - 実行・監視スクリプト
    - run_execution.py
      - ExecutionEngine 起動用エントリポイントを追加。
      - KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用。
      - 起動時にプロセス優先度を "high" に設定。
      - 停止制御: data/stop_requested.flag を監視し、flag 検知でエンジンを停止。
      - PID ファイル管理（data/execution.pid）。
      - BrokerClientFactory を用いてブローカークライアントを抽象化。
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
      - RiskManager のデフォルト設定 (max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等) を導入。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動用エントリポイントを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視実行時は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して監視データを記録。
      - 起動時にプロセス優先度を "high" に設定。
      - 停止制御: data/stop_requested.flag を検知してループ終了。
  - 設定・環境管理
    - config.py
      - 環境変数および .env の自動読み込みを実装（プロジェクトルートを .git または pyproject.toml で探索）。
      - .env/.env.local の読み込みルール（OS 環境変数の保護、上書き制御）を導入。
      - 複数の設定プロパティを提供（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / システム環境等）。
      - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
      - KABUSYS_ENV, LOG_LEVEL のバリデーション。
    - config_setup.py
      - .env 作成・更新の対話式ウィザードを提供（テンプレート生成・既存値読み込み・シークレットマスク等）。
      - .env の書き込みフォーマットを定義（Git にコミットしない旨のヘッダ付き）。
  - 設定検証
    - validate_config.py
      - .env と config/*.yaml の基本的な妥当性検証 CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パス／YAML の存在とパース確認、live 環境向けの追加ガードを実装。
      - --strict モードで警告を失敗扱いにできる。
  - ロギング / プロセス制御ユーティリティ
    - utils/logging_setup.py
      - ルートロガー設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
      - LOG_DIR / LOG_LEVEL の解決優先順を実装。ディレクトリ作成失敗時は file handler をスキップして stdout のみで継続。
    - utils/process_priority.py
      - Windows と POSIX（Linux/macOS 等）を吸収したプロセス優先度設定関数を追加（high/normal/low）。
      - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供（アクセス権限がない場合は警告を出してスキップ）。
      - 許容できる失敗はログ警告で扱い、安全にフォールバック。
  - 監視関連
    - monitoring.monitoring_db.init_monitoring_db（初期化呼び出しを利用）
    - monitoring.system_monitor（SystemMonitor 本体は別ファイルに実装済みを想定）
  - ポートフォリオ構築関連（純関数）
    - portfolio/portfolio_builder.py
      - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
      - スコアが全て 0 の場合は等金額配分にフォールバックし警告を出す。
    - portfolio/risk_adjustment.py
      - セクター集中制限を行う apply_sector_cap を追加（当日売却予定銘柄の除外、unknown セクターは制限対象外）。
      - レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear とフォールバック）。未知レジームは警告して 1.0 フォールバック。
    - portfolio/position_sizing.py
      - position size（発注株数）計算: allocation_method に応じた計算（risk_based / equal / score）を実装。
      - リスクベースの計算、per-stock cap、lot_size（単元株）での丸め処理、aggregate cap によるスケーリングと端数配分ロジックを実装。
      - 手数料・スリッページ見積り用 cost_buffer を考慮した集計判定を導入。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 用の検証レポート生成スクリプトを追加。
      - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定を行う。
      - 日付フィルタオプション（--from/--to）、--db による DB 指定をサポート。
      - P95 計算、および各クエリでテーブル未存在時のフォールバック処理を実装。
  - 研究用基盤（未完の部分を含む）
    - research/factor_research.py
      - ファクター計算モジュールの骨組みを追加（Momentum / Value / Volatility / Liquidity を想定）。
      - DuckDB 接続を取る設計、calc_momentum のドキュメント化と定数を導入（実装途中の箇所あり）。

### Changed
- n/a（初回リリースのため変更履歴はありません）。

### Fixed
- n/a（初回リリースのため修正履歴はありません）。

### Notes / Implementation details
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされるため、配布後にも安全に動作する。
- ログは stdout にも出力する設計のため、cron やコンテナ実行時のログ取り回しを容易にしている。
- 実行系（ExecutionEngine）は paper_trading と本番 DB を明確に分離しているため、ペーパートレード時に本番データを汚すリスクを低減。
- process_priority や CPU affinity は権限不足等で失敗する可能性があり、その場合は警告ログを出して処理を続行する実装。
- 一部モジュール（例: research.calc_momentum）は実装が途中の箇所を含むため、今後の追加実装・テストが必要。

## 参考
- パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" として定義されています。

----- 

今後のリリースでは、既存機能のテストカバレッジ拡充、research モジュールの完成、ExecutionEngine / SystemMonitor の詳細実装および運用改善（エラーハンドリング、メトリクス強化）を予定しています。