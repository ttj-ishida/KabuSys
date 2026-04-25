CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記録しています。
<https://keepachangelog.com/ja/1.0.0/>

Unreleased
----------
- （現在のブランチに未リリースの変更はありません）

[0.1.0] - 2026-04-25
-------------------

Added
-----
- 基本リリース: KabuSys v0.1.0
  - 日本株自動売買システムの初期実装一式を追加。

- 環境設定 / ロード
  - .env 自動ロード機能を実装（プロジェクトルートは .git / pyproject.toml を基準に探索）。
  - .env のパースロジックを強化（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードの無効化が可能。

- 設定管理 API (kabusys.config)
  - Settings クラスを提供し、環境変数からアプリケーション設定を取得する一元化インターフェースを追加。
  - 各種設定プロパティを提供（J-Quants トークン、kabu API、DB パス、Paper Trading 設定、監視閾値、実行環境フラグ等）。
  - PAPER_FILL_MODE の妥当性チェック（"instant" | "partial" | "never" | "reject"）を実装。
  - KABUSYS_ENV 値検証（development / paper_trading / live）とログレベル検証を実装。

- 設定ウィザード CLI (kabusys.config_setup)
  - 対話式ウィザードで .env を作成 / 更新する CLI を追加。
  - 項目定義（実行環境、API トークン、DB パス、ログレベル、Kill Switch など）を含む。
  - 既存 .env の読み込み / 値のマスク表示 / 保存確認をサポート。

- 設定検証 CLI (kabusys.validate_config)
  - 起動前チェック用 CLI を提供。必須環境変数の未設定検出、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パス親ディレクトリの存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証を実行。
  - --strict モードを実装（警告を FAIL として扱う）。

- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper 用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカクライアント生成、OrderRepository, OrderManager, RiskManager, Reconciler の組み立てを行う。
    - デフォルトでプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）による安全停止をサポート。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - Monitoring は環境に関わらず本番 sqlite_path を使用して監視テーブルを初期化。

- ロギングユーティリティ (kabusys.utils.logging_setup)
  - 統一ログ設定関数 setup_logging を追加。
    - stdout (StreamHandler) 出力と、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - 既にハンドラが設定されている場合はクリアして再設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
    - ログレベル / ログディレクトリの解決順を明記。

- プロセス優先度 / CPU affinity ユーティリティ (kabusys.utils.process_priority)
  - set_process_priority(level) を実装（Windows/Linux/macOS の差分を吸収）。
    - サポートレベル: "high" / "normal" / "low"。アクセス権限不足などで失敗した場合は警告を出力してスキップ。
  - set_cpu_affinity(cpu_count) を提供（指定した最初の N コアにプロセスを固定）。未対応環境または権限不足は警告でスキップ。

- ポートフォリオ構築モジュール (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: score 降順、同点時は signal_rank 昇順のタイブレークで候補選定。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分（全スコアが 0 の場合は等金額にフォールバックし WARNING を出力）。
  - risk_adjustment:
    - apply_sector_cap: セクター別の既存保有比率が閾値を超える場合、新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告後 1.0 でフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じて発注株数を算出。lot_size（単元）、max_position_pct、max_utilization、risk_pct、stop_loss_pct、cost_buffer 等のパラメータをサポート。aggregate cap（総投資額が available_cash を超えた場合のスケーリング）を実装。端数処理は lot_size 単位で行い、残余配分ロジックを持つ。

- Paper Trading 検証ツール (kabusys.tools.paper_verification_report)
  - ペーパートレーディング用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から各種指標を集計し、検証レポートを標準出力に出力する CLI を提供。
  - レポート指標:
    - 稼働率（uptime_pct）、総ポーリング数、エラー数
    - 注文成功率（Filled / Created）、送信率（Sent / Created）
    - リスク却下数（risk_logs）
    - API レイテンシ（avg / max / P95）
  - デフォルトしきい値:
    - 稼働率 >= 99.0%
    - 注文成功率 >= 90.0%
    - 送信率 >= 95.0%
    - P95 レイテンシ <= 200 ms
  - P95 計算実装および --from / --to / --db オプションをサポート。

- Research / ファクター計算（着手）
  - research.factor_research モジュールにモメンタム等の計算フローを設計・一部実装（定数や関数スケルトンを追加）。DuckDB を用いて prices_daily / raw_financials を参照して計算する方針。

Changed
-------
- なし（初回リリース）

Fixed
-----
- なし（初回リリース）

Known issues / Notes
--------------------
- research.factor_research は実装途中の箇所が存在します（ソース末尾が途中で切れている等）。完全なファクター計算ロジックは継続実装が必要です。
- apply_sector_cap 内の価格欠損（price == 0.0）の扱いについて注記あり（現在は 0.0 として扱うためエクスポージャーが過少見積りされる可能性がある）。将来的に前日終値などのフォールバックを導入することを想定。
- process_priority / cpu_affinity の設定は権限やプラットフォーム依存で失敗する可能性があるため、失敗時は警告を出してスキップする設計。
- .env 自動ロードはプロジェクトルートが特定できない場合はスキップする。配布後の利用やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で制御可能。
- run_execution / run_monitoring は停止フラグ（data/stop_requested.flag）や pid ファイルを利用した単純な制御を行う。運用での細かい停止・再起動ポリシーはドキュメント化・運用ルール整備が必要。

Security
--------
- 現状、シークレット（トークン・パスワード）は .env にプレーンで保存される想定。公開リポジトリに .env をコミットしない運用ルールを README 等で周知する必要があります。

Appendix
--------
- 主要な環境変数の一覧とデフォルト
  - KABUSYS_ENV: development (development|paper_trading|live)
  - JQUANTS_REFRESH_TOKEN: 必須
  - KABU_API_PASSWORD: 必須
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO
  - MONITOR_POLL_INTERVAL: 60 (秒)
  - PAPER_FILL_MODE: instant (instant|partial|never|reject)

もし詳細なリリースノート（ファイル毎の変更点や設計上の考慮点）を含めた別個のセクションをご希望でしたら、どのレベルの詳細（開発者向け/運用向けなど）を出力するか教えてください。