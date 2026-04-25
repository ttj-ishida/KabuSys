# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。通常、バージョン/日付ごとに「Added / Changed / Fixed / Security」などのセクションでまとめます。

## [0.1.0] - 2026-04-25

### Added
- 初期リリース。KabuSys 自動売買フレームワークのコアユーティリティ・CLI・ライブラリを追加。
  - パッケージ情報
    - src/kabusys/__init__.py: パッケージ名とバージョン（0.1.0）を定義。
  - 環境設定・読み込み
    - src/kabusys/config.py
      - .env 自動読み込み機能を追加（探索はプロジェクトルートを .git または pyproject.toml を基準に決定）。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。
      - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
      - .env パースロジックを実装（export プレフィックス、クォート値、バックスラッシュエスケープ、インラインコメントの取り扱いを考慮）。
      - Settings クラスを実装し、J-Quants / kabu API / DB パス /監視閾値 /環境種別（development/paper_trading/live）等のプロパティを提供。
      - Paper Trading 関連設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）をサポートし、妥当性チェックを含む。
  - 環境設定ウィザード CLI
    - src/kabusys/config_setup.py
      - 対話式ウィザードで .env を作成・更新する機能を追加。
      - デフォルト値・選択肢・シークレット項目のマスク表示や既存 .env の読み込みに対応。
      - 出力フォーマットで .env ファイルへ安全に書き込む機能を提供。
  - 設定検証 CLI
    - src/kabusys/validate_config.py
      - 起動前に環境変数・config/*.yaml の存在や基本的妥当性をチェックする検証ツールを追加。
      - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ確認、YAML パース（PyYAML が存在する場合）、
        および本番環境向けの追加ガード（LINE 設定や Kill Flag の自動クリア設定の警告）を実装。
      - --strict オプションで警告を FAIL 扱いにできる。
  - 起動スクリプト
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒、無効値時はフォールバックして警告を出す）。
      - 停止検知はプロジェクト直下 data/stop_requested.flag を監視。
      - 監視モジュールは環境に関わらず本番用 sqlite_path を使用する挙動（注記あり）。
    - src/kabusys/run_execution.py
      - ExecutionEngine の起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db、環境変数で上書き可）を使い本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立てと ExecutionEngine 起動を行う。
      - スレッドでエンジンを実行し、停止フラグ検知時に安全停止する。PID ファイル出力をサポート。
  - 監視 DB 初期化
    - src/kabusys/monitoring/monitoring_db.py への参照（init_monitoring_db を呼ぶことで監視テーブルの存在を保証）。
  - ロギングセットアップ
    - src/kabusys/utils/logging_setup.py
      - StreamHandler（stdout へ出力）と TimedRotatingFileHandler（日次ローテーション、既定 30 日保持）をルートロガーに設定するユーティリティを追加。
      - ログレベル解決順: 引数 > LOG_LEVEL 環境変数 > "INFO"。
      - ログディレクトリ解決順: 引数 > LOG_DIR 環境変数 > "logs/"。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度 / CPU affinity ユーティリティ
    - src/kabusys/utils/process_priority.py
      - Windows / POSIX (Linux/Mac/FreeBSD) の差を吸収してプロセス優先度（high/normal/low）を設定する set_process_priority を追加。psutil に基づく実装で権限不足等はログ警告でスキップ。
      - set_cpu_affinity によりプロセスを先頭 N コアにピンニングする機能を追加（引数 None で無設定、1 未満は例外）。
  - ポートフォリオ構築ライブラリ
    - src/kabusys/portfolio/portfolio_builder.py
      - 銘柄候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights。全スコアが 0 の場合は等配分へフォールバック）を実装。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限を適用する apply_sector_cap（sell 処理予定銘柄を除外できる、unknown セクターは上限適用除外）を追加。
      - 市場レジームに応じた資金乗数 calc_regime_multiplier を追加（"bull"/"neutral"/"bear" をマップ、未知値は警告の上 1.0 をフォールバック）。
    - src/kabusys/portfolio/position_sizing.py
      - 複数方式（"risk_based", "equal", "score"）の発注株数決定を実装。lot_size（単元株）で丸め、per-position 上限・aggregate cap（利用可能現金）でスケールダウンするロジックや cost_buffer（手数料/スリッページ見積）を考慮。
      - スケールダウン時に残余キャッシュで端数を lot 単位で再配分するアルゴリズムを実装。
    - src/kabusys/portfolio/__init__.py で上記 API をエクスポート。
  - リサーチ（ファクター計算）スケルトン
    - src/kabusys/research/factor_research.py にモメンタム等のファクター計算ロジックの導入（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。
  - ペーパートレード検証ツール
    - src/kabusys/tools/paper_verification_report.py
      - ペーパートレード用 SQLite から統計を集計してレポートを出力する CLI を追加。
      - 指標: 稼働率 (uptime)、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。閾値を定義して PASS/FAIL を判定。
      - --from/--to/--db オプションをサポート。デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

### Notes / Attention
- 監視（run_monitoring）は「環境にかかわらず」Settings.sqlite_path（本番 monitoring DB）を使用する設計になっています。環境分離を期待する場合は設定を確認してください。
- PAPER_FILL_MODE の有効値は "instant" / "partial" / "never" / "reject"。不正値はエラーになります。
- .env の自動ロードはテスト用途などで無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 1 に設定すると危険（自動的に Kill Switch がクリアされる）ためデフォルトは 0、注意喚起を行っています。
- ログは標準出力（stdout）にも出るため、cron / Task Scheduler 等からの起動でもログ取得しやすくなっています。

もし特定ファイルの変更差分や、リリースノートをもっと粒度細かく分けたい場合（例: 監視関連 / 実行エンジン / ポートフォリオのそれぞれに対する詳細な項目化）、どのカテゴリを優先するか教えてください。