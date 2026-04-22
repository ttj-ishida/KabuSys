# Changelog

すべての重要な変更は Keep a Changelog の慣習に従って記録しています。  
フォーマット: https://keepachangelog.com/ja/

注意: 以下はリポジトリ内のソースコードから機能・振る舞いを推測して作成した初期の変更履歴です。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-22
初回リリース — 基本コンポーネントと CLI ユーティリティを実装。

### Added
- 基本パッケージ情報
  - kabusys パッケージの初期バージョンを設定（__version__ = "0.1.0"）。

- 実行エントリ / ランタイム
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) をサポート。
    - RiskManager に既定のパラメータを設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。initial_portfolio_value を broker.get_available_cash() で初期化。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視用 DB 接続は環境に依らず本番 sqlite_path を使用（監視テーブル初期化を実施）。
    - 停止フラグ (data/stop_requested.flag) を監視してループ終了。

- 環境設定 / 検証
  - config.py: 環境変数・設定管理モジュールを追加。
    - .env の自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml を起点）。
    - .env パーサは export 形式・クォート・エスケープ・インラインコメントに対応。
    - Settings クラスを実装し、J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定プロパティ等を提供。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の検証。
    - settings インスタンスをモジュールレベルで公開。

  - config_setup.py: .env を対話式に作成・更新するウィザード CLI を追加。
    - 対話入力で主要設定（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LOG_LEVEL 等）を生成。
    - .env を安全なフォーマットで書き出す機能を提供。

  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML が利用可能な場合は）パース検証を行う。
    - --strict モードをサポート（警告も失敗扱いにできる）。

- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順選抜（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコア 0 の場合は等配分にフォールバック）を実装。

  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限をチェックして候補をフィルタリング（未知セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知は 1.0 にフォールバック）。

  - portfolio/position_sizing.py:
    - calc_position_sizes: 指定の割当方式（risk_based / equal / score）に基づいて銘柄ごとの買付株数を算出。
    - 単元株（lot_size）丸め、per-position 上限・aggregate cap のスケールダウン、cost_buffer を考慮した保守的見積り等を実装。

  - portfolio パッケージの __all__ を通じて主要機能をエクスポート。

- ユーティリティ
  - utils/logging_setup.py:
    - 統一ログ設定ユーティリティ。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順をサポートし、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。

  - utils/process_priority.py:
    - プロセス優先度（high/normal/low）設定をクロスプラットフォームで実装（Windows の priority class / POSIX の nice）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合は警告出力でスキップ。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成 CLI を追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を計算して標準出力にレポートを出力。
    - デフォルトおよび閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 latency 200 ms）を設定。
    - 日付フィルタ (--from/--to)、DB パス指定 (--db) をサポート。
    - P95 計算ロジックを実装。

- データ分析 / リサーチ（初期実装）
  - research/factor_research.py:
    - モメンタム等のファクター計算モジュールの骨組みと定数を追加。DuckDB 接続を受け取り prices_daily / raw_financials を用いる方針で設計。
    - calc_momentum の関数スケルトンと多数の定数（期間やウィンドウ長）を追加（将来的な拡張を想定）。

### Changed
- なし（初回リリース）

### Fixed
- なし

### Removed
- なし

### Security
- なし

---

注記 / 実装上の注意点（コードから読み取れる運用上のポイント）
- .env の自動読み込みはデフォルトで有効。テストなどで無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定する。
- run_monitoring と run_execution の両方で起動時にプロセス優先度を "high" に設定する呼び出しが入っている（set_process_priority）。
- run_monitoring は監視 DB 初期化を行い、duckdb は分析用途に接続する構成。monitoring は環境に関わらず本番 sqlite_path を使う点に注意。
- run_execution は paper_trading モードでは DB を分離し、MockBroker を利用する想定（BrokerClientFactory による切替）。
- ロギングは stdout を使う設計（cron 等で stdout/stderr を一本化しておく運用に配慮）。
- 一部ファイル（例: research/factor_research.py）が実装途中の形跡あり。追加実装・テストが必要。

もしリリースノートの粒度（たとえばコミットごとの詳細や既知の issue の記載）をさらに細かく反映したい場合は、コミットログや issue トラッカーを提供してください。