# CHANGELOG

すべての重要な変更点をこのファイルに記載します。  
以下の内容は提示されたコードベースの実装から推測してまとめたものであり、ドキュメントやコミット履歴がある場合はそちらを優先してください。

※ フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-19

### Added
- 初回リリースを追加。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV による挙動分岐:
      - KABUSYS_ENV=paper_trading の場合は Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient 系を使って本番 DB と分離して動作する想定。
    - BrokerClientFactory を経由してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。エンジンは別スレッドで run_session を実行し、data/stop_requested.flag による停止制御をサポート。
    - 起動時に監視テーブルを初期化（init_monitoring_db を呼び出し冪等的に保証）。
    - PID ファイル出力（data/execution.pid）をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db 等）を使用する旨の挙動。
    - 停止フラグ（data/stop_requested.flag）検知によるループ終了、KeyboardInterrupt での正常終了処理、例外捕捉時のログ出力を実装。
    - DuckDB へ接続している（分析用データ取り込みを想定）。

- 環境設定 / 構成管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で特定）。
    - .env のパースロジックで export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントなどに対応。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを実装し、アプリケーション設定（トークン、API URL、DB パス、各種閾値、KABUSYS_ENV 検証等）をプロパティ経由で提供。バリデーション（有効な KABUSYS_ENV や LOG_LEVEL、PAPER_FILL_MODE の列挙チェック等）を行う。
  - config_setup.py
    - 対話式 .env 作成/更新ウィザードを実装。
    - セクション化された項目定義（J-Quants、kabuステーション、LINE、DB、システム設定、Kill Switch）を用意。
    - シークレット項目は表示マスク、既存値の利用、選択肢サポート、確認プロンプトとファイル書き込み機能を提供。
  - validate_config.py
    - 起動前の設定検証 CLI を実装（python -m kabusys.validate_config）。
    - 必須/任意の環境変数確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス親ディレクトリの存在チェック、config/*.yaml の存在確認と（PyYAML がある場合の）パース検証を行う。
    - KABUSYS_ENV=live のときの安全ガード（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の警告）を追加。
    - --strict オプションで警告を FAIL 扱いにするモードをサポート。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio モジュールを追加・公開:
    - portfolio_builder.py
      - select_candidates: BUY シグナルのスコア降順ソートと上位 N 選択。
      - calc_equal_weights: 等金額配分 (1/N)。
      - calc_score_weights: スコア正規化配分（全て 0 の場合は等配分にフォールバックし警告）。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中上限チェックおよび候補除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 にフォールバックして警告）。
    - position_sizing.py
      - calc_position_sizes: 複数の allocation_method を実装（risk_based / equal / score）。
      - lot_size（単元）丸め、max_position_pct による per-stock 上限、max_utilization / available_cash による aggregate cap、cost_buffer を考慮した保守的コスト見積、スケーリングと端数配分ロジックを実装。
  - すべて DB 参照を行わない純粋関数設計（メモリ内計算）。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ロギング初期化ユーティリティを追加。
    - stdout への StreamHandler（stdout を使用）と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止。LOG_LEVEL / LOG_DIR の解決順をサポート。ログディレクトリ作成失敗時はファイル出力をスキップして警告。
  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加（set_process_priority）。
    - Windows と POSIX（Linux/Mac/FreeBSD）に対応し、psutil を利用して優先度や CPU affinity を設定（set_cpu_affinity）。
    - 設定失敗時は警告でスキップする堅牢な実装。

- モニタリング / 監視系
  - monitoring 初期 DB 初期化呼び出し（init_monitoring_db）が各起動スクリプトから呼ばれるようになり、監視テーブルの存在を保証。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加（指定期間の検証）。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数などを計算。
    - P95 計算、日付フィルタ、SQLite DB パスの解決（--db / 環境変数 / デフォルト）をサポート。
    - PASS/FAIL 判定基準（デフォルト閾値: 稼働率 99%、成功率 90%、送信率 95%、P95 <= 200ms）を実装。

- パッケージ情報
  - kabusys.__version__ を "0.1.0" に設定。

### Changed
- （初回リリースのため特になし）

### Fixed
- （初回リリースのため特になし）

### Notes / 実装上の注記（コードから推測）
- .env の自動ロードはプロジェクトルートを基準に行われ、OS 環境変数が存在する場合は上書きされない（.env.local は上書き可。ただし OS 環境変数は保護）。
- Settings のプロパティは遅延評価でアクセス時に環境変数の存在や妥当性をチェックするため、起動前に validate_config を使ったチェックを推奨。
- position_sizing などの数値ロジックは多数の安全弁（価格欠損のスキップ、lot_size 丸め、aggregate cap のスケールダウン、端数配分の安定化）を備えているが、将来の拡張（銘柄別 lot_size 等）がコメントとして示されている。
- process_priority / logging_setup はエラー時に graceful にフォールバックする設計で、cron やルート権限がない環境でも致命的にならないよう配慮されている。
- monitoring は本番用監視 DB を参照する仕様（KABUSYS_ENV に依存しない）ため、paper_trading と monitoring DB の分離運用に注意が必要。

--- 

今後のリリースには、各モジュール（ExecutionEngine, SystemMonitor, BrokerClient 実装、DuckDB スキーマ定義、config/*.yaml の具体内容）に関する変更やバグ修正、テストカバレッジの拡充を追記してください。