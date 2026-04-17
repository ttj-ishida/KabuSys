# CHANGELOG

すべての notable な変更点を Keep a Changelog 準拠で日本語で記載します。

フォーマット:
- Unreleased: 今後の変更（現時点では空）
- 0.1.0: 初回公開リリース（コードベースに基づき推測して記載）

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-17

初回リリース。日本株自動売買システム「KabuSys」の主要コンポーネントを実装・収録。

### Added
- 基本パッケージ情報
  - src/kabusys/__init__.py
    - パッケージ名・バージョン（0.1.0）を定義。

- 設定管理・.env 自動読み込み
  - src/kabusys/config.py
    - プロジェクトルート（.git または pyproject.toml）を基準に .env を自動ロード。
    - .env/.env.local のロード順・上書きルールを実装（OS 環境変数保護あり）。
    - .env 行解析ロジックを実装（export 形式、クォート、エスケープ、インラインコメント処理対応）。
    - 各種設定プロパティを提供（J-Quants、kabu API、DB パス、監視閾値、環境判定など）。
    - 入力検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を追加。

- 環境設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成・更新するツールを追加。
    - デフォルト値、シークレット表示（マスク）、項目説明付き。
    - .env の読み取り・書き込みヘルパーを実装。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml の妥当性をチェックする CLI を追加。
    - 必須/任意の環境変数チェック、KABUSYS_ENV・LOG_LEVEL 等の検証、DB パスの親ディレクトリ確認、YAML ファイルの存在・パース検証（PyYAML が無ければ警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定・Kill flag の自動クリア設定警告等）。

- 実行エンジン起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成（モック含む）。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと実行（スレッドでデーモン実行）。
    - 停止フラグ（data/stop_requested.flag）検出時に安全に停止。PID ファイル管理（data/execution.pid）。
    - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を設定。

- 監視ループ起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor をポーリングで定期実行する起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨の実装。
    - 停止フラグ（data/stop_requested.flag）検出でループ終了。起動時にプロセス優先度を "high" に設定。

- プロセス優先度 / CPU affinity ユーティリティ
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定する set_process_priority を追加。アクセス拒否等は警告してスキップ。
    - set_cpu_affinity により先頭 N コアへのピニングをサポート（未対応環境では警告してスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を追加。
    - スコアが全て 0 の際は等配分へフォールバックしログ出力。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap。
    - マーケットレジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームは警告して 1.0 フォールバック）。

  - src/kabusys/portfolio/position_sizing.py
    - 各銘柄の発注株数算出 calc_position_sizes を実装（risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）によるスケール調整、cost_buffer の考慮、端数分配ロジックを実装。

  - src/kabusys/portfolio/__init__.py
    - 上記関数をパブリックにエクスポート。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - DuckDB 接続を用いてモメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20 等）、流動性指標等を計算する関数を実装。
    - prices_daily / raw_financials テーブルのみ参照し純粋関数として設計。

- Paper Trading 検証レポートツール
  - src/kabusys/tools/paper_verification_report.py
    - paper_trading DB（デフォルト data/paper_trading.db）を解析し、稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出・判定（PASS/FAIL）しレポート出力。
    - 閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を実装。
    - 日付フィルタ（--from / --to）、DB パス指定（--db / 環境変数）をサポート。

- その他ユーティリティ/パッケージ構造
  - src/kabusys/tools/__init__.py, src/kabusys/utils/__init__.py を追加（パッケージ化）。

### Changed
- （初回リリースのため該当なし）

### Fixed / Robustness
- config の .env パーサーは引用符内のエスケープや export プレフィックス、インラインコメントを正しく扱うようになり、より多様な .env フォーマットに対応。
- MONITOR_POLL_INTERVAL が 0 以下や非整数のときは警告しデフォルト（60 秒）にフォールバックするように実装（run_monitoring.py）。
- DuckDB / SQLite のテーブル未存在時（report ツール等）に OperationalError を捕捉してデフォールト値を扱う耐性を追加（paper_verification_report.py）。
- process_priority はプラットフォーム差異（Windows 定数の未定義等）に対して安全にフォールバックするよう実装。

### Notes / Implementation details
- run_execution.run uses:
  - ExecutionEngine を別スレッドで run_session 実行。停止フラグ検出で engine.stop() を呼び安全シャットダウン。
  - paper_trading 環境では paper 用 SQLite（デフォルト data/paper_trading.db）を使い、本番 DB と完全に分離する設計。
- run_monitoring は monitoring 用 DB 初期化（init_monitoring_db）を行い、duckdb も併用して SystemMonitor に接続を渡す。
- RiskManager の initial_portfolio_value は broker.get_available_cash() で初期化される（実行時の現金量に依存）。
- portfolio の position sizing は lot_size（現状共通 100）や cost_buffer を考慮し、available_cash を超えた場合は端数調整ロジックで公平に配分する。

### Known limitations / TODO（コード内コメントより）
- position_sizing.calc_position_sizes:
  - 銘柄ごとの lot_size を将来的に stocks マスタから取得する設計への拡張が想定されている。
- risk_adjustment.apply_sector_cap:
  - 価格が欠損（0.0）の場合はエクスポージャーが過小算出される可能性があり、前日終値等によるフォールバックを検討する旨の注記あり。
- research モジュールは prices_daily / raw_financials のデータ品質に依存するため、データ不足時は None を返す設計。

---

以上。コードを読み取って推測した初回リリースの変更点一覧です。必要であれば各項目をさらに細分化して対応ファイルや行数・関数名を明示することもできます。