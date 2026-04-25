# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]
- なし

## [0.1.0] - 2026-04-25
初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装しました。以下はコードベースから推測できる主要な追加・改善点と運用上の注意点です。

### 追加 (Added)
- 基本パッケージ構成
  - kabusys パッケージ本体（__version__ = 0.1.0）
  - サブパッケージ: portfolio, execution, monitoring, tools, research, utils 等の骨格実装。

- 設定関連
  - Settings クラス（src/kabusys/config.py）
    - 環境変数ベースの設定取得（J-Quants / kabu API / DB パス / 監視閾値 等）
    - env 値検証（development / paper_trading / live）
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）
  - 自動 .env 読み込み機能
    - プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
    - クォート、エスケープ、インラインコメント対応のパーサ実装（_parse_env_line）

- 設定ユーティリティ CLI
  - config_setup.py: 対話式ウィザードで .env を作成/更新（項目定義、既存値の再利用、秘匿入力対応）
  - validate_config.py: 起動前チェックツール（必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース等）
    - --strict モードで警告を FAIL 扱いにできる

- 実行・監視起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動シーケンス（プロセス優先度設定、DB 接続、ブローカ生成、OrderManager/RiskManager/Reconciler 組立、スレッド起動）
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用して本番 DB と分離
    - 停止フラグ (data/stop_requested.flag) と pid ファイル (data/execution.pid) による制御
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能、デフォルト 60 秒）
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（設計上の注意点）
    - 停止フラグ検出でループ終了

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio_builder.py
    - select_candidates（スコア降順、signal_rank でタイブレーク）
    - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合は等分配へフォールバック）
  - risk_adjustment.py
    - apply_sector_cap（セクター別上限チェック。unknown セクターは除外しない）
    - calc_regime_multiplier（regime に応じた投下資金乗数。未知レジームは警告して 1.0 にフォールバック）
  - position_sizing.py
    - calc_position_sizes（risk_based / equal / score の配分方式、lot_size による丸め、aggregate cap によるスケールダウン、cost_buffer 考慮）

- ユーティリティ
  - logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保管）を設定
    - LOG_DIR / LOG_LEVEL の解決順とフォールバック処理
  - process_priority.py
    - プロセス優先度設定（Windows/Linux/macOS に対応。psutil 使用）
    - CPU affinity 設定ヘルパ（set_cpu_affinity）

- 分析・検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite を読み、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等の指標を集計して検証レポートを生成
    - デフォルト閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）
    - --from / --to / --db オプション対応

- DB 統合
  - DuckDB と SQLite の両方を利用する設計（duckdb_path / sqlite_path 設定、duckdb は分析用、sqlite は監視/発注ログ用）
  - monitoring_db.init_monitoring_db の呼び出しを起動時に行い監視テーブルの存在を保証（冪等）

- Execution リスク設定（デフォルト）
  - RiskManager の設定デフォルトを実装（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20 等）
  - initial_portfolio_value を broker.get_available_cash() で初期化

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- .env パーサの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い、空行/コメント行のスキップに対応。
- logging_setup: ログディレクトリ作成失敗時にファイルハンドラをスキップしてコンソール出力でフォールバックする挙動を追加。
- process_priority: OS に依存する定数参照を安全に行う実装（getattr フォールバック）。

### 破壊的変更 (Breaking Changes)
- 監視挙動に関する設計上の注意
  - run_monitoring は KABUSYS_ENV に関わらず settings.sqlite_path（本番 monitoring DB）を使用します。テスト目的で paper_trading 環境でも別 DB を期待していた場合、誤って本番 DB を操作する可能性があるため注意してください。
- process_priority / cpu_affinity の適用はプラットフォーム権限に依存します。権限不足で警告が出る可能性があります（挙動はスキップされ安全に続行します）。

### セキュリティ (Security)
- .env ファイルは絶対にリポジトリにコミットしない旨を config_setup の出力に明記。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  未設定の場合は validate_config でエラーとなり、Settings._require は ValueError を投げます。

### 既知の制限 / TODO
- risk_adjustment.apply_sector_cap: price_map に価格が欠損（0.0）の場合にエクスポージャーが過小評価される可能性がある旨の注記。前日終値や取得原価などのフォールバックを将来的に検討。
- position_sizing.calc_position_sizes:
  - lot_size は現在全銘柄共通（将来的に銘柄別 lot_map への対応が示唆されている）
  - 一部アルゴリズム（aggregate cap の端数処理など）は再現性・安全弁を意識した実装だが、実運用での微調整が必要
- research/factor_research.py はファクター計算の実装開始（ファイル末尾で途中までの実装が含まれているように見える）
- tools/paper_verification_report の P95 算出は単純な順位選択実装（大規模データや小サンプル時の注意あり）

### 利用上の注意（運用メモ）
- run_execution 実行時:
  - paper_trading 環境では BrokerClientFactory が MockBrokerClient を生成し、paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離される設計。
  - Engine は別スレッドで run_session を実行し、停止フラグで安全停止を試みる。
- run_monitoring 実行時:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（1 秒以上の整数）。不正値はデフォルト 60 秒にフォールバック。
- ロギング:
  - デフォルトは logs/<app_name>.log に日次ローテーションで出力。LOG_DIR 環境変数で変更可能。
  - 出力は stdout も使用するため cron 等からの起動でリダイレクトしやすい。
- validate_config を先に実行して設定の妥当性（必須変数、KABUSYS_ENV の値、DB パスの親ディレクトリ存在、config/*.yaml のパース）を確認することを推奨。

---

（注）本 CHANGELOG は提示されたソースコードから推測して作成しています。実際のリリースノートや変更履歴は、コミット履歴やプロジェクト管理ツールの記録に基づいて作成することを推奨します。