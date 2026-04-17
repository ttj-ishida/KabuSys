# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

最新の変更は一番上に記載します。

## [0.1.0] - 2026-04-17

Added
- 初期リリース: KabuSys のコアユーティリティ・CLI・モジュールを追加。
- 設定管理:
  - 環境変数読み込み・管理モジュールを追加（kabusys.config）。
  - プロジェクトルート（.git または pyproject.toml）を基準に .env 自動ロードを行う機能を実装。
  - .env の自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パースの強化: export プレフィックス対応、クォート／エスケープ、インラインコメントへの対応。
  - Settings クラスを提供し、J-Quants / kabu API / DB /監視閾値などの取得と妥当性チェックを行う。
  - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）を実装。

- 設定支援 CLI:
  - 対話式 .env 作成ウィザード（kabusys.config_setup）を追加。
    - デフォルト値、選択肢、シークレットマスク表示、保存プレビュー機能を持つ。
    - .env を安全なテンプレート形式で出力（Git にコミットしないよう注意喚起を出力）。

- 設定検証 CLI:
  - kabusys.validate_config を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML がある場合）パース検証。
    - KABUSYS_ENV=live 向けの追加ガード（LINE 未設定、KILL_FLAG_CLEAR_ON_START の警告等）。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行周りスクリプト:
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - プロセス優先度を最初に "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH/ data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（paper_trading では Mock を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと実行（スレッド実行、stop flag による停止）。
    - RiskManager に対する初期設定値（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）をデフォルトで設定。

  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒。0 以下は無効扱いしてデフォルトへフォールバック）。
    - 監視（Monitoring）は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化（init_monitoring_db）。
    - stop flag（data/stop_requested.flag）検出でループを安全に終了。
    - check_once() 実行中の例外はログに残して次ポーリングへ継続。

- 監視 DB 初期化:
  - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等操作）。

- DuckDB 統合:
  - DuckDB 接続を受け取って分析処理を行う設計を導入（Settings.duckdb_path デフォルト: data/kabusys.duckdb）。

- プロセス管理ユーティリティ:
  - set_process_priority / set_cpu_affinity を実装（kabusys.utils.process_priority）。
    - Windows と POSIX（Linux / macOS / FreeBSD）を吸収し psutil を使って優先度設定／CPU affinity 固定を行う。
    - アクセス権限や未対応 OS の場合は警告を出して安全にフォールバック。

- ポートフォリオ構築モジュール（kabusys.portfolio）:
  - 候補選定・重み計算（portfolio_builder）:
    - select_candidates: スコア降順・タイブレークに signal_rank を使用。
    - calc_equal_weights / calc_score_weights（スコア全0 の場合は等金額配分へフォールバック）。
  - リスク調整（risk_adjustment）:
    - apply_sector_cap: セクター集中上限を評価して候補を除外（unknown セクターは適用しない）。
    - calc_regime_multiplier: market regime に基づく投入資金乗数（bull/neutral/bear、未知値はフォールバックで 1.0）。
  - ポジションサイジング（position_sizing）:
    - calc_position_sizes: risk_based / equal / score の allocation_method をサポート。
    - 単元株丸め（lot_size）、ポジション上限、aggregate cap（available_cash を超える場合のスケールダウンと端数の再配分）を実装。
    - cost_buffer による保守的コスト見積りをサポート。

- 研究用ファクターモジュール（kabusys.research.factor_research）:
  - calc_momentum / calc_volatility などを実装。
  - DuckDB 上の prices_daily テーブルを用いた SQL ベースの計算を行う設計（MA200、1/3/6M リターン、ATR、出来高系指標など）。
  - 大きなウィンドウ／スキャン日数や不足データ時の None 返却のポリシーを明記。

- Paper Trading 検証ツール:
  - tools/paper_verification_report.py を追加。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計してレポート出力。
    - 基準値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を実装。
    - P95 の計算、期間フィルタ（--from/--to）対応、DB 存在チェックを実装。

Changed
- コードベースをモジュール化して CLI（python -m kabusys.<module>）で実行可能にした（config_setup / validate_config / tools など）。
- 設定ファイルの既存値読み込みと、ウィザードでの既存値再利用をサポート。

Fixed
- .env の読込時に OS 側の環境変数を保護する仕組み（protected set）を導入し、既存の OS 環境変数を上書かないように修正。
- run_monitoring のポーリング間隔指定で不正な値が指定された場合に例外を起こさずデフォルトへフォールバックするよう改良。

Security
- .env を生成する際にシークレット値はマスクして表示（config_setup）。
- .env テンプレートに対して "絶対に Git にコミットしないこと" を明示。

Notes / Internal
- パッケージバージョンを __version__ = "0.1.0" として設定。
- ドキュメント参照:
  - PortfolioConstruction.md / StrategyModel.md を参照する旨の注記をコード内に記載（設計に準拠した実装であることを明示）。
- いくつかの TODO／将来拡張メモをソース内に残している（例: lot_size を銘柄別で管理する拡張、position_sizing の価格フォールバック等）。

---

今後のリリースでは以下を検討しています:
- テストカバレッジ追加（ユニットテスト / CI）。
- 銘柄別単元株情報の導入（lot_map）。
- position_sizing の前日終値等のフォールバック価格導入。
- duckdb を活用したより多様な研究指標・可視化の追加。