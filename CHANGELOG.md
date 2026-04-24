CHANGELOG
=========

すべての変更は Keep a Changelog の方針に準拠して記載しています（日本語）。

[0.1.0] - 2026-04-24
--------------------

Added
- 初回リリース: KabuSys 基本機能を追加。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、BrokerClientFactory を介して実ブローカー / MockBrokerClient を切り替え可能。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止は data/stop_requested.flag によるファイルフラグで制御。
- 設定・起動支援 CLI
  - config_setup.py: .env を対話式に作成・更新するウィザードを追加。必須/任意項目、シークレット入力、保存確認などを提供。
  - validate_config.py: 環境変数および config/*.yaml を起動前に検証する CLI を追加。--strict モードで警告を失敗扱いにできる。
- 設定管理
  - config.py: Settings クラスを導入。.env の自動読み込み（プロジェクトルート検出 .git / pyproject.toml に基づく）、.env のパース強化（export プレフィックス、クォート内エスケープ、インラインコメントの扱い）を実装。保護された OS 環境変数を上書きしない読み込みロジックを採用。
  - 環境変数のプロパティを提供（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグ関連、閾値設定など）。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ログ初期化関数 setup_logging を追加。コンソール (stdout) と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに設定。既存ハンドラの二重追加を防止し、ログディレクトリ作成失敗時はファイル出力をスキップしてフォールバックする。
  - utils/process_priority.py: set_process_priority / set_cpu_affinity を追加。Windows / POSIX を透過的に扱い、権限不足などの例外は警告でフォールバック。
- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio/portfolio_builder.py: 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を追加。スコア全ゼロ時のフォールバック警告あり。
  - portfolio/risk_adjustment.py: apply_sector_cap（セクター集中上限による候補除外）、calc_regime_multiplier（市場レジームに応じた投下資金乗数）を追加。未知レジーム時のフォールバック挙動を明記。
  - portfolio/position_sizing.py: calc_position_sizes を追加。allocation_method に「risk_based」「equal」「score」をサポート。単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り、残余キャッシュを用いた切り上げロジックなどを実装。
- 監視・検証ツール
  - tools/paper_verification_report.py: Paper Trading 向け検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率、注文成立率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定する。閾値（稼働率 99%、成立率 90%、送信率 95%、P95レイテンシ 200 ms）をデフォルトで定義。
- パッケージ情報
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
- .env パーサの堅牢化（config._parse_env_line）
  - export KEY= 値、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いを改善。無効行のスキップや key 未指定時の安全な処理を実装。
- ログ設定の既存ハンドラ処理を明確化
  - setup_logging は既に設定済みのハンドラを flush/close のうえ削除してから再設定するようにして、二重出力を防止。
- DB 接続方針
  - 監視系（run_monitoring）は環境にかかわらず（KABUSYS_ENV に依存せず）本番 sqlite_path を使用する仕様を明確化。run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離。
- プロセス優先度設定タイミング
  - run_execution / run_monitoring の起動直後に set_process_priority("high") を呼ぶようにして、起動処理全体の優先度を上げる。

Fixed
- 環境変数値の妥当性チェック強化
  - MONITOR_POLL_INTERVAL のパースで負の値や 0 を検出してデフォルト（60 秒）にフォールバックするようにし、time.sleep に渡す不正値による例外を回避。
  - Settings.paper_fill_mode は有効値を検証し、不正な値で ValueError を送出するようにした。
  - Settings.env / log_level の妥当性チェックを追加し、不正値時に明確なエラーを発生させる。
- 実行中停止制御の改善
  - run_execution/run_monitoring ともに data/stop_requested.flag と pid ファイルを用いた停止検出・停止処理を追加。スレッド終了待ちや DB 接続のクローズを finally ブロックで確実に行うようにしてリソースリークを防止。
- validate_config のチェック強化
  - 必須環境変数の未設定・プレースホルダ値検出、DB パスの親ディレクトリ存在チェック、PyYAML 未導入時の挙動（YAML 内容検証のスキップ）を追加。KABUSYS_ENV=live 時の追加ガード（LINE 未設定、KILL_FLAG_CLEAR_ON_START 設定）も実装。

Notes / Known limitations
- research/factor_research.py は一部実装（calc_momentum）を含むがスニペットの終端で切れており、完全なファクター計算パイプラインは今後の実装が必要。
- position_sizing の価格フォールバック（前日終値や取得原価など）が未実装のため、価格欠損時にエクスポージャーや発注量の過少見積りが起きる可能性がある（TODO コメントあり）。
- process_priority / cpu_affinity は権限やプラットフォームによっては適用されない場合があり、その際は警告ログでフォールバックする。

今後の予定（提案）
- research モジュールの完全実装（ファクター正規化・結合、Signal 生成パイプラインの追加）。
- 個別銘柄の lot_size をマスタ化して銘柄別単元対応。
- テストカバレッジ（特に .env パーサ、position_sizing の集計・スケーリングアルゴリズム）拡充。
- 実運用（live）向けの安全ガード強化（発注前の事前シミュレーション・サンドボックスモード等）。

-----