# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-23
初回リリース。KabuSys のコアユーティリティ、実行用スクリプト、ポートフォリオ構築ロジック、設定/検証ツール、ペーパートレード検証機能などを追加しました。

### 追加 (Added)
- 全体
  - パッケージの初期バージョンを 0.1.0 に設定。
  - パッケージ概要モジュールを追加（kabusys.__init__）。

- 実行 / 監視スクリプト
  - run_execution.py
    - ExecutionEngine 起動用エントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine をスレッドで起動。
    - 停止制御: data/execution.pid および data/stop_requested.flag を使用して起動/停止を管理。
    - プロセス優先度を最初に High に設定。
    - DuckDB 接続（分析用 DB）を併用。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。不正値はデフォルトにフォールバックし、警告を出力。
    - 監視は環境にかかわらず本番の sqlite_path を使用（monitoring DB として data/monitoring.db を想定）。
    - 停止フラグ（data/stop_requested.flag）と KeyboardInterrupt を検知してクリーンに終了。
    - プロセス優先度を High に設定。

- 設定管理
  - config.py
    - .env の自動読み込み機能を追加（プロジェクトルート検出: .git or pyproject.toml）。
    - .env 読み込み順序: OS 環境変数 > .env.local > .env。自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
    - 環境変数パースの堅牢化（export プレフィックス、シングル/ダブルクォート、インラインコメント処理など）。
    - Settings クラスを実装し、J-Quants / kabu API / LINE / DB / 監視閾値 / システム設定等のプロパティを提供。
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path、pid/kill flag path、閾値設定（CPU/MEM/DISK）などを含むユーティリティを追加。

  - config_setup.py
    - 対話式 .env 作成ウィザードを追加。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）と説明、デフォルト値、シークレット扱いをサポート。
    - 既存 .env の読み込み・再利用、最終確認後に .env を書き込み。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML 利用可の場合）を実装。
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング / プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。
    - StreamHandler を stdout に出力、TimedRotatingFileHandler による日次ローテーション（30日保持）をサポート。
    - LOG_LEVEL / LOG_DIR の解決順を実装、既存ハンドラのクリアを行う。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみ継続。

  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加。
    - Windows / POSIX(nice) をサポートし、"high"/"normal"/"low" レベルを指定可能。
    - CPU affinity を設定する set_cpu_affinity() を提供。
    - psutil のアクセス権限や未対応 OS を考慮して安全にフォールバックする。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等重配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - calc_score_weights は全スコアが 0 の場合に等重配分へフォールバックして警告を出力。

  - portfolio/risk_adjustment.py
    - セクター集中制限を行う apply_sector_cap を追加（既存保有のセクター別時価から上限を判定して候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear のマップ、未知レジームはフォールバックと警告）。

  - portfolio/position_sizing.py
    - ポジションサイズ算出 calc_position_sizes を追加。
    - allocation_method に応じた株数算出（risk_based / equal / score）を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケールダウンと端数処理）や cost_buffer を考慮した拘束を実装。
    - 価格欠損時のスキップやログ出力を行う。

  - portfolio/__init__.py
    - 上記ポートフォリオ関数群をパッケージ公開。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ (avg/max/P95) を集計。
    - デフォルト閾値: 稼働率 >= 99.0%、成立率 >= 90.0%、送信率 >= 95.0%、P95 <= 200 ms。
    - --from / --to / --db オプションで期間・DB を指定可能。
    - データが不足する場合は N/A を表示し、Fail 条件を列挙。

- リサーチ
  - research/factor_research.py（途中実装）
    - DuckDB を用いたファクター計算モジュールを追加（モメンタム、MA200乖離、ATR、出来高等を想定）。
    - 設計方針や定数、関数 calc_momentum のインターフェースを定義（prices_daily / raw_financials を参照）。

- DB 初期化連携
  - monitoring.monitoring_db.init_monitoring_db を用いて起動時に監視テーブルの存在を保証（init は冪等）。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 非推奨 (Deprecated)
- なし（初回リリース）

### 削除 (Removed)
- なし（初回リリース）

### セキュリティ (Security)
- なし（初回リリース）

注意:
- 一部モジュール（例えば monitoring.system_monitor、monitoring.monitoring_db、execution.* の詳細実装）は本リリース内で別ファイルとして参照されていますが、ここに含まれるスニペットはエントリポイント・ユーティリティ・ポートフォリオロジック・設定まわりに重点を置いています。
- .env ファイルは秘匿情報を含むため、config_setup の出力にある通り Git にコミットしないでください。