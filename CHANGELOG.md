CHANGELOG
=========

すべての注目すべき変更はこのファイルで管理します。  
フォーマットは Keep a Changelog に準拠します。

Unreleased
----------

（ここは次のリリースまで未使用）

0.1.0 - 2026-04-19
-----------------

Added
- 基本モジュールと CLI を追加（初回リリース）。
  - kabusys パッケージのバージョンは `__version__ = "0.1.0"`。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（BrokerClientFactory が生成）を利用し、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）へ記録して本番 DB と分離。
    - ExecutionEngine をデーモンスレッドで実行し、data/stop_requested.flag を検知すると安全に停止。実行中は PID ファイル（data/execution.pid）を使用。
    - 起動時にプロセス優先度を "high" に設定。
    - RiskManager のデフォルト設定を組み立てて渡す（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。初期ポートフォリオ値は broker.get_available_cash() を参照。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告。
    - 監視は KABUSYS_ENV に依らず本番用 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。ループは data/stop_requested.flag を監視して終了。
    - duckdb との接続も確立。
- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。.env（優先度低）と .env.local（上書き）を読み込み、OS 環境変数は保護（上書きされない）。
    - .env のパースはシングル/ダブルクォート、エスケープ、インラインコメントなどに対応。読み込み失敗は警告で処理。
    - Settings クラスを導入し、アプリケーション設定をプロパティ経由で提供（J-Quants トークン、kabu API パスワード、DB パス、各種監視閾値、環境判定プロパティ等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - paper_sqlite_path、pid/kill flag の設定、kill_flag_clear_on_start 等の追加。
- 設定ユーティリティ / 検証
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。シークレット項目のマスク表示、選択肢・デフォルトサポート、途中キャンセル対応。
  - validate_config.py
    - 起動前に .env や config/*.yaml の不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パス親ディレクトリの存在チェック、config/*.yaml の存在・パースチェック（PyYAML が無ければスキップして警告）。
    - --strict オプションで警告も FAIL 扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定関数 setup_logging を提供。
    - stdout 出力用 StreamHandler と日次ローテート（TimedRotatingFileHandler）でログファイル出力（デフォルト logs/<app_name>.log、30 日保持）。
    - LOG_DIR 作成失敗時はファイル出力をスキップして stdout のみで継続。
    - ログレベル決定ロジック（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（権限や未対応 OS では警告を出して安全にスキップ）。
- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を抽出（同点時は signal_rank 昇順でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重の重み計算。全スコア 0 時は警告を出して等分配にフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存エクスポージャーが閾値（max_sector_pct）を超える場合、そのセクターの新規候補を除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に基づく投下資金乗数を提供。未知レジームは警告して 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数計算を実装。
    - risk_based: リスク許容率（risk_pct）と stop_loss_pct に基づく個別目標株数を計算。
    - equal/score: 重みと価格から個別割当を計算。lot_size（単元株）で丸め、_max_per_stock による per-stock 上限を適用。
    - aggregate cap: 合計投資額が利用可能現金を超える場合はスケールダウンし、残余で端数を lot_size 単位で再配分するロジックを実装。cost_buffer を用いた保守的なコスト見積り対応。
- 分析・レポートツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs などから稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）を集計。
    - Pass/Fail 基準（デフォルト）を設定: 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。期間指定 (--from / --to) と DB パスの指定オプションをサポート。
    - P95 計算、データ不足時の N/A の扱い、SQLite が存在しない場合のエラーメッセージを実装。
- 研究用ファクター計算（骨格）
  - research/factor_research.py
    - Momentum 等のファクター計算モジュールの骨格を追加（duckdb 接続を前提に prices_daily / raw_financials を参照する設計）。モジュール設計の説明と定数群を実装（関数 calc_momentum 等の開始）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / Implementation details
- .env 自動読み込みはデフォルトで有効。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- .env のロードでは OS 環境変数を保護（既存の環境変数は上書きされない、.env.local は override=True で上書きするが protected キーは例外）。
- run_monitoring は MONITOR_POLL_INTERVAL に 0 以下や不正値が設定された場合に警告しデフォルトにフォールバックする（time.sleep の ValueError を回避）。
- ログディレクトリ作成や psutil による優先度設定は権限の問題や未対応環境で失敗する可能性に配慮し、失敗時は警告して進行する設計。

今後の TODO / 改善案
- portfolio.position_sizing: 銘柄ごとの lot_size をサポートするための拡張（stocks マスタ参照など）。
- risk_adjustment.apply_sector_cap: 価格欠損時のフォールバック（前日終値や取得原価）を利用してエクスポージャーの過少見積りを防止。
- research/factor_research: ファクター計算の完全実装（calc_momentum の続きなど）。
- テストカバレッジの追加（config パーサ、ウィザード、各ポートフォリオ関数、report ツール等）。

-- end --