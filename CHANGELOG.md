CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained in Japanese.

Unreleased
----------
- なし

0.1.0 - 2026-04-17
------------------
Added
- 初回リリース: KabuSys 自動売買フレームワークの基盤機能を追加。
- 実行エントリポイント:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV による paper_trading 切替をサポートし、
    paper_trading 時は専用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）と MockBrokerClient を使用して本番 DB と分離。
    - エンジンはスレッドで実行し、 data/stop_requested.flag の存在で安全に停止可能。
    - 起動時に実行用 PID ファイルを書き込む仕組み（pid_file）を採用。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定（デフォルト: 60秒）。不正値時はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - data/stop_requested.flag による停止検知を実装。
- 設定管理:
  - config.py: 環境変数 / .env 自動読み込み機能を追加 (.env, .env.local)。
    - プロジェクトルートを .git または pyproject.toml から探索して自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパースは export 形式、クォート、インラインコメント等に対応。
    - Settings クラスを導入し、各種設定値取得（J-Quants / kabuAPI / DB パス / PID ファイル /閾値など）とバリデーションを提供。
    - PAPER_FILL_MODE（instant/partial/never/reject）等の検証を実装。
- 設定関連 CLI:
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。項目定義、既存 .env 読み込み、確認・保存フローを提供。
  - validate_config.py: 起動前設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスや config/*.yaml の存在・パースチェック、
    本番向けガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START に関する警告）を実装。--strict オプションで警告も FAIL 扱いに可能。
- ポートフォリオ構築モジュール (純粋関数群、DB 参照なし):
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順に選定（同点は signal_rank でブレーク）。
    - calc_equal_weights, calc_score_weights: 等金額およびスコア正規化重みを算出。全スコア 0 の場合は等分にフォールバックして警告。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限(max_sector_pct)をチェックし、上限超過セクターの新規候補を除外。
      - sell_codes により当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム(bull/neutral/bear)に応じた投下資金乗数を返す（未知レジームは警告のうえ 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に基づき各銘柄の発注株数を算出。
      - lot_size（単元）に合わせた丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、
        cost_buffer を考慮した保守的なコスト見積りと残余配分ロジックを実装。
- 研究／ファクター:
  - research/factor_research.py:
    - DuckDB を用いたファクター計算モジュールを追加（prices_daily / raw_financials テーブル想定）。
    - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比）等の算出関数を実装。
    - 欠損データやウィンドウ不足時の取り扱いに配慮。
- ユーティリティ:
  - utils/process_priority.py:
    - クロスプラットフォームのプロセス優先度設定ユーティリティを追加。
    - Windows（psutil の優先度定数）／POSIX (nice) を吸収し、失敗時は警告でスキップ。
    - set_cpu_affinity により最初の N コアにピン留め可能（未指定時は何もしない）。
- モニタリング DB 初期化:
  - monitoring.monitoring_db.init_monitoring_db を用いた監視テーブル初期化（冪等）を run_execution/run_monitoring で実行。
- ツール:
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成スクリプトを追加。指定期間の稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数等を算出し PASS/FAIL 判定を出力。
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。閾値はソース内で定義（稼働率 >=99% 等）。

Changed
- なし（初回リリースのため新規導入が中心）。

Fixed
- なし（初回リリース。各モジュールにて実行時の例外をログで安全に処理する実装あり）。

Security
- 環境変数管理に関する留意:
  - .env は生成時にコメントで「絶対に Git にコミットしないこと」と明記。
  - config_setup の対話入力でシークレット項目は表示をマスクして扱う。

Notes / Implementation details (概要・運用上の注意)
- run_monitoring は MONITOR_POLL_INTERVAL に不正な値が設定された場合、警告を出しデフォルト（60秒）に戻る。
- run_monitoring は監視用 DB に対し「環境にかかわらず本番 sqlite_path を使用」する仕様のため、監視専用 DB 運用を行う場合は設定変更が必要。
- run_execution は paper_trading 時に本番 DB を触らないよう paper_sqlite_path を優先して使用する。
- ファクター計算・分析は DuckDB を想定し、prices_daily / raw_financials 等のテーブルが存在することが前提。
- process_priority / set_cpu_affinity は権限不足等で失敗する可能性があり、その場合はログで警告して処理を継続する設計。

今後の課題（想定）
- 銘柄別 lot_size のサポート（現在は全銘柄共通の lot_size）。
- price 欠損時のフォールバック（前日終値や取得原価など）を position_sizing / risk_adjustment に導入。
- monitoring と execution の DB 分離や監視メトリクスの拡張、アラート送信（LINE）連携の実稼働確認。
- factor_research の追加ファクター実装やベクトル化・並列化による高速化。

デベロッパーメモ
- パッケージバージョン: __version__ = "0.1.0"
- 主要 CLI:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

-- End of CHANGELOG --