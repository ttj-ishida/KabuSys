CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に準拠して記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

Unreleased
----------

- 進行中 / 既知の事項
  - research.calc_momentum の実装が途中（ファイル末尾で切れている）ため、ファクター計算モジュールの一部機能が未完です。今後のリリースで完了予定。
  - 今後の改善予定: 銘柄ごとの lot_size をマスタから読み込む設計拡張（position_sizing の TODO）。

[0.1.0] - 2026-04-23
--------------------

Added
- 初期リリース。以下の主要機能・モジュールを追加。
  - 実行系 / 監視系の起動スクリプト
    - run_execution.py
      - ExecutionEngine を起動するエントリポイント。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
      - BrokerClientFactory を利用して実運用/モックを切り替え。
      - エンジンは別スレッドで実行し、data/execution.pid（デフォルト）へ PID 書き込み・停止フラグ（data/stop_requested.flag）で安全停止。
      - RiskManager のデフォルト設定を導入（max_position_pct、max_utilization、rate_limit など）。
    - run_monitoring.py
      - SystemMonitor のポーリングループを提供。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視用 DB は環境に依らず本番 sqlite_path を使用して監視データの一貫性を保つ。
      - 停止フラグ（data/stop_requested.flag）の検知でループを終了。
      - 起動時にプロセス優先度を "high" に設定し、例外発生時はロギングして次ポーリングを継続。

  - 設定管理・ウィザード・検証
    - config.py
      - 環境変数読み込みと Settings クラスを提供。
      - プロジェクトルート検出（.git または pyproject.toml 基準）により .env 自動読み込み（.env、.env.local）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env パースは export 形式やクォート、インラインコメントを考慮した堅牢な実装。
      - 各種設定プロパティ（duckdb/sqlite パス、paper_trading 用パス、閾値、env 判定等）を提供。
    - config_setup.py
      - 対話式の .env 作成・更新ウィザードを提供（secret 項目のマスク表示、既存 .env の取り込み、自動書き出し）。
    - validate_config.py
      - 起動前チェック CLI。
      - 必須環境変数や KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML がインストールされている場合）を検証。
      - --strict オプションで警告を FAIL 扱いにできる。

  - ポートフォリオ構築モジュール（純粋関数）
    - portfolio/portfolio_builder.py
      - 候補選定 select_candidates（スコア降順、signal_rank を tie-break）を実装。
      - 等金額配分 calc_equal_weights／スコア加重配分 calc_score_weights（全銘柄スコアが 0 の場合は等配分へフォールバック）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap：既存保有を元にセクター集中を判定し、新規候補を除外。
      - calc_regime_multiplier：市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームは警告の上 1.0 にフォールバック。
    - portfolio/position_sizing.py
      - calc_position_sizes：allocation_method（risk_based / equal / score）に基づく発注株数決定ロジックを実装。
      - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash）を考慮。資金超過時はスケーリングし、残余キャッシュで端数を lot 単位で配分するアルゴリズムを実装。
      - cost_buffer によりスリッページ/手数料を保守的に見積もる。

  - ユーティリティ
    - utils/logging_setup.py
      - 全起動スクリプト共通のログ設定ユーティリティを追加。
      - stdout へ StreamHandler、ログファイルへ TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
      - LOG_LEVEL / LOG_DIR の優先解決、既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバック対応を実装。
    - utils/process_priority.py
      - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定する関数を追加。
      - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。権限不足等を許容する警告処理あり。

  - 実用ツール
    - tools/paper_verification_report.py
      - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）を読み、期間指定でレポートを生成。
      - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を計算して PASS/FAIL を判定（デフォルト閾値をコード内に定義）。
      - P95 計算、NULL 値ハンドリング、SQL の期間フィルタリングを実装。

  - パッケージメタ
    - src/kabusys/__init__.py に version を追加（0.1.0）。

Changed
- 初期リリースのため過去バージョンからの変更点はなし。

Fixed
- 初期リリースのため過去バージョンからの修正点はなし。

Security
- シークレット情報（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）は Settings を通して必須チェックを行い、config_setup の出力でも .env に平文で保存する旨の注意を明示（.env を Git にコミットしないよう注意喚起）。

Notes / Usage highlights
- ポイント
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔を環境変数で上書き可能（正の整数のみ。有効でない場合はデフォルト 60 秒）。
  - KABUSYS_ENV: "development" / "paper_trading" / "live" のいずれか。paper_trading 時は発注は仮想（Mock）で、本番 DB と分離される。
  - .env 自動読み込み: プロジェクトルートが特定できれば .env / .env.local を自動でロード。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
  - ロギング: デフォルトは logs/ 以下に日次ローテーションで保存。ログディレクトリ作成に失敗してもコンソール出力は維持。
  - process_priority: 権限不足や未対応 OS の場合は警告を出してスキップする安全設計。
  - Paper Trading レポート: デフォルト閾値（稼働率 99%、fill_rate 90% など）に基づき PASS/FAIL を判定。DB が存在しない場合はエラー表示。

Acknowledgements
- このリリースは初期設計に基づく実装をまとめたもので、今後のリファクタリングやテスト拡充、未実装ファクターの完了（research モジュール）を予定しています。