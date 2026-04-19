CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、本 CHANGELOG はリポジトリ内のソースコードから機能や挙動を推測して作成しています。

Unreleased
---------

- （今後の変更点をここに記載します）

0.1.0 — 2026-04-19
------------------

Added
- 基本アプリケーション構成および CLI を実装
  - Settings クラス（kabusys.config）を通じた環境変数/ .env 読み込み・検証機能を提供。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）。
    - .env と .env.local の読み込みルール（OS 環境変数優先、.env.local は上書き可能）。
    - 必須値取得ヘルパー `_require()` を提供し、未設定時は明示的なエラーを投げる。
    - 各種設定プロパティ（DB パス、KABUSYS_ENV、LOG_LEVEL、Paper Trading 関連設定等）を定義。
    - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）。

- 設定操作用ユーティリティ
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - 複数の設定項目（環境、API トークン、DB パス、ログレベル、Kill Switch など）を対話で入力可能。
    - シークレット項目は表示マスク、確認プロンプト付きで .env に保存。

  - validate_config.py: 起動前の設定検証ツールを追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガード。
    - --strict オプションで警告も失敗扱いにできる。

- 実行系 / 監視系スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory（ブローカークライアントの抽象化）を使用し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と実行 PID 管理（data/execution.pid）に対応。停止フラグ検知で安全に停止。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義し、初期ポートフォリオ値に broker.get_available_cash() を利用。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視情報を記録（設計上の注記）。
    - 停止フラグ（data/stop_requested.flag）の検知で監視ループを終了。
    - 起動時にプロセス優先度を "high" に設定。

- ロギング / プロセス管理ユーティリティ
  - utils.logging_setup: 統一ログ設定ユーティリティを追加。
    - StreamHandler（標準出力 stdout）と TimedRotatingFileHandler（日次・30世代保持）をルートロガーへ登録。
    - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベルとログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。

  - utils.process_priority: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX(Linux, macOS, FreeBSD) の差異を吸収して set_process_priority(level="high"|"normal"|"low") を提供。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアにピン留め可能（未対応環境は警告でスキップ）。
    - 権限不足や未対応機能に対しては警告ログでフェイルセーフ。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定と重み計算を提供。
    - select_candidates: スコア降順（同点は signal_rank 小さい方優先）で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装（スコア全0 の場合は等配分へフォールバックし警告）。

  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中を抑制するフィルタ（既存ポジションのセクター比率が閾値を超えた場合、同セクター候補を除外）。"unknown" セクターは上限チェック対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未定義のレジームは 1.0 にフォールバックし警告）。

  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づき発注株数を計算。
    - 単元株（lot_size）丸め、per-position 上限 / aggregate cap（available_cash）スケーリング、cost_buffer（手数料・スリッページ見積り）を考慮した安全な割付ロジックを実装。
    - risk_based モードでは risk_pct / stop_loss_pct に基づくポジションサイズ決定。

- Paper Trading 検証ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite ログを解析して検証レポートを生成するスクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数など。
    - 判定基準（デフォルト）を定義:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日時フィルタ（--from / --to）、DB パス指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。
    - データ欠損・テーブル未存在時のフォールバック処理あり。

- 研究用ファクタ計算（部分実装）
  - research.factor_research: DuckDB 接続を受け取り prices_daily / raw_financials を用いてモメンタム等のファクターを計算する基盤を追加（モジュール設計・定数・calc_momentum の骨格あり、実装途中ファイルあり）。

Documentation
- パッケージメタ情報: __version__ を 0.1.0 に設定。
- 各スクリプト・モジュールにモジュール docstring と使用例を追加して使い方を明確化。

Security
- シークレット（API トークン等）の .env への取り扱いを注意喚起（config_setup のヘッダに .env を Git にコミットしないよう明記）。

Notes / Migration
- .env 自動ロードはデフォルトで有効。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- run_monitoring は「監視専用 DB」を環境にかかわらず sqlite_path（本番想定）へ書き込む設計のため、本番/開発で分離したい場合は SQLITE_PATH を適切に設定すること。
- Paper Trading を本番と完全分離するため、KABUSYS_ENV=paper_trading 時は paper_sqlite_path が使用される。
- LOG_DIR 作成に失敗した場合はファイルロギングが無効化され、標準出力のみでログが出力される点に注意。

Deprecated
- なし

Removed
- なし

Fixed
- （初回リリースのため該当なし）

Security
- なし

----- 

この CHANGELOG はコードの実装内容を元に推測して作成しています。実際のリリースノートとして公開する際は、リリース日やリリース対象バージョン、影響範囲（既知の制約や移行手順）を合わせてご確認ください。