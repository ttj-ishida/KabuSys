CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従って記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-19
--------------------

Added
- 初期リリース: 基本的な自動売買フレームワーク「KabuSys」のコア機能を追加。
  - エントリポイント / 起動スクリプト
    - run_execution.py
      - ExecutionEngine を起動する CLI スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、paper_trading 専用の SQLite DB（環境変数 PAPER_TRADING_SQLITE_PATH、デフォルト: data/paper_trading.db）へ記録することで本番 DB と完全分離。
      - 起動時にプロセス優先度を High に設定するフローを追加。
      - 停止フラグ (data/stop_requested.flag) と実行 PID ファイル (data/execution.pid) に対応。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
      - 監視データ用 SQLite は監視プロセスが常に本番 sqlite_path を参照する設計（環境に依存しない）。
      - 停止フラグ検知でループを終了する仕組みを実装。
  - 設定管理
    - config.py
      - .env ファイル自動読込（プロジェクトルート検出: .git または pyproject.toml）を実装。OS 環境変数は保護され、.env.local による上書きをサポート。
      - 必須/オプション設定、デフォルト値、バリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を提供する Settings クラスを追加。
      - 各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等）および閾値（CPU/MEM/DISK）等のプロパティを提供。
  - 設定ユーティリティ
    - config_setup.py
      - 対話式ウィザードで .env を生成／更新するツールを追加。既存値の読み込み、シークレット値のマスク表示、保存確認をサポート。
    - validate_config.py
      - .env と config/*.yaml の事前検証 CLI を追加。必須環境変数チェック、パス存在チェック、YAML パース検証（PyYAML が存在する場合）、本番環境向けガードを実装。
      - --strict オプションを追加（警告を FAIL 扱いにできる）。
  - ロギング / プロセス管理ユーティリティ
    - utils/logging_setup.py
      - StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、デフォルト保存期間 30 日）をルートロガーに設定する共通ユーティリティを追加。
      - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続。
      - ログレベル・ログディレクトリ解決の優先順を実装（引数 > 環境変数 > デフォルト）。
    - utils/process_priority.py
      - プロセス優先度（high/normal/low）をクロスプラットフォームで設定するユーティリティを追加（Windows / POSIX 対応）。
      - CPU affinity を最初の N コアへ固定する set_cpu_affinity() を追加。
      - 権限不足や未対応環境でも安全にスキップする実装。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を追加。スコア合計が 0 の場合は等配分へフォールバック（警告）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限（max_sector_pct）を既存保有比率に基づいて適用し、上限を超えるセクターの新規候補を除外するロジックを追加。"unknown" セクターは除外対象外。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返すユーティリティを追加。未知レジームはフォールバック（1.0）し警告を出力。
    - portfolio/position_sizing.py
      - 各銘柄の発注株数を決定する calc_position_sizes を実装。
      - allocation_method="risk_based"/"equal"/"score" をサポート。
      - lot_size（単元株）で丸め、1銘柄上限（max_position_pct）や aggregate cap（available_cash）を考慮したスケーリングと残差処理（lot 単位で追加配分）を実装。
      - cost_buffer による手数料／スリッページの保守的見積りをサポート。
  - モニタリング / 解析ツール
    - monitoring.monitoring_db（初期化呼び出しを起動スクリプトで利用）
    - tools/paper_verification_report.py
      - Paper Trading 用の検証レポート生成スクリプトを追加。
      - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシなどを集計・出力し、閾値に基づく PASS/FAIL 判定を行う。デフォルト閾値:
        - 稼働率 >= 99.0%
        - 注文成功率 >= 90.0%
        - 送信率 >= 95.0%
        - P95 レイテンシ <= 200 ms
      - 日付フィルタ (--from/--to)、DB パス指定 (--db) をサポート。
  - 研究用モジュール
    - research/factor_research.py（ファクター計算の基盤を追加）
      - Momentum / Value / Volatility / Liquidity の設計方針と定数を整備。DuckDB 接続を受けて prices_daily / raw_financials を参照して計算する設計。モメンタム計算関数のスケルトンを含む（未完成部分あり）。
  - パッケージメタ情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Changed
- （初回リリースのためなし）

Fixed
- （初回リリースのためなし）

Notes / 補足
- 環境変数関連の主なキー:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - 実行環境: KABUSYS_ENV (development | paper_trading | live)
  - ログ設定: LOG_LEVEL, LOG_DIR
  - DB パス: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
  - 監視: MONITOR_POLL_INTERVAL, PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
  - Paper Trading 振る舞い: PAPER_FILL_MODE (instant | partial | never | reject)
- 依存:
  - duckdb, psutil が runtime に必要（環境によっては optional に扱われる箇所あり）。
  - validate_config は PyYAML が存在する場合に config/*.yaml の内容検証を行う（未インストール時は警告でスキップ）。
- ログは標準出力 (stdout) とファイル（logs/<app_name>.log）に出力されるが、ログディレクトリの作成に失敗した場合はファイル出力をスキップして stdout のみで動作するようフォールバックする。
- run_monitoring と run_execution は stop flag（data/stop_requested.flag）を監視して安全にシャットダウンできるよう設計されています。

今後の予定（予定機能・改善案）
- research/factor_research の完全実装（モメンタム等の計算ロジック完成）。
- 銘柄ごとの単元株情報（lot_size）を銘柄マスタに持たせる拡張。
- position_sizing の価格フォールバック（前日終値等）の実装。
- より詳細なテストカバレッジ追加・CI ワークフロー整備。

----