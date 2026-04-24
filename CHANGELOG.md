CHANGELOG
=========

すべての注目すべき変更点をここに記録します。このファイルは "Keep a Changelog" の形式に従います。
セマンティック・バージョニングを採用しています。

0.1.0 - 2026-04-24
-----------------

Added
- 全体
  - 初回公開リリース: KabuSys (日本株自動売買システム) の基本コンポーネントを追加。
  - バージョン情報を __version__ = "0.1.0" として定義。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合は Paper Trading 用の専用 SQLite (デフォルト data/paper_trading.db) を使用し、本番 DB と完全に分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（実運用 / モックを切り替え可能）。
    - Engine はデーモンスレッドで実行し、data/stop_requested.flag の検出で安全に停止可能。PID ファイルを書き込む機能あり (data/execution.pid)。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込み。初期ポートフォリオ値は broker.get_available_cash() を使用。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。0 以下の不正値はデフォルトにフォールバックし警告を出す。
    - 監視プロセスは KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視 DB の一貫性確保）。
    - 停止は data/stop_requested.flag の検出で行う。

- 設定管理
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から検出）。
    - 読み込み順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応（より堅牢な解析）。
    - Settings クラスを提供し、各種環境変数（J-Quants / kabuAPI / DB パス / 監視閾値 / ログ等）をプロパティ経由で取得・検証する。
    - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の値チェックを実装（不正値は例外）。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。シークレットは入力時にマスク表示。
    - 既存 .env の読み込み・再利用に対応。ファイル保存前に確認プロンプトを表示。
    - 出力される .env はコメント付きテンプレート形式。

  - validate_config.py
    - 起動前チェック用 CLI を追加。.env と config/*.yaml の検証を行い、errors/warnings/infos を出力。
    - --strict オプションで警告を FAIL 扱いにできる。
    - PyYAML 未インストール時は YAML 検証をスキップして警告を出す。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソールのみ出力。ログレベル決定は引数 > 環境変数 > デフォルトの順。

  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティを追加。
    - Windows 用の優先度定数と POSIX(nice) ベースの設定をサポート。権限不足や未対応プラットフォームは警告でスキップ。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - シグナル候補の選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - スコアが全て 0 の場合は等配分へフォールバックし警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限を行う apply_sector_cap を追加。既存保有を考慮し、一定割合以上のセクターは新規候補を除外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 にフォールバックし警告）。

  - portfolio/position_sizing.py
    - 株数算出ロジック calc_position_sizes を追加。
    - risk_based / equal / score の割当方式をサポート。lot_size（例:100）で丸め、max_position_pct / max_utilization 等の上限を考慮。
    - available_cash を超過する場合のスケーリング処理、cost_buffer による保守的見積り、端数配分アルゴリズムを実装。

- データベース / 分析基盤
  - DuckDB と SQLite を併用する設計を導入。各スクリプトで接続を確立（Settings.duckdb_path / sqlite_path）。
  - monitoring 用テーブル初期化ユーティリティ (init_monitoring_db) を呼び出すことで起動時に冪等的にテーブルを保証。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。期間指定 (--from/--to) や DB パス指定 (--db) に対応。
    - システム稼働率、注文成功率、送信率、P95 レイテンシ等を計算し、閾値（稼働率 99%、成立率 90% 等）で PASS/FAIL 判定を行う。
    - P95 計算や latency 集計、関連テーブルが欠けている場合のフォールバック処理を実装。

- リサーチ
  - research/factor_research.py
    - ファクター計算モジュールの骨子を追加（Momentum, Value, Volatility, Liquidity 等）。DuckDB の prices_daily / raw_financials を参照して計算する設計（実装は一部記述）。

Changed
- なし（初回リリースのため変更履歴無し）

Fixed
- なし（初回リリース）

Security
- 機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_TOKEN 等）は .env に保管し、config_setup のプロンプトではマスク表示するよう配慮。

Notes / Migration
- 初回導入時の推奨手順:
  1. python -m kabusys.config_setup で .env を作成
  2. python -m kabusys.validate_config で設定検証
  3. 実行: python -m kabusys.run_monitoring / python -m kabusys.run_execution
- Paper Trading を行う場合は KABUSYS_ENV=paper_trading を設定して専用 DB (PAPER_TRADING_SQLITE_PATH) を利用してください。
- ログはデフォルトで logs/ に出力されます。ファイル出力が不要な環境では LOG_DIR を変更するかディレクトリ作成権限を確認してください。

今後の予定 (短期)
- research/factor_research の各ファクター計算の完成
- ExecutionEngine / SystemMonitor の追加テスト・障害対策強化
- 銘柄別 lot_size のサポート等、position_sizing の拡張

--------------------------------------------------------------------
（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートと差異がある可能性があります。）