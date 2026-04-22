# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、重要度の高い変更をカテゴリ別に整理しています。

最近の変更履歴
----------------

### Unreleased
- Added
  - research/factor_research モジュール（ファクター計算基盤）を追加。DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 系のファクターを計算する設計を導入。関数は DuckDB の prices_daily / raw_financials テーブル参照を前提としており、分析パイプラインで再利用可能な純粋関数を目指す。
- Changed
  - research モジュール内の実装は一部未完（ファイル末尾で途中終了）であり、追加実装・テストが必要。今後 P95 等の計算や欠損データ処理の堅牢化を予定。
- Notes / TODO
  - factor_research の実装完了（欠損ハンドリング、SQL チューニング、ユニットテスト追加）を次のリリースで行う予定。

### 0.1.0 - 2026-04-22
初期リリース。以下の主要機能を含む。

- Added
  - 実行系 / 監視系 起動スクリプト
    - run_execution.py
      - ExecutionEngine を起動する CLI スクリプト。
      - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録して本番 DB と完全分離。
      - 実行中は execution.pid を生成・利用し、data/stop_requested.flag による安全停止をサポート。
      - 起動時にプロセス優先度を "high" に設定。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
      - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用。
      - 停止フラグ（data/stop_requested.flag）を検知して安全にループを終了。

  - 設定管理・CLI
    - config.py
      - 環境変数をラップする Settings クラスを提供。.env 自動読み込み（.env と .env.local、OS 環境変数を保護する挙動）と、各種設定プロパティを実装（DB パス、paper_trading 用パス、閾値、PID / kill フラグパスなど）。
      - PAPER_FILL_MODE 等の検証ロジックや KABUSYS_ENV のバリデーションを実装。
    - config_setup.py
      - 対話式ウィザードで .env を初期作成・更新する機能を追加。デフォルト・既存値の取り扱い、シークレットのマスク表示、最終確認後に .env 書き込みを行う。
    - validate_config.py
      - 起動前チェック用 CLI。必須環境変数やパスの存在、config/*.yaml の存在・パース（PyYAML 有無に応じてスキップ）などを検証し、errors/warnings/infos を出力。--strict モードで警告を失敗扱いにできる。

  - ポートフォリオ構築ライブラリ（純粋関数群、DB 参照なし）
    - portfolio.portfolio_builder
      - select_candidates: シグナルのスコア順で候補選定（タイブレークに signal_rank を使用）。
      - calc_equal_weights: 等金額配分。
      - calc_score_weights: スコア正規化配分（全銘柄のスコアが 0 の場合は等分へフォールバック）。
    - portfolio.position_sizing
      - calc_position_sizes: 複数の配分方式（risk_based / equal / score）を実装。単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）によるスケールダウン、コストバッファの考慮、残差を考慮した追加配分ロジックを実装。
    - portfolio.risk_adjustment
      - apply_sector_cap: セクター集中上限チェック（既存保有のエクスポージャー計算、当日売却予定銘柄の除外、"unknown" セクターは除外しない）。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは 1.0 でフォールバック）。

  - ユーティリティ
    - utils/logging_setup.py
      - 統一ログ設定ユーティリティを提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
      - ログレベル・ログディレクトリの解決順を明記（引数 > 環境変数 > デフォルト）。
    - utils/process_priority.py
      - Windows / POSIX の差分を吸収してプロセス優先度を設定するユーティリティ（high/normal/low）。CPU affinity を最初の N コアに固定する set_cpu_affinity() も提供。権限不足や未対応 OS の場合は警告を出してスキップする堅牢な実装。

  - モニタリング DB 初期化と SystemMonitor 連携
    - monitoring.monitoring_db.init_monitoring_db を呼び出して監視用テーブルの存在を保証する（冪等）。
    - SystemMonitor（監視の実体）は実行スクリプトから初期化して定期チェックを実行。

  - ペーパートレード検証ツール
    - tools/paper_verification_report.py
      - Paper Trading 用 SQLite DB（デフォルト data/paper_trading.db）から期間集計レポートを生成する CLI。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、閾値（稼働率 99%、成功率 90% 等）に基づいて PASS/FAIL 判定を行う。P95 計算や欠損データの扱いも実装。

  - パッケージメタ
    - __init__.py にてバージョンを "0.1.0" として設定。

- Changed
  - N/A（初期リリース）

- Fixed
  - N/A（初期リリース）

- Security
  - 環境変数ファイル（.env）は Git にコミットしないよう README 等で注意喚起（config_setup にも警告コメントを出力）。

重要な動作・運用上の注意
- run_monitoring は MONITOR_POLL_INTERVAL に不正な値が与えられた場合、デフォルト 60 秒にフォールバックして警告ログを出す。
- run_execution は paper_trading モードの際に paper_trading DB を使用し、本番データと完全分離する設計（本番誤発注防止）。
- Settings は自動で .env / .env.local を読み込むが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化できる（テスト用途）。
- logging_setup はログディレクトリ作成に失敗した場合でもアプリは継続し、コンソールログのみで動作するようにしている。
- process_priority の設定は OS の制約や権限により失敗する可能性があり、その場合は警告ログを出してスキップする。

既知の制限・今後の予定
- research/factor_research モジュール（ファクター計算）は実装途中の箇所があり、追加の実装・テストが必要（Unreleased にて管理）。
- 将来的には単元株（lot_size）を銘柄ごとに扱えるよう stocks マスタへの拡張を予定（position_sizing 内に TODO コメントあり）。
- price 欠損時のフォールバック（前日終値や取得原価の利用）は現状未実装。セクターエクスポージャー計算で過少見積りとなる可能性があるため、将来的な改善を検討。

-----

この CHANGELOG はソースコードから判別できる実装内容・設計意図に基づいて作成しています。差分ベースの厳密な履歴が必要な場合は、git のコミットログと併せて確認してください。