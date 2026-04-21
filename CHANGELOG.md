Changelog
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) の形式に従って記載しています。

v0.1.0 - 2026-04-21
-------------------

Added
- 基本コンポーネントと CLI を追加（初回リリース）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告ログを出力。
    - 監視は環境設定（KABUSYS_ENV）にかかわらず本番用の sqlite_path を使用する点を明示。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) を検知して安全にループを終了。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の MockBrokerClient を使い、Paper Trading 用 DB（data/paper_trading.db、PAPER_TRADING_SQLITE_PATH で上書き可）に記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 実行中は停止フラグを監視し、フラグ検知時に engine.stop() を呼び安全停止。
  - config.py
    - Settings クラスを導入し、環境変数から各種設定をプロパティ経由で取得するユーティリティを追加。
    - .env 自動ロード機能を追加（プロジェクトルートを .git / pyproject.toml から検出）。優先順位: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードの無効化が可能。
    - .env のパースロジックはクォート、エスケープ、先頭の "export " を扱うよう強化。
    - 各種設定プロパティを提供（例: duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, CPU/メモリ/ディスク閾値, PAPER_FILL_MODE 等）。PAPER_FILL_MODE の妥当性チェックあり。
  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等)、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML パース確認（PyYAML があれば）等を実行。
    - --strict オプションで警告も失敗扱いにできる。
  - config_setup.py
    - .env の対話式ウィザードを追加。初期作成・更新を支援。
    - 既存 .env の読み込み・マスク表示、デフォルト提示、シークレット入力、書き込み処理を提供。
    - 書き込み後に validate_config 実行を促すメッセージを表示。
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db。--db または PAPER_TRADING_SQLITE_PATH で指定可能。
    - P95 の計算ロジック、閾値（稼働率 99%、成功率 90% 等）を実装。
  - portfolio モジュール
    - portfolio_builder.py
      - select_candidates: スコア降順、同点は signal_rank 昇順で上位 N を選択。
      - calc_equal_weights: 等金額配分を計算。
      - calc_score_weights: スコア比率で重み付け。全スコアが 0 の場合は等金額配分にフォールバックして警告ログを出力。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中を防ぐため、既存ポジションのセクター比率が上限を超える場合に新規候補を除外（"unknown" セクターは適用除外）。売却予定銘柄をエクスポージャー計算から除外可能。
      - calc_regime_multiplier: market レジームに応じた資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告のうえ 1.0 にフォールバック。
    - position_sizing.py
      - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づいて発注株数を計算。lot_size（単元株）を考慮し、1銘柄上限・ポートフォリオ上限・cost_buffer（スリッページ・手数料見積り）を反映して aggregate cap によりスケールダウン・端数調整を行うロジックを実装。
  - utils
    - logging_setup.py
      - 統一ログ設定ユーティリティを追加。stdout (StreamHandler) と日次ローテートのファイルハンドラ (TimedRotatingFileHandler) をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして警告出力。
      - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
    - process_priority.py
      - プロセス優先度および CPU affinity 設定ユーティリティを追加。Windows/Linux/Mac の差分を吸収し psutil を使用。失敗時は警告を出して安全にフォールバック。
  - package メタデータ
    - __init__.py に __version__ = "0.1.0" を追加。

Changed
- なし（初回リリースのため既存挙動の変更はありません）。

Fixed
- なし（初回リリース）。

Notes / Important details
- 監視モジュール（run_monitoring）は「環境にかかわらず」本番用 sqlite_path を参照します。環境分離が必要な場合は設定や運用フローで対応してください。
- .env の自動ロードはプロジェクトルート検出に依存します（.git または pyproject.toml があるディレクトリ）。プロジェクトルートが特定できない場合は自動ロードをスキップします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- config_setup により生成された .env は絶対に Git へコミットしないでください（脚注も README に含める想定）。
- Paper Trading は本番 DB と完全分離するため、環境変数と Settings.is_paper を用いて paper_sqlite_path を切り替えます。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力しますが、LOG_DIR 環境変数や setup_logging の引数で変更可能です。
- process_priority と CPU affinity の設定は権限や OS によって無効化される場合があります。その際は警告ログが出力されます。

開発者向けコマンド（主な使い方）
- .env の対話式生成/更新:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

謝辞
- 初回リリースにあたり、設定と運用を容易にするための CLI とユーティリティ群を整備しました。今後は strategy や execution のコアロジック、バグ修正、テストの充実を予定しています。