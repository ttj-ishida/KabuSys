CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。フォーマットは "Keep a Changelog" に準拠しています。

目次
----
- [Unreleased](#unreleased)
- [0.1.0 - 2026-04-22](#010---2026-04-22)

Unreleased
----------
### 注意事項
- research/factor_research.py において calc_momentum の実装が途中で終了している箇所が見つかっています。今後のリリースで完了予定です。
- ドキュメント整備・追加テストは継続中です。

0.1.0 - 2026-04-22
------------------
初回リリース — KabuSys の基本機能群を追加しました。日本株自動売買システムのコアユーティリティ、設定管理、監視・実行スクリプト、ポートフォリオ構築ロジック、解析ツール類を含みます。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として公開。
  - パッケージエクスポート: data, strategy, execution, monitoring。

- 設定管理
  - kabusys.config.Settings クラスを実装し、環境変数経由でアプリ設定を統一的に取得。
  - .env 自動読み込み機能を追加（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env のパースを強化（export プレフィックス対応、シングル／ダブルクォート内のエスケープ、インラインコメント処理など）。
  - 設定必須チェック用のヘルパ _require を実装。

- 設定支援ツール
  - config_setup.py: 対話式ウィザードで .env を作成 / 更新する CLI を実装。
    - 複数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定など）を対話的に入力可能。
    - シークレット項目は表示をマスクして扱う。
  - validate_config.py: 起動前検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの存在チェック（親ディレクトリ）、config/*.yaml の存在とパース検証（PyYAML 有無に応じて挙動を変える）。
    - --strict オプションで警告を失敗扱いにできる。

- 実行系スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てとデーモンスレッドでの実行制御。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を利用した安全停止機構。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit breaker 等）を定義。
    - duckdb を解析用データ保存に利用。

- 監視系スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバックし警告出力）。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使う（監視 DB を分離しない設計）。
    - stop flag によるループ中断と KeyboardInterrupt ハンドリング。
    - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築ライブラリ (kabusys.portfolio)
  - portfolio_builder.py
    - select_candidates: スコア降順 + tie-breaker（signal_rank）で候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等分配にフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有のセクター比率が閾値を超える場合、新規候補を除外）。"unknown" セクターは無視。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバック警告）。
  - position_sizing.py
    - calc_position_sizes: 発注株数計算を実装（allocation_method: "risk_based" / "equal" / "score"）。
      - risk_based: 損切り幅・リスク率に基づく株数計算。
      - equal/score: 配分比率と最大ポジション上限、単元株（lot_size）丸めを考慮。
      - aggregate cap のスケーリング処理を実装して available_cash を超えた場合に比例縮小と再配分（lot 単位で端数処理）を行う。
      - cost_buffer を導入して手数料・スリッページ分を保守的に見積もる。

- ロギング & プロセス制御ユーティリティ
  - utils/logging_setup.py
    - setup_logging を実装。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - ログディレクトリの作成に失敗した場合はファイル出力を無効にしてコンソール出力のみで継続。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
    - stdout を使用することで cron 等でのリダイレクト運用を想定。
  - utils/process_priority.py
    - set_process_priority: Windows/Linux/macOS 等を抽象化してプロセス優先度を設定（Windows の HIGH_PRIORITY_CLASS を考慮、POSIX は nice 値を設定）。
    - set_cpu_affinity: 指定コア数での CPU ピン留めを実装（psutil を使用、権限不足時は警告を出してスキップ）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ統計（avg/max/P95）を算出し PASS/FAIL 判定を出力。
    - デフォルト DB は data/paper_trading.db。--from, --to, --db オプションで期間・DB 指定可能。
    - 判定基準の閾値を定義（稼働率 99.0%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。

- 分析基盤連携
  - DuckDB を分析ストアとして利用する設計を導入（duckdb_path 設定でファイルを指定）。
  - research/factor_research.py を追加（モメンタム、ボラティリティ等のファクター計算を目的としたモジュール。実装は一部未完）。

- その他
  - scripts / モジュールの例外処理やリソースクローズを整理（sqlite3/duckdb 接続の明示的クローズ）。
  - init_monitoring_db の呼び出しを行い、監視用テーブルの存在保証（冪等に実行できるよう配慮）。
  - tools パッケージ初期化ファイルを追加。

### 変更 (Changed)
- ログ出力先の方針を明確化: コンソールは stdout を使用、ファイルは日次ローテーションで最大 30 日保持。
- .env 自動ロードの優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- run_monitoring の挙動: 監視は常に本番 sqlite_path を参照する（環境に依存しない設計）。
- run_execution の DB 接続: paper_trading 環境では専用の paper_sqlite_path を使用して本番 DB と分離。

### 修正 (Fixed)
- validate_config: PyYAML 未導入時に YAML 検証をスキップして警告出力するよう修正（起動時に fatal にならない）。
- .env 読み込み時の I/O エラーは警告に変換して続行するようにし、ファイル読み込み失敗でアプリケーションがクラッシュしないよう整備。
- process_priority / cpu_affinity: 権限不足や未対応 OS の場合は例外を投げず警告でスキップするように変更。

### 既知の問題 (Known issues)
- research/factor_research.py の calc_momentum 関数の実装が途中で終わっており、ファクター計算の一部が未完成です。今後のリリースで完了予定。
- position_sizing.calc_position_sizes の price 欠損（0.0）時は現在単純にスキップしているため、実データ欠損時にエクスポージャーが過小見積もりされる可能性があります（将来的に価格フォールバックを追加する予定）。
- 一部機能は psutil や PyYAML 等の外部依存が必要です。未インストール時は機能の一部を使用できない旨の警告が出ます。

ライセンス / 貢献
-----------------
- 貢献やバグ報告はプルリクエスト / イシューで受け付けます。
- .env に秘密情報を含めたまま Git にコミットしないでください（config_setup のヘッダにも注意喚起あり）。

以上。必要であれば各モジュールごとの変更点をより詳細に分割したバージョン履歴を作成します。どの程度の粒度が良いか指示ください。