CHANGELOG
=========

すべての重要な変更は Keep a Changelog の慣習に従って記載します。  
フォーマット: https://keepachangelog.com/ja/ に準拠しています。

現在のリリース
--------------

[0.1.0] - 2026-04-23
-------------------

Added
- 初回リリース。システム全体の基盤機能を実装しました。
  - 基本メタ情報
    - パッケージバージョンを __version__ = "0.1.0" に設定。
  - 設定 / 環境変数管理
    - 環境変数自動ロード: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - .env パーサー: export 文、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - Settings クラス: 各種設定プロパティ（J-Quants/Kabu API、データベースパス、Paper Trading 設定、監視閾値、実行環境フラグなど）を提供。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
  - 設定支援ツール
    - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を実装。シークレット表示マスク、選択肢サポート、保存確認を含む。
    - validate_config.py: .env と config/*.yaml の事前検証 CLI を実装。必須/任意環境変数チェック、パス存在 (親ディレクトリ) チェック、YAML のパース検証（PyYAML があれば実施）、本番環境向けガード警告、--strict モードをサポート。
  - 実行スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを実装。
      - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用して本番 DB と分離（README 等の指示に従う）。
      - BrokerClientFactory 経由でブローカークライアント生成（paper/live を透過的に扱う想定）。
      - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み合わせて実行。ExecutionEngine はスレッドで run_session を起動し、data/execution.pid に PID を出力。
      - 停止フラグ(data/stop_requested.flag) 検出で安全停止。
      - RiskManager のデフォルトパラメータを実装（max_position_pct, max_utilization, rate_limit_per_sec 等）。初期ポートフォリオ値に broker.get_available_cash() を使用。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを実装。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、1 秒未満や不正値はデフォルトにフォールバック）。
      - 監視プロセスは環境に関わらず本番 sqlite_path を使用する（監視用 DB の一元化）。
      - stop flag 検出でループを終了、KeyboardInterrupt ハンドリング、DB 接続のクリーンアップを実施。
  - 監視・モニタリング関連
    - monitoring_db の初期化呼び出し（init_monitoring_db）を起動スクリプトで保証（冪等）。
    - SystemMonitor の呼び出しポイントを提供（check_once 呼び出しループ）。
  - ロギング / プロセス制御ユーティリティ
    - utils/logging_setup.py: 統一的なログ設定ユーティリティを提供。
      - stdout へ StreamHandler、さらに 日次ローテートの TimedRotatingFileHandler を設定（logs/<app_name>.log, 30 日保持）。
      - LOG_DIR 環境変数および引数で出力先を上書き可能。既存ハンドラをクリアして二重設定を防止。
      - ディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
    - utils/process_priority.py:
      - set_process_priority(level) を実装（Windows と POSIX を吸収し psutil を利用）。
      - set_cpu_affinity(cpu_count) を実装（指定された最初の N コアに固定）。権限不足や非対応環境は警告でスキップ。
  - ポートフォリオ構築ライブラリ
    - portfolio/portfolio_builder.py:
      - select_candidates: スコア降順、同点は signal_rank 昇順で上位 N を選択。
      - calc_equal_weights / calc_score_weights: 等金額配分およびスコア比率配分（スコア全て 0 の場合は等配分にフォールバック）。
    - portfolio/risk_adjustment.py:
      - apply_sector_cap: セクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外（未知セクター("unknown") は除外しない）。
      - calc_regime_multiplier: market レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバック）。
    - portfolio/position_sizing.py:
      - calc_position_sizes: risk_based / equal / score の allocation_method を実装。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）に応じたスケーリングと端数再配分ロジックを実装。
      - cost_buffer を考慮した保守的コスト見積り。
      - 価格欠損時のスキップやデバッグログを出力。
  - 研究・ツール
    - research/factor_research.py: ファクター計算モジュール（Momentum, Value, Volatility, Liquidity）の基礎を実装。DuckDB 接続を受け prices_daily / raw_financials テーブルを参照する設計（ファイルは一部未完）。
    - tools/paper_verification_report.py:
      - ペーパートレード用 SQLite DB を解析し、稼働率、注文成功率、送信率、レイテンシ（P95 など）を計算してレポートを生成。
      - パス/フェイル閾値を定義（例: 稼働率 >= 99%、P95 <= 200 ms など）。--from/--to/--db オプションをサポート。
      - P95 計算、各種クエリで存在しないテーブルや OperationalError を捕捉して N/A を扱う。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- 初期リリースのため該当なし。

Security
- .env ファイルの取り扱いに関する注意喚起を config_setup に記載（.env を Git にコミットしないことを明示）。
- 環境変数にシークレットを扱う際は config_setup のシークレットマスク表示により誤表示を防止。

Notes / Known issues
- research/factor_research.py はファイル末尾が途中で切れている（calc_momentum の実装開始はあるが完全ではない）。ファクター計算の完成は今後の作業。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に 0.0（欠損） がある場合、エクスポージャーが過少見積となる可能性がある点を TODO コメントで指摘。将来的に前日終値や取得原価へのフォールバックが必要。
- logging_setup でログディレクトリ作成に失敗した場合、ファイル出力はスキップされるが stdout ログは有効。ファイル出力失敗の詳細は起動ログに警告が出る。
- process_priority/set_cpu_affinity は権限不足やプラットフォーム非対応時に機能しない可能性がある（警告を出してスキップする）。
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用する」設計になっているため、Paper Trading 用の監視分離が必要な場合は運用上の注意が必要。

Usage highlights
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行スクリプト:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
- Paper トレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

開発者向けメモ
- 自動 .env 読み込みはプロジェクトルート判定に依存する（.git / pyproject.toml）。パッケージ化・配布後も動作するように __file__ を起点に探索します。
- 環境変数の必須チェックは Settings プロパティで ValueError を投げる仕様のため、起動前に validate_config を実行することを推奨します。
- 各モジュールは可能な限り副作用を避け、純粋関数（ポートフォリオ/サイズ計算等）として実装されています。ユニットテストによる検証が容易です。

今後の予定
- factor_research の完成（Momentum 等の完全実装）。
- ExecutionEngine / BrokerClient 実装の詳細（本番接続・モック挙動の網羅的テスト）。
- 価格欠損時のフォールバック戦略追加（前日終値等）。
- 単体テスト・CI の整備とドキュメント（README、運用手順）の充実。