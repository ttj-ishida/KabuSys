CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

0.1.0 - 2026-04-18
------------------

概要:
初期リリース相当の機能群を追加しました。日本株自動売買システムのコア機能（設定管理、実行エンジン起動、監視、ポートフォリオ構築、リスク調整、ポジションサイズ計算、ユーティリティ、検証・セットアップツール、ペーパー検証レポート、ファクター計算基盤など）を実装しています。

Added
- 基本 CLI 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプト。KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite を使用し、本番 DB と完全に分離して動作。
    - 停止フラグ（data/stop_requested.flag）検知による安全な停止処理。
    - 実行時の PID を data/execution.pid に書き出す仕様（pid_file パスは設定で変更可）。
    - ブローカークライアントのファクトリを使用して環境依存のクライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を開始する一連のフロー。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトへフォールバック。
    - 監視用 DB（sqlite）は監視処理が常に本番 sqlite_path を使用する設計（環境に依らず）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。

- 設定・環境関連
  - config.py: 環境変数・設定管理クラス Settings を実装。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env および .env.local の読み込み順序（OS 環境変数を保護する protected 機能）。
    - 複数の設定プロパティ（J-Quants、kabuAPI、LINE、DuckDB/SQLite パス、paper_trading 用 DB、監視閾値、ログレベル、KABUSYS_ENV の検証など）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を提供。
    - シークレット入力のマスク表示、既存値再利用、保存前の確認表示を実装。
    - デフォルトや選択肢を提示する項目定義を整備。

- 検証ツール
  - validate_config.py: 起動前チェック CLI を追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
    - KABUSYS_ENV / LOG_LEVEL 値検証、DB パスの親ディレクトリ存在チェック。
    - config/*.yaml の存在確認と（PyYAML があれば）パースチェック。
    - KABUSYS_ENV=live の追加ガード（LINE 通知設定確認、KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソートと上位 N 抽出（同点は signal_rank でブレーク）。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率配分を計算（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限に基づく候補除外ロジック（sell_codes を除外する挙動をサポート）。
    - calc_regime_multiplier: market regime に応じた投下比率乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数を計算（allocation_method: "risk_based"/"equal"/"score"）。
    - 単元株（lot_size）丸め、per-position 最大、aggregate cap（available_cash を超える場合のスケールダウンと残差配分）を実装。
    - cost_buffer による保守的コスト見積り（スリッページ・手数料を考慮）。

- リサーチ基盤
  - research/factor_research.py（モメンタム等ファクター計算基盤を実装）
    - DuckDB 接続を受け、prices_daily / raw_financials テーブルを参照してモメンタム・ボラティリティ等の定量ファクターを計算する設計（関数 calc_momentum 等の実装に着手）。

- ツール
  - tools/paper_verification_report.py: ペーパー取引結果の検証レポート生成スクリプト。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）等を集計して PASS/FAIL 判定を出力。
    - コマンドライン引数で期間指定（--from/--to）と DB 指定（--db）をサポート。
    - デフォルト DB は data/paper_trading.db を参照（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ロギング設定ユーティリティ（console stdout と TimedRotatingFileHandler による日次ローテーション、30 日保持）。
    - LOG_LEVEL / LOG_DIR の解決順を提供。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 固定機能を提供。
    - 権限不足や未対応 OS 時には警告を出して安全にフォールバック。

- DB 初期化サポート
  - monitoring/monitoring_db.init_monitoring_db を各起動スクリプトから呼び出して監視テーブルが存在することを保証（冪等処理）。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Security
- 初期リリースのため該当なし。

Notes / 使用上の重要点
- .env 自動ロード:
  - プロジェクトルート検出により、カレントワーキングディレクトリに依存せず .env の自動読込を行う。
  - OS 環境変数は保護され、.env.local の override でも保護される。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途）。
- Paper trading 分離:
  - KABUSYS_ENV=paper_trading の場合、run_execution は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番監視 DB（monitoring.db）とは分離している。
- 監視プロセス:
  - run_monitoring は監視用 DB に本番 sqlite_path を常に使う設計（環境にかかわらず）。
- 停止制御:
  - stop_requested.flag（data/stop_requested.flag）と PID ファイルにより外部からの安全停止／監視が可能。
- ログ:
  - 日次ローテーション、30 日保持。ファイル作成に失敗した場合は stdout のみで稼働。
- 設定検証:
  - validate_config により起動前に必須設定・YAML の妥当性・本番ガードをチェックできる。

BREAKING CHANGES
- なし（初期リリース）。

今後の予定（未実装・改善点のメモ）
- research/factor_research の完全実装（関数群の完成・テスト）。
- 銘柄別の lot_size をホストするマスタ導入（position_sizing の拡張）。
- price の欠損時のフォールバック（前日終値や取得原価など）を実装してエクスポージャー算出の精度を向上。
- テストカバレッジの拡充・CI 統合。

貢献
- 初期実装に関するフィードバックやバグ報告は歓迎します。