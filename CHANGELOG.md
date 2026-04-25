# Changelog

すべての重要な変更は "Keep a Changelog" の形式に従って記載しています。  
このファイルでは、提供されたコードベースの内容から推測される追加・変更点をまとめています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

現在のバージョンはパッケージ定義（src/kabusys/__init__.py）に基づき 0.1.0 としています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-25
初回リリース。本リリースでは自動売買システムの基盤となる設定管理、ランナー、ユーティリティ、ポートフォリオ構築・リスク調整・ポジションサイジングの純粋関数群、ペーパートレード検証ツールなどを導入しました。

### Added
- 起動スクリプト / エントリポイント
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検知・優雅終了対応。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレード DB（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを作成（モック/実ブローカ切替）。
    - ExecutionEngine をバックグラウンドスレッドで動作させ、停止フラグで停止。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイル管理を行う。

- 設定管理・ユーザー補助
  - config.py: 環境変数/ .env 自動読み込みと Settings クラスを提供。
    - プロジェクトルート検出（.git / pyproject.toml）に基づく .env 自動読み込み（.env, .env.local）。
    - .env のパースはクォートやエスケープ、コメントに堅牢に対応。
    - 各種設定プロパティ（DB パス、PID パス、閾値、paper_trading 関連設定など）を定義。
    - PAPER_FILL_MODE の検証、環境種別（development/paper_trading/live）の検証を実装。
  - config_setup.py: インタラクティブな .env 作成/更新ウィザードを追加。
    - 秘匿項目は入力時にマスクし、.env の書き出しテンプレートを整備。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース確認（PyYAML が利用可能な場合）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（デフォルト logs/<app>.log、30日分保持）をルートロガーにセット。
    - LOG_LEVEL / LOG_DIR の解決順を実装し、ディレクトリ作成失敗時はファイル出力をスキップして続行するフォールバックを用意。
  - utils/process_priority.py: プラットフォーム非依存のプロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX(Linux/Mac/FreeBSD) を吸収し、アクセス権限不足などの例外時は警告ログでスキップ。
    - set_cpu_affinity により最初の N コアに固定する機能を提供。

- ポートフォリオ構築関連（純粋関数群、メモリ内計算）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順・同点は signal_rank でタイブレークして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分（全スコアが 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限（max_sector_pct）を適用して候補銘柄を除外。
    - calc_regime_multiplier: market レジーム ("bull","neutral","bear") に応じた投下資金乗数を返す（デフォルト・未知はフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based","equal","score"）に応じて発注株数を算出。単元株（lot_size）で丸め、ポジション上限・aggregate cap によりスケールダウン、残差を大きい順に再配分するロジックを実装。
    - 手数料・スリッページ見積り用 cost_buffer を考慮した見積り。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite を読み取って検証レポートを生成する CLI を追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシなどを算出し、閾値に基づく PASS/FAIL 判定を出力。
    - フィルタ期間指定（--from / --to）や DB パス指定（--db / 環境変数）に対応。
    - 閾値はソースに定義（稼働率 99% など）。

- 研究用ファクタ計算モジュール（基盤）
  - research/factor_research.py: DuckDB を使ったモメンタム等のファクタ計算モジュールを追加（モジュール設計・関数シグネチャ、定数群を含む）。（一部実装が続く／未完の箇所あり）

### Changed
- ログ出力の取り扱い
  - logging_setup ではコンソール出力を stdout に統一（stderr ではなく）。これは cron / Task Scheduler 等でのリダイレクト運用を考慮した設計。
- DB 初期化の扱い
  - run_execution.py / run_monitoring.py 内で init_monitoring_db を呼び、監視テーブルが存在することを保証（冪等に実行）。

### Fixed / Robustness
- .env のパース処理を強化
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなどを考慮してより堅牢に値を読み取るように実装。
- ログディレクトリ作成失敗やファイルハンドラ作成失敗の際にアプリが致命的終了しないようにフォールバックを実装。
- process_priority の実行で権限不足などにより例外が発生した場合は警告ログを出してスキップするようにして、安全に起動できるようにした。

### Known issues / Notes
- research/factor_research.py は設計と一部ロジックが含まれていますが、ソース提供時点では関数の実装が途中で切れている（未完）箇所があります。実利用前に完全実装と単体テストが必要です。
- 一部 TODO コメント（例: position_sizing の価格フォールバック、risk_adjustment の price 欠損処理）あり。実運用では過去終値やマスタデータの導入検討が推奨されます。
- run_monitoring の設計では「監視は環境に関係なく本番 sqlite_path を使用する」旨の注記があります。これは意図的な設計（監視データを一元に保存）と思われますが、テスト環境で別 DB を使いたい場合は注意が必要です。

---

（補足）リリース日・バージョンはコード内の __version__ と現在日付から推測して設定しています。必要に応じて日付やバージョンは調整してください。