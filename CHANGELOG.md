Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

[Unreleased]: https://example.com/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/releases/tag/v0.1.0

0.1.0 - 初回リリース
-------------------

リリース日: (初回リリース)

Added
- 基本アプリケーションとユーティリティ群を追加。
  - パッケージ情報
    - kabusys.__version__ = "0.1.0"
  - 環境・設定管理
    - kabusys.config
      - .env 自動ロード（プロジェクトルートの .env / .env.local を優先順に読み込み）。
      - .env パーサ（コメント・クォート・export 形式対応）。
      - Settings クラスを提供し、環境変数から各種設定値（J-Quants、kabu API、DB パス、監視閾値、実行環境など）を取得可能。
      - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH 等のデフォルト値と検証ロジックを実装。
    - kabusys.config_setup
      - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
      - デフォルト値・選択肢・シークレット項目表示（マスク）に対応。
    - kabusys.validate_config
      - .env と config/*.yaml の設定検証 CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ確認、YAML パース検証（PyYAML があれば）を提供。
      - --strict モードで警告を失敗として扱う。
  - 実行 / 監視エントリポイント
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db デフォルト）を使用し、本番 DB と完全分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行。
      - 停止フラグ (data/stop_requested.flag) と PID ファイルの取り扱い。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
      - 監視は KABUSYS_ENV に関わらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用する動作を明記。
      - stop フラグ検出で優雅にループを終了。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - kabusys.portfolio.portfolio_builder
      - select_candidates: BUY シグナルのソート・上位 N 選出。
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）。
    - kabusys.portfolio.risk_adjustment
      - apply_sector_cap: セクター集中を防ぐ候補フィルタリング（sell_codes を除外）。
      - calc_regime_multiplier: レジーム（bull/neutral/bear）に基づく投下資金乗数。
    - kabusys.portfolio.position_sizing
      - calc_position_sizes: allocation_method に応じた発注株数計算（risk_based / equal / score）、単元（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り実装。
  - 研究用ファクター計算
    - kabusys.research.factor_research
      - DuckDB 接続を受け取り、Momentum / Volatility（ATR, turnover, volume_ratio 等）を計算する関数を追加。
      - prices_daily テーブルを想定した SQL + Python 実装。
  - ツール
    - kabusys.tools.paper_verification_report
      - Paper Trading 検証レポート生成 CLI を追加。
      - 稼働率 (uptime)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシなどを算出し、PASS/FAIL 判定を行う。
      - --from / --to / --db オプションを提供。PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能。
  - ユーティリティ
    - kabusys.utils.process_priority
      - Windows / POSIX を抽象化したプロセス優先度設定と CPU affinity 設定を追加（psutil ベース）。
      - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。権限不足や未対応 OS 時のフォールバックと警告を実装。

Changed
- 初回公開のため該当なし（新規実装群の提供）。

Fixed
- 初回公開のため該当なし。

Notes / 重要な動作・デフォルト
- .env 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト等で利用）。
- run_monitoring は監視用 DB（Settings.sqlite_path）を用いるが、run_execution は paper_trading 環境のとき paper_sqlite_path を使用して DB 分離を行う。
- MONITOR_POLL_INTERVAL:
  - 環境変数で整数秒を指定可能。1 未満や不正値はデフォルト 60 秒にフォールバックし警告を出す。
- kill / stop フラグ:
  - data/stop_requested.flag による停止検出を両スクリプトが参照。
  - PID ファイルや kill flag のパスは Settings 経由で構成可能（PID_FILE_PATH, KILL_FLAG_PATH）。
- Paper Trading の振る舞い:
  - PAPER_FILL_MODE をサポート（instant/partial/never/reject）。無効値は ValueError。
  - デフォルト paper DB は data/paper_trading.db。ただし PAPER_TRADING_SQLITE_PATH で上書き可能。
- DuckDB と SQLite の併用:
  - 分析用に DuckDB（DUCKDB_PATH）を使用し、監視や簡易トランザクションは SQLite を使用する設計。

開発者向け備考
- validate_config は config/*.yaml の存在チェックと PyYAML による簡易パース検証を行う（PyYAML がない場合は警告してスキップ）。
- portfolio / position sizing のロジックは純粋関数として設計されており、DB 参照を行わないためユニットテストが容易。
- process_priority, CPU affinity は権限や OS により失敗する可能性があるため、失敗時は警告ログを出して処理を継続するよう安全対応済み。

Security
- .env は絶対にリポジトリにコミットしないことを .env のテンプレート・ウィザードで明記。

今後の予定（提案）
- stocks マスタに銘柄ごとの lot_size を持たせ、position_sizing を拡張する。
- price フォールバック（前日終値や取得原価）を追加して apply_sector_cap の欠損時挙動を改善する。
- ExecutionEngine / SystemMonitor の詳細実装（ログ・例外の集約、外部モニタ連携）の追加ドキュメント化。

-- End of CHANGELOG.md --