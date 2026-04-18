# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。  
このリポジトリは初回リリースとしてバージョンを設定しています。

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション情報とバージョン番号を追加
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
    - .env と .env.local の読み込み順序、OS 環境変数保護（protected）を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 複数の設定プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE、PID/KILL フラグ関連、リソース閾値、ログレベル、環境判定等）。
    - .env パースは export 構文、クォート内のエスケープ、インラインコメント扱いなどに対応。

- 環境設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する機能を追加。
    - デフォルト値、シークレット表示（マスク）、選択肢、キャンセルハンドリングを実装。
    - .env の読み書きロジックを備え、保存確認を行う。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml の妥当性をチェックする CLI を追加。
    - 必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML がない場合は警告）を実装。
    - KABUSYS_ENV=live の際の追加警告（LINE 通知設定や kill flag の扱い）を追加。
    - --strict オプションで警告を FAIL 扱いにする機能を追加。

- 実行エンジン起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを行う。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（MockBroker を含む想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立て、別スレッドで run_session を実行。PID ファイル管理と停止フラグ（data/stop_requested.flag）を監視して安全に停止する。

- 監視（モニタリング）起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor をポーリングで起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視用 DB 初期化（init_monitoring_db）を行い、Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）の検知でループ終了。
    - 例外時はログを残して次回ポーリングへフォールバック。

- 監視 DB 初期化ユーティリティ参照
  - run_monitoring / run_execution から monitoring_db.init_monitoring_db を呼び、監視用テーブルの存在を冪等に保証。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から統計を集計し、検証レポートを標準出力へ出力するスクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数などの指標を算出し、PASS/FAIL 判定を行う。
    - デフォルト閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を設定。
    - --from / --to / --db オプションをサポート。

- ポートフォリオ構築ライブラリ
  - src/kabusys/portfolio/*
    - portfolio_builder.py
      - 候補選定 select_candidates（スコア降順、同点は signal_rank 昇順）。
      - 等金額配分 calc_equal_weights。
      - スコア加重配分 calc_score_weights（合計スコアが 0 の場合は等金額にフォールバック）。
    - risk_adjustment.py
      - apply_sector_cap: セクター別上限チェック（既存保有比率が max_sector_pct を超えるセクターの新規候補を除外）。"unknown" セクターは除外しない。
      - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear マッピング、未知のレジームは警告して 1.0 でフォールバック）。
    - position_sizing.py
      - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数算出。リスクベースの計算、単元（lot_size）丸め、per-position と aggregate のキャップ、available_cash によるスケールダウンロジック、cost_buffer（スリッページ/手数料想定）考慮を実装。
      - スケーリング後の残差処理（fractional remainder）により lot 単位で再配分。

- リサーチ（ファクター計算）の土台
  - src/kabusys/research/factor_research.py
    - モメンタム・バリュー・ボラティリティ・流動性等のファクター計算モジュール骨格を追加。DuckDB 接続を受けて prices_daily / raw_financials テーブルを参照する設計。
    - モメンタム計算 calc_momentum のシグネチャとドキュメントを追加（内部実装の続きあり）。

- ログ設定ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - setup_logging(app_name, log_dir, level) を追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（デフォルト logs/<app_name>.log 日次ローテート、30 世代保持）を設定。
    - 既存ハンドラをクリアして二重設定を防止。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力にフォールバック。ログレベル/ログディレクトリは引数→環境変数→デフォルトの優先順位で解決。

- プロセス優先度・CPU affinity ユーティリティ
  - src/kabusys/utils/process_priority.py
    - set_process_priority(level) により Windows/Linux/macOS で適切に nice / priority を設定（psutil 使用、許容されない場合は警告してスキップ）。
    - set_cpu_affinity(cpu_count) でプロセスを最初の N コアにピン留め（psutil がサポートする場合）。
    - クロスプラットフォーム差分を吸収する実装。

### Changed
- （初回リリースのため主な変更はなし。将来のバージョンで API/仕様変更を記載予定）

### Fixed
- （初回リリースのため無し）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- （該当なし）

### Notes / Known issues
- src/kabusys/research/factor_research.py の calc_momentum 実装が途中で終わっている箇所（ソース末尾に "start_da" で切れている）。ファクター計算の完全実装は今後のコミットで追加予定。
- position_sizing.py と risk_adjustment.py のいくつかの箇所に TODO コメントあり（価格欠損時のフォールバック戦略や将来的な lot_size の銘柄別対応）。実運用前に該当ロジックの追加検討が必要。
- .env の書き込み対象ファイルは .env を想定しており、機密情報(.env の内容)は Git 管理下にコミットしないよう注意する旨の警告を config_setup に記載。
- validate_config は PyYAML 未インストール時に YAML 内容検証をスキップして警告を出す仕様。YAML 検証を有効にするには PyYAML をインストールすること。

---

今後のリリースでは、ファクター計算の完成、ExecutionEngine / SystemMonitor のテスト補強、ドキュメント強化、及び実稼働向けの運用ドキュメント（デプロイ/監視/バックアップ手順）を予定しています。