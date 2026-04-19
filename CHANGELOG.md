Keep a Changelog に準拠した CHANGELOG.md（日本語）
※コード内容から推測して作成しています。実際のコミット履歴や日付は含まれていません。

フォーマット:
- https://keepachangelog.com/ja/1.0.0/

----------------------------------------------------------------------
# Changelog

すべての重要な変更点はこのファイルに記録します。  
フォーマットは Keep a Changelog を採用し、セマンティックバージョニングに従います。

## [Unreleased]
- ドキュメントやリファクタがあればここに記載します。

## [0.1.0] - 初回リリース（推定）
初回の機能群を追加。以下はコードベースから推測してまとめた主要な機能と修正点です。

### 追加
- アプリケーション基盤
  - パッケージの初期バージョンを追加（__version__ = "0.1.0"）。
  - Settings クラスによる環境変数/設定管理を実装。
    - .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml）。
    - OS 環境変数を保護しつつ .env/.env.local を読み込む挙動。
    - 必須環境変数取得用の _require() を提供。
    - 各種設定プロパティ（DB パス、PID / kill flag パス、閾値、env/log level 判定、paper trading 関連）を実装。

- 起動スクリプト / 実行基盤
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV による paper_trading モード判定を行い、paper_trading 環境時は専用 SQLite（data/paper_trading.db）を使用する設計。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立て/起動処理を実装。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止する仕組み。
    - 実行用 PID ファイル path をサポート（data/execution.pid）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - monitoring は環境に関わらず本番 sqlite_path を使用する設計（監視データは一元化）。
    - 停止フラグ検知でループを終了、KeyboardInterrupt ハンドリング、DB コネクションのクローズを保証。

- 設定・検証関連 CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する機能を実装。
    - .env の読み込み/書き込みロジックを提供（シークレット項目のマスク表示、選択肢・デフォルト対応）。
    - 生成される .env ファイルにはコメントと注意書きを含める（.env を Git にコミットしないよう注意）。

  - validate_config.py
    - 起動前に .env と config/*.yaml の簡易検証を行う CLI を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、YAML の存在/パースチェック（PyYAML がない場合は警告）を実装。
    - KABUSYS_ENV=live 時の追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定に対する警告）。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバックし警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中上限チェック（apply_sector_cap）を実装。既存保有時価からセクターごとのエクスポージャを計算して新規候補を除外。
    - market レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear をマップ、未知レジームはフォールバックで警告）。
    - sell_codes（当日売却予定）をエクスポージャ計算から除外可能。

  - portfolio/position_sizing.py
    - 発注株数計算 calc_position_sizes を実装（allocation_method: risk_based / equal / score）。
    - 単元株丸め（lot_size, デフォルト 100）、max_position_pct、max_utilization、cost_buffer による保守的見積り、aggregate cap によるスケーリングを実装。
    - 利用可能現金を超える場合はスケールダウンし、残余キャッシュで大きな端数順に単位を追加配分するロジックを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 一貫したロギング設定ユーティリティを追加。
    - コンソール（stdout）へ StreamHandler、日次ローテート（TimedRotatingFileHandler）でログをファイル出力（logs/<app_name>.log）し 30 日保持。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラをクリアして二重設定を防止。

  - utils/process_priority.py
    - Windows / POSIX（Linux/macOS/FreeBSD）差分を吸収してプロセス優先度を設定する API を提供（set_process_priority）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- モニタリング DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を起動スクリプトから呼び出し、監視テーブルが存在することを保証（冪等）。

- Paper Trading 向けツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）を読み、システム稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを集計して検証レポートを出力するスクリプトを追加。
    - 実行例引数: --from / --to / --db。
    - Pass/Fail 判定の閾値を定義（稼働率 99% 以上、成立率 90% 以上、送信率 95% 以上、P95 <= 200 ms 等）。
    - 空データやテーブル欠損時に graceful に扱う（OperationalError を捕捉して N/A を表示）。

- リサーチモジュール（開発中）
  - research/factor_research.py にモメンタム/ボラティリティ/バリュー/流動性等のファクター計算ロジックを追加（DuckDB 接続を受け prices_daily / raw_financials テーブル参照）。
  - calc_momentum 等の設計が含まれている（実装途中の箇所あり）。

### 変更
- .env パーサー強化（config._parse_env_line）
  - export KEY=val 形式に対応。
  - シングル/ダブルクォート内でのバックスラッシュエスケープを処理。
  - クォート無し値のインラインコメント処理をスペース/タブに依存して正しく扱うよう改善。

- ログ出力先の統一
  - ログは stdout をデフォルトのコンソール出力先に使用（cron 等で stdout/stderr を一本化する運用に配慮）。

- run_execution/run_monitoring:
  - 起動直後にプロセス優先度を "high" に設定するように変更（set_process_priority 呼び出しを追加）。

- Settings:
  - PAPER_FILL_MODE の検証を追加（valid 値: instant|partial|never|reject）。無効値は ValueError。
  - is_paper / is_live / is_dev のプロパティを追加。

### 修正 (バグ修正 / ロバストネス向上)
- MONITOR_POLL_INTERVAL の不正値（0以下や非数）を検知してデフォルトにフォールバックし、警告を出すように修正。
- logging_setup: ログディレクトリ作成失敗時に FileHandler の作成をスキップし、コンソール出力のみで継続するよう堅牢化。
- process_priority: 権限不足や未実装関数の例外を捕捉して警告を出し処理を継続するように修正。
- calc_score_weights: スコア合計が 0 のとき等金額配分にフォールバックして警告を出すように修正。
- position_sizing: 価格が欠損（None や <=0）な銘柄をスキップして誤った計算を防止。
- paper_verification_report: テーブル/カラムが存在しない場合に sqlite3.OperationalError を捕捉して N/A を返すように堅牢化。

### セキュリティ
- .env の取り扱いに関する注意書きを config_setup の生成ファイルに明記（.env をリポジトリに含めないよう促す）。

### 既知の制限 / TODO
- position_sizing の lot_size は全銘柄共通に固定（将来的に銘柄別 lot_map 対応を検討）。
- risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合、保守的なフォールバック未実装（TODO コメントあり）。
- research/factor_research.py は一部実装が途中（calc_momentum の実装途中でファイルが切れている）。
- Paper Trading 用 DB の初期化やスキーマ文言は monitoring_db.init_monitoring_db の実装に依存（コードからは詳細不明）。

### 破壊的変更
- なし（初期リリースに相当）。

----------------------------------------------------------------------
参照:
- 各 CLI: python -m kabusys.config_setup, python -m kabusys.validate_config, python -m kabusys.tools.paper_verification_report
- デフォルトパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - ログ: logs/<app_name>.log
  - stop flag: data/stop_requested.flag
  - execution PID: data/execution.pid

（本 CHANGELOG はコードの静的解析から推測して作成しています。実際のリリースノートはコミット履歴やリリース日・影響範囲を確認して調整してください。）