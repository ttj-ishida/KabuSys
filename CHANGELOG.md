CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
形式は "Keep a Changelog" に準拠します。

フォーマット:
- 各リリースは日付付きで記載
- セクションは Added / Changed / Deprecated / Removed / Fixed / Security を使用

[Unreleased]
------------

（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-19
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本コンポーネントを追加。
  - 実行系
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV による paper_trading モードをサポートし、ペーパートレード時は専用の SQLite（data/paper_trading.db、環境変数で上書き可）へ完全分離して記録する。
      - BrokerClientFactory を利用して実運用/モックの切替を行う。
      - スレッドで Engine を実行し、data/stop_requested.flag を監視して安全に停止する。
      - 実行中の PID 管理用の pid ファイルをサポート（data/execution.pid）。
  - 監視系
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出力。
      - 監視は環境に依らず本番 sqlite_path を使用して監視データを記録。
      - 停止フラグ（data/stop_requested.flag）を検知してループを終了。check_once() 呼び出しでの例外はログに例外情報を残して次ループで継続。
  - コンフィグ / 環境変数管理
    - config.py: Settings クラスを追加。環境変数から設定値を提供。
      - .env 自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml で探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env パースの堅牢化（export プレフィックス、クォート、エスケープ、インラインコメントの扱いなど）。
      - 各種既定値・検証（KABUSYS_ENV の有効値、PAPER_FILL_MODE の検証、ログレベル検証等）。
    - config_setup.py: 対話式 .env 作成ウィザードを追加。既存 .env 読み込み・編集、秘匿項目のマスク表示、保存機能を提供。
    - validate_config.py: 設定検証 CLI を追加。必須環境変数・KABUSYS_ENV・DB パス・config/*.yaml の存在と YAML パースを検証。--strict オプションで警告を FAIL 扱いにできる。
  - ポートフォリオ構築（純関数群）
    - portfolio/portfolio_builder.py
      - 候補選定 select_candidates（スコア降順、signal_rank でタイブレーク）
      - 等配分 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等配分へフォールバック）
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限チェックにより一部候補を除外（"unknown" セクターは除外対象外）
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear にマップ、未知のレジームは警告を出して 1.0 にフォールバック）
    - portfolio/position_sizing.py
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数決定。lot_size（単元）丸め、max_position_pct/ max_utilization、aggregate cap とコストバッファ考慮によるスケーリングロジックを実装。
      - risk_based モードはリスク許容率（risk_pct）・stop_loss_pct を用いて株数を算出。
      - aggregate cap 超過時のスケールダウンと端数処理（lot 単位で残差に基づく追加配分）を実装。
  - 解析 / 研究
    - research/factor_research.py: DuckDB 接続を利用したファクター計算モジュールを追加（モメンタム・MA200 乖離・ATR などを想定）。（注: ファイル末尾で実装途上の箇所あり）
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
      - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL を判定する。閾値はソース内で定義可能。
      - --from / --to / --db オプションで期間・DB を指定可能。PAPER_TRADING_SQLITE_PATH 環境変数でデフォルト DB を変更可能。
  - ユーティリティ
    - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
      - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
      - LOG_LEVEL / LOG_DIR 環境変数、引数での上書き対応。
    - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
      - Windows と POSIX（Linux/Mac 等）を吸収。権限不足や未サポート OS では警告を出してスキップ。
      - set_process_priority("high"/"normal"/"low")、set_cpu_affinity(N) を提供。

Changed
- －（初回リリースのため変更履歴はなし）

Fixed
- －（初回リリース）

Deprecated
- －（初回リリース）

Removed
- －（初回リリース）

Security
- －（初回リリース）

Notes / 制限事項 / TODO
- config.py の自動 .env ロードはプロジェクトルート検出に依存するため、配布先によっては自動読み込みがスキップされる（その場合は環境変数を明示設定してください）。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、将来的には前日終値や取得原価をフォールバック価格として使用することが想定されている（ソース内に TODO コメントあり）。
  - lot_size は現状グローバル固定（将来的には銘柄別 lot_map の導入を検討）。
- research/factor_research.py はファイル末尾で実装が途切れている（calc_momentum の続きを要実装）。研究用ファクター計算は現状未完成の箇所あり。
- run_monitoring は監視データの DB に本番 sqlite_path を利用する仕様。環境によらず同じ DB を使う設計であるため、開発用に分離したい場合は sqlite_path を環境変数で変更する必要がある。
- ロギング設定はログディレクトリ作成失敗時にファイル出力をしない挙動となる（その場合は標準出力のみ）。
- process_priority / set_cpu_affinity は権限や OS により失敗する可能性があり、その場合は警告ログを出して処理を継続する設計。

開発者向けメモ
- validate_config.py の --strict モードで警告を失敗扱いにできるため、本番デプロイ時は --strict を CI やデプロイスクリプトに組み込むことを推奨。
- .env の秘匿項目は config_setup ウィザードでマスク表示されるが、.env ファイル自体は絶対に Git にコミットしないこと（ヘッダにその旨を明記）。
- paper_trading 用の挙動（MockBrokerClient、専用 DB、fill_mode による動作差異）はペーパートレード検証に有用。PAPER_FILL_MODE の許容値チェックがあり、不正値は起動時に例外を投げる。

今後の改善提案（優先度順）
1. research モジュールの完全実装（calc_momentum の完了、他ファクターの追加）。
2. position_sizing の価格フォールバックロジック実装（前日終値や取得原価の利用）。
3. ログの構造化（JSON 出力オプション）とより詳細な運用モニタリング（メトリクスエクスポート）。
4. 銘柄毎の lot_size サポート（stocks マスタの導入）。
5. テストカバレッジ向上（特にポジションサイズ、スケーリングアルゴリズム、apply_sector_cap の境界ケース）。

---
（この CHANGELOG はコードベースのコメント・実装・ドキュメント文字列から推測して作成しました。実際のリリースノート作成時はコミット履歴やリリース担当者の確認を行ってください。）