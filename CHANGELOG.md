Keep a Changelog
=================

すべての変更は https://keepachangelog.com/ja/ に準拠して記載します。

[0.1.0] - 2026-04-18
-------------------

Added
- 基本パッケージ初期実装を追加。
  - src/kabusys/__init__.py: パッケージバージョン定義 (__version__ = "0.1.0")。
- 環境・設定管理
  - src/kabusys/config.py:
    - .env/.env.local の自動ロード（プロジェクトルートを .git または pyproject.toml で検出）。
    - 行パーサ実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
    - Settings クラスを提供し、各種環境変数を型変換・検証してプロパティとして公開。
    - PAPER_FILL_MODE のバリデーション、paper_trading 用 sqlite パス、監視・閾値設定などを含む。
  - src/kabusys/config_setup.py:
    - 対話式 .env 作成/更新ウィザード（--env-file オプション対応）。シークレットマスクやデフォルト提示機能を備える。
- 設定検証 CLI
  - src/kabusys/validate_config.py:
    - .env と config/*.yaml の事前検証ツール。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パス（親ディレクトリ存在チェック）、PyYAML がなければ YAML 検証をスキップする挙動、KABUSYS_ENV=live 向けの追加警告等を実装。
    - --strict オプションで警告も失敗扱いにできる。
- 実行スクリプト
  - src/kabusys/run_execution.py:
    - ExecutionEngine 起動スクリプト（プロセス優先度の設定、DB接続、BrokerClientFactory を通じたブローカークライアント生成、依存コンポーネント（OrderRepository/OrderManager/RiskManager/Reconciler）の組み立て、スレッドでの engine.run_session 実行、停止フラグ監視）。
    - Paper trading（KABUSYS_ENV=paper_trading）の場合は専用 SQLite（デフォルト data/paper_trading.db）を用いて本番 DB と分離する設計。
    - 停止制御: data/stop_requested.flag による外部停止検知、PID ファイル管理（data/execution.pid）。
  - src/kabusys/run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する点に注意。
    - 起動時にプロセス優先度を "high" に設定、停止フラグ監視により優雅な終了。
- モニタリング DB 初期化フック（init_monitoring_db）および SystemMonitor を利用する構成（run_monitoring/run_execution から呼び出し）。
- ロギング・プロセス制御ユーティリティ
  - src/kabusys/utils/logging_setup.py:
    - 共通のログ設定ユーティリティ。stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を root ロガーに設定。ログディレクトリ自動作成、30 日分保持、既にハンドラがある場合のクリア処理。
    - ログレベル解決順（引数 → 環境変数 LOG_LEVEL → デフォルト）。
  - src/kabusys/utils/process_priority.py:
    - プラットフォーム差異を吸収したプロセス優先度設定（Windows / POSIX 対応）。CPU affinity 設定関数も提供。アクセス権限や未対応 OS の場合は安全にフォールバックして警告。
- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で候補選定（signal_rank をタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額およびスコア加重の重み計算（スコア全0 の場合は等分にフォールバックして警告）。
  - src/kabusys/portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中を抑止するフィルタリング（sell_codes を除外、"unknown" セクターは制限外扱い）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマップ、未知レジームは 1.0 でフォールバック）。
  - src/kabusys/portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づいた株数決定。単元株丸め（lot_size）、最大ポジション/利用率制約、aggregate cap スケーリング、cost_buffer（手数料・スリッページ想定）を考慮した実装。再現性のため残差ハンドリングも実装。
  - src/kabusys/portfolio/__init__.py: 上記 API をまとめてエクスポート。
- 研究モジュール（初期）
  - src/kabusys/research/factor_research.py:
    - ファクター計算基盤の追加（モメンタム・MA200乖離・ATR・出来高指標等の設計、DuckDB を用いたデータ参照設計）。（ファイルは途中まで実装されている状態。）
- ツール
  - src/kabusys/tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプト。SQLite（PAPER_TRADING_SQLITE_PATH）から以下を集計:
      - system_status（稼働率 / 総ポーリング / エラー数）
      - trade_logs（Created/Filled/Sent から成功率・送信率、レイテンシの平均/最大/P95）
      - risk_logs（リスク却下数）
    - 基準値（uptime 99%, fill rate 90%, send rate 95%, P95 latency 200ms）による PASS/FAIL 判定を出力。
    - コマンドライン引数 --from/--to/--db をサポート。
- 監視・運用関連の小機能
  - 停止フラグ (data/stop_requested.flag) によるプロセス間停止連携を採用。
  - KILL_FLAG_CLEAR_ON_START（起動時 kill flag 自動クリア）設定をサポート（Settings と validate_config で扱い、live 環境では警告）。
  - Paper trading 用の挙動分離（MockBrokerClient を用いる設計。BrokerClientFactory の使用により実運用/テスト切替を容易にする想定）。
- DB 接続
  - sqlite3 / duckdb 接続を各スクリプトで確立し、終了時にクローズする一貫した挙動を実装。
  - init_monitoring_db を実行して監視テーブルの存在を保証（冪等）。

Changed
- 初回公開のため該当なし。

Fixed
- 初回公開のため該当なし。

Security
- 初回公開のため該当なし。

Notes / 実運用上の注意
- run_monitoring は説明どおり「監視」は常に本番 sqlite_path を参照します（環境にかかわらず）。運用時に意図した DB を参照する設定を確認してください。
- run_execution は paper_trading 環境では paper_sqlite_path を使用し、本番 DB と完全分離する設計です。ペーパートレード検証時は PAPER_TRADING_SQLITE_PATH の設定を確認してください。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力をスキップして stdout のみで稼働します（失敗は stderr に出力されます）。
- process_priority / set_cpu_affinity は権限不足や未対応 OS 上で例外を吐かず警告でフォールバックするようになっていますが、期待どおり優先度が設定されない場合があります。
- config の自動ロードはプロジェクトルート検出に依存するため、配布後や CWD が特殊な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して自動ロードを無効化できます。

既知の未完了事項
- research/factor_research.py は続きの実装が必要（ファイル冒頭は設計通りだが途中で切れている）。
- BrokerClientFactory / ExecutionEngine 等の詳細な実装は本チェンジログ対象コードに含まれている依存関係に依存（ここで示した起動シーケンスは現行コードベースのコントラクトに基づく説明）。

今後の予定（例）
- factor_research の完成と単体テスト追加。
- 各モジュールの単体テスト・統合テストを追加し CI を整備。
- ロギング・監視データの保管・ローテーションポリシー強化。

--- 
このリリースはコードベースの初期機能群をまとめたものです。詳細は各モジュールの docstring およびソースコードコメントを参照してください。