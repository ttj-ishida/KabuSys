# CHANGELOG

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]
- research/factor_research.calc_momentum の実装が途中（ソースが途中で切れているため完全実装が必要）。
- 追加のテスト、ドキュメント整備、およびいくつかのエラーハンドリング強化が今後の課題。

## [0.1.0] - 2026-04-21
初回リリース。以下の主要機能・モジュールを追加しました。

### 追加
- 実行・監視用エントリポイント
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離する挙動を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）と実行 PID ファイル（data/execution.pid）に対応し、安全に停止処理を行える。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する仕様。
    - 停止フラグファイルを検知してループを終了。KeyboardInterrupt にも対応。

- 設定関連
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - 複雑な .env 行パースをサポート（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理など）。
    - Settings クラスで各種設定（J-Quants / kabuAPI / DB パス / Paper Trading 設定 / 監視閾値 / 環境名・ログレベル判定等）を取得可能に。
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path のデフォルトなどを実装。
  - config_setup.py
    - .env 作成・更新の対話式ウィザードを実装。秘密情報はマスクして表示。
    - .env の既存値読み込み、選択肢表示、保存確認をサポート。
    - .env 書き込みテンプレートは Git にコミットしないよう注記。

- 設定検証 CLI
  - validate_config.py
    - .env と config/*.yaml（存在/パース）を起動前に検証する CLI。
    - 必須/任意環境変数のチェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェックを実装。
    - PyYAML 未導入時は YAML 内容検証をスキップして警告。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険設定警告など）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等ウェイト（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア総和が 0 の場合は等ウェイトにフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用して候補を除外する apply_sector_cap を実装。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップ、未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数を計算する calc_position_sizes を実装（allocation_method: risk_based / equal / score をサポート）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap によるスケールダウン、cost_buffer による保守的見積り、残余キャッシュを用いた端数処理を実装。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定するユーティリティを実装。
    - LOG_LEVEL / LOG_DIR / 引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで継続。
    - 既存ハンドラはクリアして再設定することで二重設定を防止。
  - utils/process_priority.py
    - psutil を用いてプロセス優先度設定（Windows の priority class / POSIX の nice 値）と CPU affinity 設定を提供。
    - 対応 OS の差分を吸収し、権限不足や未実装機能には警告を出して安全にスキップ。

- モニタリング DB 初期化
  - monitoring/monitoring_db.py（参照されている init_monitoring_db を各起動処理で呼び出し、監視テーブルの存在を保証）

- 実行系コンポーネント（組み立て例）
  - execution/*.py（BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager）
    - 起動スクリプト内での組み立てロジック（RiskConfig のデフォルト値、初期資金取得を broker.get_available_cash() で行う等）を実装。
    - Reconciler や OrderManager などの連携を行い、エンジンを別スレッドで起動して停止フラグを監視する。

- テスト・運用支援ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / デフォルト data/paper_trading.db）からデータを集計し、稼働率（uptime）、注文成功率（fill rate）、送信率、レイテンシ（avg/max/P95）等を計算して PASS/FAIL を判定するレポート生成スクリプトを実装。
    - デフォルト基準値（稼働率 99%、fill rate 90%、send rate 95%、P95 レイテンシ 200 ms）を使用。
    - 日付フィルタ（--from / --to）や --db オプションをサポート。

- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

### 変更
- なし（初回リリースのため既存との互換性変更なし）。

### 修正
- なし（初回リリース）。

### 既知の問題
- research/factor_research.calc_momentum の実装が途中でファイルが切れている（未完成）。ファクター計算モジュールはまだ完全ではないため、DuckDB を用いたファクター計算の追加実装と単体テストが必要。
- position_sizing の価格欠損（price が 0 または None）の場合に現状はスキップする実装だが、将来的に前日終値や取得原価等のフォールバック価格ロジックを導入することを推奨（TODO 注記あり）。
- 一部の機能（psutil による優先度設定や CPU affinity）は環境や権限に依存し、設定に失敗した場合は警告を出してスキップする挙動。

### セキュリティ
- .env は機密情報を含むため絶対に Git にコミットしない旨を config_setup に明記。

---

注:
- ドキュメントやテストを充実させることで運用安全性を高める必要があります。特に本番（KABUSYS_ENV=live）運用時は validate_config による事前チェックと LINE 等の通知設定を必ず確認してください。