CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠します。  
新しいエントリは上から順に配置しています。

[Unreleased]
------------

0.1.0 - 2026-04-19
------------------

Added
- 基本リリース: KabuSys パッケージの初期実装を追加。
  - パッケージバージョンを __version__ = "0.1.0" として公開。
- 実行用スクリプト:
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB (PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のバックグラウンド実行（スレッド）に対応。
    - 停止フラグ (data/stop_requested.flag) と PID 管理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動用エントリポイントを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔指定をサポート（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視用 DB 初期化（monitoring 用テーブル）および DuckDB 接続を確立。
    - 停止フラグの検出で安全にループ終了。
- 設定関連:
  - config.py: Settings クラスを追加し、環境変数の取得・検証を一元管理。
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を探索）。
    - .env と .env.local の読み込み順序、OS 環境変数保護（上書き禁止）の仕組みを実装。
    - 各種設定プロパティを提供（J-Quants / kabu API / DB パス / Paper Trading 関連 / 監視閾値 / ログレベル等）。
    - PAPER_FILL_MODE の妥当性チェック、KABUSYS_ENV の妥当性チェックを実装。
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を提供。
    - 複数の設定項目（環境、API トークン、DB パス、ログレベル、Kill Switch 等）を対話的に編集・保存可能。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスや config/*.yaml ファイルの存在・YAML パース検証、live 環境向け追加警告などを実行。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス管理ユーティリティ:
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を設定する setup_logging を実装。
    - LOG_DIR 作成失敗時はファイル出力をスキップし、コンソールのみで継続するフォールバックを組み込み。
    - 既存ハンドラのクリア処理を実装して二重設定を防止。
  - utils/process_priority.py:
    - プラットフォーム差（Windows / POSIX）を吸収してプロセス優先度を設定する set_process_priority を実装。
    - CPU affinity を設定する set_cpu_affinity を提供（core 数指定に応じて最初の N コアにピン留め）。
    - psutil の権限エラーや未実装 API に対する安全なフォールバック（警告ログ）を実装。
- ポートフォリオ構築モジュール:
  - portfolio/portfolio_builder.py:
    - シグナル選定(select_candidates)、等金額/スコア加重の重み計算(calc_equal_weights / calc_score_weights) を実装。
    - スコアが全て 0 の場合のフォールバックとログ出力を実装。
  - portfolio/risk_adjustment.py:
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有のセクター別エクスポージャ計算と候補除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear マッピングと未知レジームのフォールバック）。
  - portfolio/position_sizing.py:
    - 株数決定ロジック calc_position_sizes を実装。
      - allocation_method に応じた計算 (risk_based / equal / score)。
      - 単元（lot_size）丸め、1 銘柄上限・総投下上限（aggregate cap）のスケーリング、cost_buffer を用いた保守的見積り、残差処理による追加配分のロジックを実装。
- ツール・レポート:
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill/send）、リスク却下数、レイテンシ（平均/最大/P95）などの集計と PASS/FAIL 判定閾値を実装。
    - --from / --to / --db オプションで期間・DB を指定可能。
- 研究用モジュール（未完/着手）:
  - research/factor_research.py (着手):
    - Momentum/Value/Volatility/Liquidity の計算方針と定数を追加。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - モメンタム計算 calc_momentum のインタフェースが定義され、実装が開始されている（ファイル末尾が途中で切れているため追加実装が必要）。

Changed
- ログ出力先の設計:
  - コンソール出力を stdout に統一（cron 等からのリダイレクトを想定）。
- .env 読み込み:
  - export KEY=val 形式やシングル/ダブルクォートのエスケープ、インラインコメント処理など実用的なパーサーを実装。
  - .env.local は OS 環境変数を保護しつつ上書き可能にした（override=True での読み込み）。

Fixed
- MONITOR_POLL_INTERVAL の不正値に対する安全性向上:
  - 0 以下や数値以外が設定された場合はデフォルトにフォールバックして予期せぬ ValueError を防止。
- DB 初期化呼び出しの冪等性:
  - init_monitoring_db を起動スクリプト側で確実に呼び出して監視テーブルが存在することを保証（既存 DB でも安全に動作）。

Security
- API シークレット（J-Quants / kabu API）の .env での取り扱いをウィザードで secret マスク表示にして、.env をコミットしない旨の注意を明記。

Known issues / TODO
- research/factor_research.calc_momentum の実装が途中で終わっている（ファイル末尾が切れている）。完全実装が必要。
- position_sizing の価格欠損（price == 0 の場合）のフォールバック処理は TODO コメントを残しており、前日終値などの代替価格戦略を検討する必要がある。
- apply_sector_cap は sector_map に存在しない code を "unknown" 扱いにしているが、unknown セクターに対するポリシー（上限適用の有無）を明確化する必要がある。
- Windows / 一部 OS での優先度設定や CPU affinity が権限や未実装 API のためスキップされるケースがある（処理は安全にフォールバックするが、運用ドキュメントに注意事項を追記予定）。

Acknowledgments
- 初期設計では DuckDB と SQLite を併用し、分析データとランタイム監視/トレードログを分離するアーキテクチャを採用しています。これにより Paper Trading と Live 環境の DB 分離が容易になっています。

---

注:
- 本 CHANGELOG は提示されたコードベースから機能・振る舞いを推測して作成しています。実装の細部や将来の変更により差分が生じる可能性があります。