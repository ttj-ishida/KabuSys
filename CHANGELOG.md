CHANGELOG
=========

すべての注目すべき変更を時系列で記録します。  
このファイルは「Keep a Changelog」形式に従っています。

0.1.0 - 2026-04-23
-----------------

Added
- 初期リリースとして以下の主要機能を追加しました。
  - 実行エントリ / 起動スクリプト
    - run_execution.py
      - ExecutionEngine 起動スクリプトを提供。プロセス優先度を "high" に設定し、スレッドでエンジンを実行します。
      - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離されます。
      - BrokerClientFactory により環境に応じたブローカークライアントを生成。
      - Engine の PID ファイル管理、停止フラグ (data/stop_requested.flag) による安全停止、thread.join による待機ロジックを実装。
      - RiskManager のデフォルト設定例を導入（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視データの一元化）。
      - 停止フラグ (data/stop_requested.flag) による終了検知、例外発生時はログ出力して次ポーリングを継続。

  - 設定管理
    - config.py
      - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
      - .env のパース実装を強化（export プレフィックス対応、シングル/ダブルクォート内でのエスケープ、インラインコメント処理）。
      - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
      - Settings クラスを導入し、環境変数をプロパティ経由で取得するインターフェースを提供。
      - 新プロパティ:
        - paper_fill_mode（PAPER_FILL_MODE、"instant"|"partial"|"never"|"reject"、不正値は例外）
        - paper_sqlite_path（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）
        - pid_file_path / kill_flag_path / kill_flag_clear_on_start
        - cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct（監視閾値）
      - env / log_level の値検証（不正値は ValueError）。
    - config_setup.py
      - 対話式ウィザードで .env の初期作成・更新を支援。複数の設定項目（J-Quants トークン、kabu パスワード、DB パス、ログレベル、KABUSYS_ENV など）を扱う。
      - シークレット項目は表示をマスク、既存 .env の読み込み・再利用に対応。
      - .env のテンプレート書き出しを実装（.env を Git にコミットしない旨を出力）。

  - 設定検証 CLI
    - validate_config.py
      - .env と config/*.yaml の設定不備を起動前に検出するコマンドラインツール。
      - 必須環境変数チェック、KABUSYS_ENV 検証、LOG_LEVEL 検証、DB パスの親ディレクトリ確認、config/*.yaml の存在確認および（PyYAML が利用可能な場合は）パース検証を実行。
      - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定の有無や KILL_FLAG_CLEAR_ON_START の危険設定の警告）。
      - --strict フラグで警告を FAIL 扱いにできる。

  - ポートフォリオ構築ライブラリ
    - package: kabusys.portfolio
      - portfolio_builder.py
        - select_candidates: BUY シグナルをスコア降順でソートして上位 N 件を選択。
        - calc_equal_weights / calc_score_weights: 等分配・スコア加重の重み計算（全スコアが 0 の場合は等分配へフォールバック）。
      - risk_adjustment.py
        - apply_sector_cap: セクター集中上限チェック（既存ポジションの時価を考慮）、"unknown" セクターは上限適用しない設計。
        - calc_regime_multiplier: 市場レジーム ("bull","neutral","bear") に応じた投資乗数を返す（未定義レジームは 1.0 にフォールバック）。
      - position_sizing.py
        - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく株数計算を実装。
        - lot_size（単元株）丸め、per-stock 上限・aggregate cap（利用可能現金に基づくスケールダウン）、cost_buffer を用いた保守的見積り、残余キャッシュによる端数配分ロジックを実装。

  - ユーティリティ
    - utils/logging_setup.py
      - 一貫したログ設定ユーティリティを提供。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log）をルートロガーに設定。
      - LOG_LEVEL, LOG_DIR の環境変数や引数で上書き可能。ログディレクトリ作成失敗時はファイル出力を無効化してコンソール出力のみ継続。
    - utils/process_priority.py
      - psutil を用いたクロスプラットフォームのプロセス優先度設定（Windows / POSIX 対応）。set_cpu_affinity による CPU 固定機能も提供。権限不足などの例外は警告出力して安全にスキップ。

  - 検証・分析ツール
    - tools/paper_verification_report.py
      - Paper Trading 用の検証レポート生成スクリプトを追加。システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計して PASS/FAIL を判定。
      - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。CLI で日付範囲や DB パスを指定可能。
      - P95 の算出、SQL クエリによる集計、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を実装。

  - リサーチ基盤（開始）
    - research/factor_research.py
      - ファクター計算モジュールの骨格を追加（モメンタム / MA200 / ATR / ボリューム等を想定）。DuckDB 接続を受け取り、prices_daily / raw_financials を用いた計算を想定した設計。

  - パッケージ情報
    - kabusys.__init__.py に __version__ = "0.1.0" を設定。主要パッケージエクスポートを定義。

Changed
- 初期リリースなので「Added」が中心。設定読み込み/パース周りは堅牢性を意識して設計（export 対応、クォート・エスケープ対応、OS 環境変数保護機構の追加）。

Fixed
- 特定の実装上の注意点・フォールバックを設けて運用上の障害を軽減:
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出してデフォルトにフォールバックし、time.sleep の ValueError を回避。
  - ログディレクトリ作成失敗／ファイルハンドラ作成失敗時にコンソール出力へフォールバック。
  - psutil によるプロセス優先度設定が権限不足で失敗した場合は警告を出してスキップ。

Notes / 注意事項
- .env ファイルは機密情報を含むため、絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも明記）。
- 本番 (KABUSYS_ENV=live) では KILL_FLAG_CLEAR_ON_START を 0（自動クリア無効）にすることを推奨します。validate_config では live 時のガードと警告を行います。
- Paper Trading と本番 DB は分離されていますが、監視（monitoring）は運用方針により本番 sqlite_path を使用する設計です。運用ルールに合わせて環境変数を調整してください。
- research/factor_research.py は計算ロジックの骨格を含みますが、実運用で使う前にさらにテストとチューニングを推奨します。

今後の予定（例）
- ExecutionEngine / SystemMonitor のユニットテスト追加
- ファクター計算の完全実装と最適化（duckdb クエリ最適化）
- 銘柄ごとの lot_size 管理（マスタデータの導入）
- ログ・監視周りのメトリクス化（Prometheus 等との統合検討）

--- 
(この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートに合わせて調整してください。)