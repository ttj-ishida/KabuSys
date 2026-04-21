CHANGELOG
=========

All notable changes to this project will be documented in this file.
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

Unreleased
----------

（現在未リリースの変更はありません）

0.1.0 - 2026-04-21
-----------------

初回リリース。以下の主要機能・ユーティリティを追加しました。

Added
- パッケージ基盤
  - パッケージメタ情報: __version__ = "0.1.0" を設定。
  - 公開モジュール群: data, strategy, execution, monitoring をエクスポート。

- 環境設定・設定管理
  - Settings クラス（kabusys.config）:
    - 環境変数・設定値を一元管理（J-Quants / kabu API / DB パス / 各種閾値 等）。
    - KABUSYS_ENV の妥当性チェック（development / paper_trading / live）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）や PID / Kill-flag パス等を提供。
  - 自動 .env ロード:
    - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込み（OS 環境変数優先）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止可能。
  - .env パーサ:
    - export プレフィックス対応、クォート（シングル/ダブル）内のバックスラッシュエスケープ処理、
      インラインコメント扱いルール等をサポート。

- 設定関連 CLI
  - 環境設定ウィザード（kabusys.config_setup）:
    - 対話式で .env を作成 / 更新するウィザードを提供（シークレット項目はマスク表示）。
    - デフォルト設定や選択肢を用意（KABUSYS_ENV, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）。
  - 設定検証ツール（kabusys.validate_config）:
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証。
    - DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証。
    - 本番（live）向けのガード条件チェック（LINE 通知設定や Kill flag の自動クリアに関する警告）。
    - --strict オプションで警告を失敗扱い（exit(1)）にできる。

- 実行用スクリプト
  - 実行エンジン起動スクリプト（kabusys.run_execution）:
    - ExecutionEngine の起動処理およびスレッド管理を実装。
    - プロセス優先度を高く設定して起動（utils.process_priority）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 組立て。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - 実行中の PID ファイル（data/execution.pid）取り扱い。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）:
    - SystemMonitor を定期実行するポーリングループを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は常に本番用 sqlite_path を使用（環境変数に関わらず）。
    - 停止フラグ検知でループを終了し、リソースをクローズ。

- 監視・モニタリング関連
  - init_monitoring_db（監視用テーブル初期化）を呼び出して監視テーブルの存在を保証（冪等）。

- ロギング / プロセスユーティリティ
  - logging_setup（kabusys.utils.logging_setup）:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート、30日保持）を統合して設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみ継続。
    - ログレベルとログディレクトリの解決順（引数 > 環境変数 > デフォルト）。
  - process_priority（kabusys.utils.process_priority）:
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU アフィニティ設定用 set_cpu_affinity を提供。
    - 権限不足や非対応環境では安全にフォールバックして警告を出す。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順・同点タイブレークで候補選定。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分（全スコア 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限をチェックして新規候補をフィルタリング（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた資金乗数（bull/neutral/bear → 1.0/0.7/0.3）。未知レジームは警告の上 1.0 にフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score の配分ロジックを実装。lot_size による丸め、1銘柄上限、aggregate cap によるスケールダウン（余剰端数を公平に配分するアルゴリズムを実装）。
    - 手数料・スリッページ見積り用の cost_buffer を考慮。

- Paper Trading / 検証ツール
  - tools.paper_verification_report:
    - paper_trading の SQLite（デフォルト data/paper_trading.db）を解析して検証レポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、API レイテンシ（avg/max/P95）。
    - 判定閾値と PASS/FAIL 判定ロジックを実装（P95 の計算を含む）。
    - --from / --to / --db オプションで期間・DB を指定可能。

- 研究用モジュール（開発中）
  - research.factor_research:
    - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクター算出設計を追加（モジュール設計と定数を定義、モメンタム計算関数の骨格を実装中）。

Changed
- （初回リリースのため履歴なし）

Fixed
- （初回リリースのため履歴なし）

Security
- （初回リリースのため記載なし）

Notes / 重要な動作・運用メモ
- 監視（run_monitoring）は常に本番用の sqlite_path を使用します。テスト目的で監視 DB を分離したい場合は運用上の工夫が必要です。
- 実行（run_execution）は KABUSYS_ENV=paper_trading の場合、paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）および Mock ブローカーを使い、本番 DB とは完全に分離されます。
- .env をリポジトリにコミットしないでください（config_setup のヘッダにも注意書きあり）。
- system/process stop フラグは data/stop_requested.flag（プロジェクトルート直下の data ディレクトリ）を使用します。運用で外部ツールからフラグを立てることで安全停止が可能です。
- ログはデフォルトで logs/<app_name>.log に日次ローテートで保存されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

今後の改善候補（想定）
- portfolio.position_sizing: 銘柄ごとの lot_size マップ対応（現状は全銘柄共通の lot_size）。
- price フォールバックロジック: risk_adjustment の exposure 計算や position_sizing の価格欠損時の扱い改善。
- research.factor_research: ファクター計算の完全実装とテスト、DuckDB クエリ最適化。
- テストカバレッジの追加（特に環境パース・資金配分アルゴリズム・スケーリングロジック）。

以上