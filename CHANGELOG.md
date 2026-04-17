KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  

Unreleased
---------

- なし

[0.1.0] - 2026-04-17
-------------------

Added
- 基本パッケージ初回リリース
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として公開。

- 設定・環境変数関連
  - Settings クラスを追加（kabusys.config）
    - .env 自動ロード機能（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
    - OS 環境変数を保護する読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - 必須/任意設定のプロパティ（J-Quants / kabu API / DB パス / LINE / 監視閾値等）。
    - env 値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
    - .env の読み取り/上書き、シークレット入力のマスク表示、出力フォーマットを提供。
    - CLI で実行可能: python -m kabusys.config_setup

- 設定検証ツール
  - 設定検証 CLI（kabusys.validate_config）
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DBパスや config/*.yaml の存在チェック（PyYAML があればパース検証実行）。
    - 本番環境向けガード（LINE 未設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を FAIL 扱いにできる。
    - CLI: python -m kabusys.validate_config

- 実行エンジン / 発注
  - Execution 起動スクリプト（kabusys.run_execution）
    - プロセス起動時に優先度を "high" に設定（set_process_priority を利用）。
    - 環境に応じて DB を分離: KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は Mock クライアント想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせ、ExecutionEngine を起動。別スレッドで run_session を実行し、停止フラグファイルを監視して安全に停止する。
    - RiskManager にデフォルト構成を付与（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。initial_portfolio_value を broker.get_available_cash() で初期化。

- 監視
  - SystemMonitor 起動スクリプト（kabusys.run_monitoring）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - Monitoring は起動環境にかかわらず本番 sqlite_path を使用（監視専用 DB 初期化を保証）。
    - 停止フラグファイル（data/stop_requested.flag）による安全停止。
    - 例外発生時もループ継続（ログ出力して次ポーリングまで待機）。

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db を利用して監視用テーブルの存在を保証（冪等性を考慮）。

- ポートフォリオ構築（pure function 群）
  - kabusys.portfolio
    - portfolio_builder
      - select_candidates: スコア降順で上位 N を選定（同点は signal_rank でブレーク）。
      - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合はフォールバック）。
    - risk_adjustment
      - apply_sector_cap: セクター集中上限をチェックし、超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear をマップ、未知のレジームはフォールバックで 1.0）。
    - position_sizing
      - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算、単元株丸め、1銘柄上限・aggregate 上限の考慮、コストバッファの反映、スケールダウンと端数処理を実装。

- 研究（ファクター計算）
  - kabusys.research.factor_research
    - DuckDB を用いたファクター計算モジュールを追加（prices_daily / raw_financials を参照）。
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR20 等）、流動性指標等の計算ロジックを実装（営業日ウィンドウを想定）。
    - データ不足時に None を返す設計。

- ユーティリティ
  - process_priority（kabusys.utils.process_priority）
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度を設定。失敗時は警告ログでスキップ。
    - set_cpu_affinity(cpu_count): 指定された最初 N コアにプロセスをピン留め。権限不足や未対応環境では警告でスキップ。

- ツール
  - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
    - SQLite（paper_trading DB）から system_status / trade_logs / risk_logs を集計し、稼働率・注文成功率・送信率・レイテンシ等を算出して CLI レポートを出力。
    - パス/フェイル基準（稼働率 >=99%、成立率>=90%、送信率>=95%、P95<=200ms）を実装。
    - 日付フィルタ（--from, --to）および --db オプションをサポート。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- なし（初回リリース）

Notes / Implementation details
- .env パーサはシングル/ダブルクォート、export プレフィックス、インラインコメントなどを考慮した堅牢な実装になっており、読み込み時に既存 OS 環境変数を保護する仕組みを採用。
- DB は SQLite（監視・paper_trading 用）と DuckDB（分析用）を併用する設計。起動スクリプトは適切にコネクションをクローズする。
- 実運用（live）においては validate_config の警告や KILL_SWITCH 周りの設定を特に確認することを推奨。

--- 

今後の計画（例）
- ExecutionEngine / BrokerClient の具体実装と統合テストの追加
- 戦略（signal generator）モジュールの追加と end-to-end テスト
- 単体テスト・CI の整備、PyPI 配布準備

（この CHANGELOG はコードの内容から推測して作成しています。実際のリリースノートとは差異がある可能性があります。）