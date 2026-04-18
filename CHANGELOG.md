# CHANGELOG

すべての注目すべき変更を記録します。本ドキュメントは Keep a Changelog の形式に準拠しています。  
リリース日はリポジトリのバージョン (src/kabusys/__init__.py の __version__) に合わせて記載しています。

## [0.1.0] - 2026-04-18 (Initial release)

### Added
- 全体
  - 初回リリース。日本株自動売買システム「KabuSys」のコア CLI/ライブラリ群を追加。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

- 実行 / 監視
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - ExecutionEngine を起動するためのエントリポイントを提供。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 実行中の停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を利用した安全停止機構を実装。
    - プロセス優先度を起動時に High に変更（utils.process_priority を使用）。
    - 各種コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立てて起動。

  - 監視ループ起動スクリプト: src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを提供。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトへフォールバックして警告を出力。
    - 監視は常に「本番」用の sqlite_path（Settings.sqlite_path）を使用する仕様に明示。
    - 停止フラグ (data/stop_requested.flag) によりループを終了する機構を実装。

- 設定管理
  - 環境変数 / 設定読み込みモジュール: src/kabusys/config.py
    - .env/.env.local の自動読み込みを実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パース処理は export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントを考慮した堅牢な実装。
    - Settings クラスを提供し、J-Quants / kabu API / DB パス / 監視しきい値 等のプロパティを公開（デフォルト値・バリデーション付き）。
    - Paper Trading 関連: PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 対応。

  - 環境設定ウィザード CLI: src/kabusys/config_setup.py
    - .env を対話式に作成・更新するウィザードを実装（秘密値入力のマスク、選択肢、デフォルト表示、保存確認）。
    - 書き込みフォーマット・テンプレートを提供し、.env を安全に生成。

  - 設定検証 CLI: src/kabusys/validate_config.py
    - .env と config/*.yaml の設定不備を起動前に検出する検証ツールを実装。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML 未インストール時はスキップ）、本番環境時の安全ガードチェック等を実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数）
  - src/kabusys/portfolio/portfolio_builder.py
    - 銘柄候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。
    - スコア全てが 0 の場合は等配分にフォールバックして警告を出力。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を実装。
    - レジーム乗数は "bull"/"neutral"/"bear" をサポートし、未知レジームは警告後 1.0 でフォールバック。
    - apply_sector_cap は既存保有と価格マップを参照し、上限超過セクターの新規候補を除外 (unknown セクターは除外対象としない)。

  - src/kabusys/portfolio/position_sizing.py
    - ポジションサイズ計算ロジックを実装（allocation_method: "risk_based", "equal", "score"）。
    - 単元株（lot_size）での丸め、per-position 上限、aggregate cap（利用可能現金によるスケーリング）、cost_buffer による保守的コスト見積り、残差配分ロジックを実装。
    - price が欠損/ゼロの場合はログ出力でスキップする振る舞い。
    - 将来的な拡張 (銘柄毎 lot_size) に関する TODO コメントあり。

- ユーティリティ
  - ログ設定ユーティリティ: src/kabusys/utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保存）をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止。
    - ログディレクトリ作成が失敗した場合はファイル出力をスキップし、コンソール出力のみで継続。
    - LOG_LEVEL / LOG_DIR / 引数で挙動を制御。

  - プロセス優先度/CPU affinity ユーティリティ: src/kabusys/utils/process_priority.py
    - Windows (psutil の優先度定数を使用) と POSIX (nice 値) の差分を吸収し、set_process_priority(level) を提供。
    - set_cpu_affinity(cpu_count) を実装（指定なしはスキップ）。権限不足時は警告を出力して安全にフォールバック。
    - サポートされるレベル: "high" / "normal" / "low"。

- モニタリング DB 初期化
  - src/kabusys/monitoring/monitoring_db.py（参照読み込みあり）を起動時に呼び出し、必要なテーブルが存在することを冪等に保証（init_monitoring_db の呼び出しポイントを実装）。

- Paper Trading 検証レポートツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数等を集計してレポート出力する CLI を追加。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し、PASS/FAIL 判定を行う。
    - 日付フィルタ (--from / --to) と DB パス指定 (--db / 環境変数 PAPER_TRADING_SQLITE_PATH) をサポート。

- リサーチ（ファクター計算）
  - src/kabusys/research/factor_research.py（実装開始）
    - Momentum / Value / Volatility / Liquidity 等のファクター計算方針を定義、DuckDB による prices_daily / raw_financials 利用の設計を導入。
    - モメンタム (calc_momentum) 等の計算を行うための定数・骨格を実装（詳細実装は続く）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- なし特記事項

### Notes / Known limitations
- .env 自動ロードはプロジェクトルートの検出に依存する（.git または pyproject.toml）。検出できない場合は自動ロードをスキップする。
- calc_regime_multiplier の bear は 0.3 を返すが、注記として generate_signals() が bear 時に BUY シグナルを生成しない設計であるため、multiplier は中間的な安全弁として機能する旨をコメントで明示。
- position_sizing の lot_size は現状全銘柄共通の想定。将来的に銘柄別単元対応を検討する旨の TODO コメントあり。
- monitoring は環境にかかわらず Settings.sqlite_path（本番監視 DB）を使用する設計。paper_trading の監視を完全分離したい場合は運用設定で対応する必要あり。
- research/factor_research の一部実装は継続中（ファイル末尾が実装途中の箇所あり）。

---

（以降のリリースはここに追加していきます）