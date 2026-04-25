CHANGELOG
=========

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
主なセクション: Added（追加）、Changed（変更）、Fixed（修正）、Removed（削除）、Security（セキュリティ）。  
日時は公表日を表します。

Unreleased
----------

- （今後の変更記録用）

[0.1.0] - 2026-04-25
--------------------

初期リリース。KabuSys のコア機能群、CLI ユーティリティ、監視・実行エンジンの起動スクリプト、ペーパートレード検証レポート等を追加。

Added
-----

- 基本情報
  - パッケージバージョンを追加: __version__ = "0.1.0"。
  - パッケージ公開用の __all__ を定義（data, strategy, execution, monitoring）。

- 起動スクリプト / デーモン類
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - ExecutionEngine をスレッドで実行、停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - PID ファイル管理（data/execution.pid）をサポート。
    - RiskManager の既定設定（max_position_pct、max_utilization、rate_limit 等）を組み込み。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計（監視データは本番 DB に記録）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。

- 設定管理 / ユーティリティ
  - config.Settings クラスを追加。
    - 環境変数のラッパー（J-Quants / kabuAPI / DB パス / 監視閾値 / 環境判定等）。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等 paper_trading 向け設定をサポート。
    - env 値検証（KABUSYS_ENV / LOG_LEVEL 等）の実装。
  - 自動 .env ロード機能を追加（プロジェクトルート検出：.git または pyproject.toml を基準）。
    - 読み込み順: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加（CLI）。
    - よく使う設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL 等）に対応。
    - シークレット入力の扱い、既存値の再利用、.env への書き込みを実装。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境用の追加ガードを実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ログ・プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging を追加。
    - StreamHandler（stdout 出力）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の環境変数や引数による上書き、既存ハンドラのクリアを実装。
  - utils.process_priority を追加。
    - プラットフォーム差分を吸収してプロセス優先度（high/normal/low）を設定する set_process_priority 実装。
    - CPU Affinity を設定する set_cpu_affinity を実装（psutil ベース、権限不足時は警告）。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates（スコア降順で上位 N 件選択）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重配分、全スコア 0.0 の場合は等分でフォールバック）
  - portfolio.risk_adjustment:
    - apply_sector_cap（セクター別上限チェックで候補除外）
    - calc_regime_multiplier（market regime による投下資金乗数: bull/neutral/bear）
  - portfolio.position_sizing:
    - calc_position_sizes（allocation_method: risk_based / equal / score をサポート）
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash を超える場合のスケーリング）を実装。
    - cost_buffer を考慮した保守的コスト見積り、残差処理によるロット単位での追加配分ロジックを搭載。

- 研究 / ファクター計算（骨格）
  - research.factor_research モジュールを追加（モメンタム、ボラティリティ、バリュー等の計算方針と定数定義）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する設計。
    - モジュールの冒頭に計算定数（短中長期日数、ATR 期間等）を定義。
    - （注意）ファイル末尾で calc_momentum の実装が途中で終わっている箇所あり（今後実装継続予定）。

- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成ツールを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ 等。
    - デフォルト閾値を設定（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200ms）。
    - --from/--to/--db オプションで期間・DB を指定可能。PAPER_TRADING_SQLITE_PATH 環境変数に対応。
    - DB のテーブル欠損時の堅牢性を考慮した例外処理（OperationalError を捕捉して N/A を返す）。

Changed
-------

- 監視・実行の挙動
  - run_monitoring は MONITOR_POLL_INTERVAL 環境変数を導入し、ポーリング間隔の調整を可能にした（デフォルト 60 秒）。
  - run_monitoring と run_execution の起動時に set_process_priority("high") を呼び出してプロセス優先度を上げるようにした。

- .env 読み込みルール
  - プロジェクトルート探索ロジックを導入（.git または pyproject.toml を基準）。これにより CWD に依存しない自動 .env ロードを実現。

Fixed
-----

- 設定検証の堅牢性向上
  - validate_config にて PyYAML 未インストール時に YAML 検証をスキップしつつ警告を出すようにした。
  - .env 解析の改善（export 形式対応、引用符の中のエスケープ処理、コメント取り扱いの改善）。

- ログ出力の安定性
  - logging_setup でログディレクトリ作成失敗時にファイルハンドラを安全にスキップし、コンソール出力のみで継続するようにした。

- プロセス優先度設定のフォールトトレランス
  - process_priority.set_process_priority / set_cpu_affinity は権限不足やプラットフォーム非対応時に警告を出してスキップするようにした（例外を投げない）。

Removed
-------

- 初期リリースのため、削除項目なし。

Security
--------

- 本リリースでは機密情報（トークン、パスワード）を .env に保存する設計のため、.env を決してリポジトリにコミットしない旨を明記（config_setup の出力ヘッダに注意喚起を追加）。

Notes / Known issues
--------------------

- research.factor_research.calc_momentum の実装が途中で切れている箇所が存在します。ファクター計算の各関数は今後追加実装・テスト予定です。
- run_monitoring は設計上「監視は常に本番 sqlite_path を使用」するため、開発環境で監視データを別 DB に隔離したい場合は現行実装では対応していません（将来的にオプション化を検討）。
- position_sizing の価格フォールバック：open_prices に欠損（0.0）があるとエクスポージャー評価が過少見積りされる可能性があり、将来的に前日終値や取得原価等のフォールバックを検討する旨をコメントで残しています。

参考: 環境変数一覧（主なもの）
- KABUSYS_ENV (development | paper_trading | live) — 実行環境
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API 用
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- LOG_LEVEL (default: INFO)
- LOG_DIR — ログ保存先
- MONITOR_POLL_INTERVAL — 監視のポーリング間隔（秒）
- PAPER_FILL_MODE — paper_trading の mock fill 動作（instant/partial/never/reject）

以上。