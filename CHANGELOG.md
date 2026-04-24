# Changelog

すべての変更は「Keep a Changelog」仕様に従い、重要なリリースノートを日本語で記載しています。  

[0.1.0] - 2026-04-24
-------------------

### 追加
- 初回公開リリース: KabuSys 自動売買フレームワークのコア機能群を追加。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。停止フラグ（data/stop_requested.flag）検知・PID 管理（data/execution.pid）に対応。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関係なく本番用 sqlite_path を使う仕様。
- 設定管理 / ユーティリティ
  - config.py: Settings クラスを実装。.env 自動読み込み（.env → .env.local、OS 環境変数優先）、自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）と入力検証を提供。
  - config_setup.py: 対話式 .env ウィザードを追加。.env の作成・更新を支援。
  - validate_config.py: 設定検証 CLI を追加。必須環境変数・パス・config/*.yaml の存在や（PyYAML があれば）パース検証、本番環境時のガード（LINE 通知や Kill Switch 設定など）を行う。--strict オプションで警告をエラー扱いにできる。
- ロギング / プロセス制御
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。StreamHandler を stdout に出力し、TimedRotatingFileHandler（日次・30 日保持）でファイル出力を行う。LOG_DIR/LOG_LEVEL の解決順に対応。
  - utils/process_priority.py: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。Windows/Linux/macOS 等の差分を吸収し、権限不足時は安全にフォールバックして警告する。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額・スコア加重の重み計算 (calc_equal_weights, calc_score_weights) を追加。スコアが全て 0 の場合のフォールバック警告あり。
  - portfolio/risk_adjustment.py: セクター集中制限 (apply_sector_cap) とレジームに応じた投下資金乗数 (calc_regime_multiplier) を追加。unknown セクターの扱いや不明なレジームのフォールバックを実装。
  - portfolio/position_sizing.py: 株数決定ロジックを追加（allocation_method: "risk_based"/"equal"/"score" をサポート）。単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ想定）対応、残余配分アルゴリズム等を実装。
  - portfolio/__init__.py: 上記 API をパッケージとしてエクスポート。
- リサーチ / ファクター計算
  - research/factor_research.py: DuckDB を使ったファクター計算モジュール（モメンタム、MA200、ATR、流動性等）を追加（設計方針・定数設定を含む）。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。P95 レイテンシ計算、稼働率・注文成功率・送信率・リスク却下数などを集計し、閾値（稼働率 99%、成功率 90% 等）に基づいて PASS/FAIL 判定を出力。--from/--to/--db オプションをサポート。
- DB 初期化 / 監視補助
  - monitoring.monitoring_db.init_monitoring_db を各起動スクリプトから呼び出して監視テーブルの存在を保証（冪等）。
- パッケージ情報
  - __init__.py にてバージョンを "0.1.0" として設定。

### 変更（設計・動作上の注意点）
- .env パーサーの強化（config._parse_env_line）
  - export KEY=val 形式に対応。
  - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理し、インラインコメントを無視する挙動を実装。
  - クォートなし値では '#' の直前がスペース/タブの場合のみコメントと認識するなど、実用的な .env 構文をサポート。
- 自動読み込みの挙動
  - プロジェクトルート探索は __file__ を基準に親ディレクトリを上方向に走査し、.git または pyproject.toml を検出して決定。
  - 自動ロードは OS 環境変数を保護し、.env.local は .env を上書きする（ただし OS 環境変数は保護対象）。
- ログ出力
  - コンソール出力は stderr ではなく stdout に出力するよう統一（cron/task scheduler でのリダイレクト運用を想定）。
  - ログディレクトリの作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続。
- 実行時安全ガード
  - run_execution は起動時に既に停止フラグが立っている場合は起動を行わず終了する。
  - run_monitoring は停止フラグを検知するとループを終了し、例外発生時はログを残して次のポーリングへ復帰する。
  - Settings にて KABUSYS_ENV の有効値チェックを導入（development / paper_trading / live）。
- Paper Trading の分離
  - paper_trading モードでは MockBrokerClient を使用する前提（BrokerClientFactory の分岐を想定）とし、DB は paper_sqlite_path を使用して本番データと完全分離する。PAPER_FILL_MODE により挙動（instant, partial, never, reject）を制御。

### 修正（バグ修正・耐障害性向上）
- MONITOR_POLL_INTERVAL の整数変換失敗や 0/負の値に対してデフォルト値（60 秒）へフォールバックする実装を追加して、time.sleep に渡す不正値によるクラッシュを防止。
- process_priority.set_process_priority/set_cpu_affinity は OS 非対応や権限エラーを検出して警告を出し、安全に処理を継続するよう改善。
- validate_config にて PyYAML が未インストールの場合、YAML 検証をスキップして警告を出すようにし、ツール自体が ImportError で死ぬのを防止。

### 既知の制限 / 注意事項
- 一部モジュールは外部依存（psutil, duckdb, sqlite3, (PyYAML 任意)）を必要とします。実行環境に応じてインストールしてください。
- position_sizing の lot_size は現状全銘柄共通の想定。将来的には銘柄ごとの lot_size をサポートする予定（TODO コメントあり）。
- research/factor_research.py は設計方針・定数を含むが、実装の一部は続きが存在する（ファイルの末尾が途中で切れている場合があるため、実行前に完全実装を確認してください）。
- 本番環境で KILL_FLAG_CLEAR_ON_START=1 を設定することは危険（validate_config で警告）。

### セキュリティ
- 機密情報（API トークン・パスワード等）は .env ファイルに格納する仕様だが、.env を決してリポジトリにコミットしないよう README／ウィザードロゴに注意喚起を出力する。

今後の予定（例）
- ExecutionEngine / Broker クライアント間のインターフェース拡張、より細かいモニタリングメトリクスの追加、テストカバレッジの拡充、銘柄ごとの lot_size サポートなどを予定しています。