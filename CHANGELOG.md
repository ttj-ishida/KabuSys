# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このプロジェクトのバージョニングは SemVer に従います。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-23

### Added
- 基本ランタイム / 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite DB を使用（data/paper_trading.db がデフォルト）し、MockBrokerClient を利用して本番 DB と完全分離する設計。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) を監視し、フラグ検知時に Engine を安全に停止。
    - 実行中の PID を data/execution.pid に保存するための pid_file サポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず監視用の本番 sqlite_path を使用（監視データは共通 DB に格納する想定）。
    - 停止フラグ (data/stop_requested.flag) を検知してポーリングループを終了。
    - 例外発生時にはログを残して次ポーリングに移行。

- 設定管理
  - config.py:
    - .env/.env.local の自動読み込み機能を追加（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパースは export プレフィックス、クォート、エスケープ、インラインコメント等に対応する堅牢な実装。
    - Settings クラスを導入し、各種環境変数（DB パス、API トークン、Paper Trading 設定、監視閾値、KABUSYS_ENV 等）をプロパティ経由で取得・検証。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性検査を実装。

- 設定ユーティリティ CLI
  - config_setup.py: 対話式ウィザードで .env ファイルを初期作成・更新するツールを追加。
    - 必須・任意項目のプロンプト、既存 .env の読み込み、保存前の確認を実装。
  - validate_config.py: .env および config/*.yaml の事前検証ツールを追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML のパース検証（PyYAML 未導入時は警告）、
      KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や Kill Flag の自動クリア設定の注意喚起）などを実施。
    - --strict モードで警告も FAIL 扱い可能。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - StreamHandler（stdout）および TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定する共通ユーティリティを追加。
    - LOG_DIR / LOG_LEVEL の解決順やファイル出力失敗時のフォールバックを実装。
    - コンソール出力は stdout を使用（cron 等の出力リダイレクトを想定）。
  - utils/process_priority.py:
    - Windows / POSIX（Linux/Mac/FreeBSD）でのプロセス優先度設定を吸収するユーティリティを追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合は警告をログに出力してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順ソートと上位 N 抽出。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算。スコアが全て 0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクターごとの既存エクスポージャーに基づく新規候補除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（フォールバックと警告含む）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: risk_based / equal / score の各配分方式に対応した株数計算。lot_size（単元）丸め、1銘柄上限・aggregate cap によるスケールダウン、cost_buffer を考慮した保守的なコスト推定、端数処理ロジックを実装。

  注: 上記ポートフォリオモジュールは純粋関数であり、DB 参照は行わずメモリ内計算のみ。

- 研究用ファクター計算
  - research/factor_research.py:
    - DuckDB 接続を受けて Momentum / Value / Volatility / Liquidity 系のファクターを計算する設計を導入（prices_daily / raw_financials テーブル参照、Zスコア正規化は外部ユーティリティを利用する前提）。
    - モメンタムに関する定数（1M/3M/6M、MA200 等）を定義し calc_momentum の雛形を実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading (SQLite) の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill）、送信率（send）、P95 レイテンシなどを算出し、閾値に基づく PASS/FAIL 判定を行う。
    - 日付フィルタ（--from / --to）および DB パス指定（--db / 環境変数）に対応。
    - P95 計算、欠損データ時の N/A 表示、テーブル欠損時の例外耐性を実装。

- パッケージ情報
  - パッケージ初期バージョン __version__ = "0.1.0" を設定。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Notes / Important behavior
- Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（監視 DB）を使用します。監視 DB と paper_trading DB は用途によって明確に分離されていますが、運用時は DB パスの設定に注意してください。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を探索）に依存します。プロジェクトルートが特定できない場合は自動ロードをスキップします。
- run_execution / run_monitoring は起動時にプロセス優先度を high に設定しようとしますが、権限不足や未対応 OS の場合は警告を出してスキップします。
- ログファイル作成に失敗した場合はコンソール出力のみで継続します。

---

過去リリースはありません（初回公開）。今後は機能追加・API 変更・バグ修正ごとにセクションを追加していきます。