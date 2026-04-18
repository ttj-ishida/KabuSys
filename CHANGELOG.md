Keep a Changelog
All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-18
--------------------

Added
- 初回公開リリース。
- 実行エントリ / 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用し、MockBrokerClient を想定した分離動作を実装。
    - 実行中の停止をファイルフラグ(data/stop_requested.flag)で検出し、安全に停止する仕組みを提供。
    - PID ファイル出力 (data/execution.pid) をサポート。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority）。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値(0 以下や非整数)は警告してデフォルトにフォールバック。
    - 監視処理は環境にかかわらず監視用 sqlite_path（Settings.sqlite_path、デフォルト data/monitoring.db）を用いる設計。
    - 停止フラグの検出と例外ハンドリングを行い、最後に DB 接続をクローズ。

- 設定・環境管理
  - config.py
    - .env の自動読み込み（プロジェクトルートを .git / pyproject.toml で探索）。
    - export KEY=val 形式やクォート内のエスケープ対応をした行パーサを実装。
    - OS 環境変数を保護して .env.local を上書き可能にするロード順（OS env > .env.local > .env）。
    - Settings クラスを導入し、アプリ全体で利用できるプロパティを提供（J-Quants、kabu API、DB パス、監視しきい値、環境判定等）。
    - PAPER_FILL_MODE（instant/partial/never/reject）と PAPER_TRADING_SQLITE_PATH をサポート。
    - KABUSYS_ENV の有効値は {development, paper_trading, live}。

- 設定ユーティリティ・バリデーション
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - 秘密値はマスク表示、既存 .env の再利用、デフォルト値の提示に対応。
  - validate_config.py
    - .env および config/*.yaml の設定を起動前に検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML があれば）を実行。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging を追加。
    - stdout 向け StreamHandler と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL 環境変数と引数で挙動を制御。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみ継続。
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定を追加（high/normal/low）。
    - POSIX では nice 値、Windows では優先度クラスを設定（権限不足や未対応 OS は警告でスキップ）。
    - CPU affinity 設定用 set_cpu_affinity を追加。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、同点タイブレーク）を追加。
    - calc_equal_weights（等金額配分）、calc_score_weights（スコア比例配分、全スコア 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - apply_sector_cap：セクター集中を防ぐため既存保有と当日売却予定を考慮し新規候補を除外するロジックを追加。unknown セクターは制限を適用しない。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に基づき投下資金乗数を返す。未知レジームは警告後に 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes：allocation_method（risk_based / equal / score）に応じて発注株数を決定する包括的ロジックを追加。
    - 単元株（lot_size）丸め、per-stock 上限・aggregate 上限、cost_buffer（手数料・スリッページ）の保守的見積り、利用可能現金に合わせたスケールダウン（端数再配分）を実装。
    - risk_based 方式ではリスク許容率（risk_pct）と stop_loss_pct を用いた株数算出を実装。

- 分析・検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード結果を SQLite（デフォルト data/paper_trading.db）から集計して報告する CLI を追加。
    - 指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシなどを算出。
    - デフォルトの合格基準（閾値）を設定:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - --from / --to / --db オプションで期間と DB を指定可能。
    - データが存在しない場合やテーブル欠損時にも寛容に動作し、N/A を出力。

- research/factor_research.py（骨格実装）
  - DuckDB を受け取り prices_daily テーブルを参照してモメンタム等のファクターを計算する関数群の骨格を追加（設計方針・定義を含む）。将来の拡張を想定。

Changed
- 初回リリースのため過去互換性問題はなし。

Fixed
- 該当なし（初回リリース）。

Deprecated
- 該当なし。

Removed
- 該当なし。

Security
- 該当なし。

Notes / 使用上の重要なポイント
- .env 自動ロード
  - プロジェクトルートが .git または pyproject.toml を基準に自動検出され、OS 環境変数が優先されます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 監視 DB と実行 DB の分離
  - run_monitoring は環境にかかわらず Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。
  - run_execution は paper_trading 時に PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離します。
- 環境変数の主要項目
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - 推奨/任意: KABUSYS_ENV (development|paper_trading|live), DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, LOG_DIR, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, MONITOR_POLL_INTERVAL, PAPER_FILL_MODE, KILL_FLAG_CLEAR_ON_START
- ログ
  - デフォルトで stdout 出力 + logs/<app_name>.log に日次ローテーションで出力。ログディレクトリ作成に失敗した場合は stdout のみで継続します。
- プロセス優先度
  - 起動スクリプトは初期化時に set_process_priority("high") を呼び出します。権限がない場合やプラットフォーム非対応の場合は警告を出しスキップします。
- 停止制御
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することでトリガーできます（スクリプトはループ内でこのファイルの有無を監視します）。
  - 実行エンジンは PID ファイルを書き込み、stop フラグ検知時に engine.stop() を呼んで安全停止を試みます。

今後の予定（例）
- research/factor_research の完全実装（ファクター計算 SQL 実装の追加）。
- ExecutionEngine / Broker 実装の詳細化・テストカバレッジ追加。
- 設定周りの単体テスト強化と CLI のエンドツーエンド検証。

--- 
この CHANGELOG はコードベースの現状から推測して作成しています。実際の変更履歴やリリース手順はプロジェクト運用に合わせて調整してください。