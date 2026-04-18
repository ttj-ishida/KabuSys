CHANGELOG
=========

すべての重要な変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に従って記載しています。

[Unreleased]
------------
- （現時点のコードベースは初期リリース相当の内容を含むため、未リリースの変更はありません）

[0.1.0] - 2026-04-18
-------------------
Added
- 基本アプリケーション初期実装を追加。
  - パッケージ情報:
    - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
  - 実行スクリプト:
    - run_execution.py
      - ExecutionEngine を起動する CLI スクリプトを提供。
      - KABUSYS_ENV による動作分岐: paper_trading 時は専用の Paper Trading DB（デフォルト data/paper_trading.db）を使用し、MockBrokerClient（BrokerClientFactory 経由）を用いることで本番 DB と分離。
      - プロセス優先度を "high" に設定（set_process_priority を最初に呼ぶ）。
      - 監視用テーブルが存在することを保つため init_monitoring_db を実行。
      - デフォルトのリスク管理パラメータを設定して RiskManager を初期化（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
      - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag を検知したら停止する仕組みを実装。PID ファイル path を利用。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを提供。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
      - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
      - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
  - 設定管理:
    - config.py
      - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
      - .env/.env.local の読み込み順と保護（OS 環境変数を上書きしない）を実装。
      - 複数の設定プロパティを提供: J-Quants, kabu API, LINE 通知、DuckDB/SQLite パス、Paper Trading の設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）、監視閾値等。
      - 環境値の検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL の有効値チェック）。
    - config_setup.py
      - .env を対話式に作成・更新するウィザード CLI を提供。デフォルト値、選択肢、シークレット入力に対応し、ファイル書き出しを行う。
    - validate_config.py
      - 起動前に .env と config/*.yaml の妥当性を検証する CLI を提供。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パス親ディレクトリ検査、config YAML の存在／パース検証（PyYAML が無い場合はスキップ）、本番環境向けの追加警告等を行う。
      - --strict オプションで警告を fail 扱いにできる。
  - Utilities:
    - utils/logging_setup.py
      - 全アプリケーションで統一して使えるログ設定ユーティリティを提供。
      - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を設定。ログディレクトリ作成に失敗した場合のフォールバックを実装。
      - LOG_LEVEL / LOG_DIR / 引数での上書きに対応。
    - utils/process_priority.py
      - Windows/Linux/macOS 向けにプロセス優先度設定（nice / Windows priority）と CPU affinity 設定関数を提供。アクセス権限エラー等は警告としてスキップ。
  - ポートフォリオ構築（純関数群: DB 非依存）:
    - portfolio/portfolio_builder.py
      - BUY シグナルから候補選定（score 降順、signal_rank でタイブレーク）。
      - 等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights、全スコア 0 の場合は等分へフォールバック）。
    - portfolio/risk_adjustment.py
      - セクター集中制限 apply_sector_cap（既存保有を考慮して、セクター上限を超える候補は除外）。
      - レジーム乗数 calc_regime_multiplier（bull/neutral/bear -> 1.0/0.7/0.3、未知値は 1.0 にフォールバック）。
    - portfolio/position_sizing.py
      - position サイズ計算（allocation_method: risk_based / equal / score）。
      - 単位株（lot_size）で丸め、per-position 上限・aggregate cap（available_cash）を考慮したスケーリング、cost_buffer を考慮した保守的見積り、残余キャッシュを利用した追加配分ロジックを実装。
  - 分析・検証ツール:
    - tools/paper_verification_report.py
      - Paper Trading 用の検証レポート生成 CLI を追加。
      - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で上書き可）。
      - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計してレポートを標準出力へ表示。閾値（稼働率 99%, 成功率 90%, 送信率 95%, P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
  - 研究用モジュール（骨格実装）:
    - research/factor_research.py
      - DuckDB の prices_daily / raw_financials を使ったファクター計算の設計と一部実装（モメンタム、MA、ATR、出来高などの指標を想定）。（実装は継続中）

Changed
- n/a（初期リリースのため、変更履歴は追加項目としてまとめています）

Fixed
- n/a（初期リリース）

Security
- 環境変数ファイル (.env) は明示的に Git にコミットしないよう注意書きを含めて生成するなど、シークレット管理に関する注意をドキュメント化。

Notes / Implementation details
- run_execution/run_monitoring はプロセスの停止を data/stop_requested.flag の存在で制御する設計です。運用ではこのフラグ生成/削除の運用ルールに注意してください。
- config モジュールの .env 自動読み込みはプロジェクトルート検出に依存するため、配布後に CWD で動かすケースなどでも期待通りに動作するよう設計されています。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 各種ファイルハンドリングや OS 固有の操作（プロセス優先度、ファイル作成等）は失敗時に警告を出して安全にフォールバックするように実装されています（運用環境での権限・パス設定に配慮）。
- Paper Trading と Live の DB は分離しているため、ペーパートレードでの検証が本番 DB に影響を与えない設計です。

今後の予定（例）
- research/factor_research の完全実装（各ファクターの SQL 実装と出力フォーマットの整備）
- ExecutionEngine / BrokerClient の統合テスト補強、エッジケース処理の改善
- ロギング/メトリクスのさらに詳細な監視（Prometheus などとの連携検討）
- position_sizing の銘柄別 lot_size 対応、手数料・スリッページモデルの改善

以上。必要であればリリースノートをバージョン別に分割したり、各モジュールごとにより詳細な変更点（関数レベル）を追記します。どの形式で出力するか（短い要約版／詳細版）をご指定ください。