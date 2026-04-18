CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付は現時点（2026-04-18）での推定リリース日を使用しています。

フォーマット:
- Added: 新規機能
- Changed: 仕様変更 / 既存機能の改善
- Fixed: バグ修正 / 回避策
- Notes: 実装上の注意や既知の制約

[Unreleased]
------------

（なし）

[0.1.0] - 2026-04-18
-------------------

Added
- 全体
  - 初期リリースとして基本的な自動売買/検証フレームワークを追加。
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

- 実行エントリ / デーモン
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて本番 DB とペーパートレード用 DB を分離（settings.paper_sqlite_path）。
    - BrokerClientFactory 経由でブローカークライアントを生成し、ExecutionEngine をスレッドで起動。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル管理 (_EXECUTION_PID) による安全停止をサポート。
    - RiskManager、OrderManager、Reconciler 等の組み立てロジックを追加。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず監視用 sqlite（settings.sqlite_path）を使用する実装。

- 設定関連 CLI / ユーティリティ
  - config.py: Settings クラスを追加。
    - .env 自動ロード（.env / .env.local）機能、環境変数のバリデーション、各種パス/フラグ/閾値プロパティを提供。
    - PAPER_FILL_MODE のバリデーションや paper_sqlite_path 等のプロパティを実装。
    - プロジェクトルート検出ロジック（.git / pyproject.toml を基準）により CWD に依存しない自動読み込みを実現。
    - .env の行パース機能（export プレフィックス、クォート / エスケープ、インラインコメント対応）。
  - config_setup.py: .env 初期作成・更新用の対話式ウィザードを追加。
    - 対話で主要な環境変数を入力、.env テンプレートを書き出す機能を提供。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在とパース検証（PyYAML が無ければスキップ）を実行。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス制御
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
    - stdout に StreamHandler、ファイルに TimedRotatingFileHandler（日次ローテーション、30日分保持）を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows/Linux/Mac 等を吸収（psutil ベース）、set_process_priority / set_cpu_affinity を提供。
    - 実行スクリプトの起動時に優先度を "high" に設定する流れを採用（run_* スクリプト内）。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で候補を選択。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分（スコアが全て 0 の場合はフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存ポジションを考慮、"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知のレジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method に応じた発注株数算出（"risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap、cost_buffer を考慮したスケーリングロジックを実装。
    - 利用可能現金を超える場合のスケールダウンと残差処理（lot 単位で再配分）を採用。

- 解析 / 検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite DB を集計してレポートを生成する CLI を追加。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ統計（avg/max/P95）を算出。
    - PASS/FAIL 判定基準（閾値）を定義（稼働率、成功率、送信率、P95 レイテンシ）。

- research
  - research/factor_research.py（骨組み）:
    - ファクター計算モジュールの骨格を追加（Momentum, Value, Volatility, Liquidity を想定）。
    - DuckDB 接続を前提に prices_daily / raw_financials を参照する方針と定数を定義。
    - モメンタム計算に必要なパラメータや補助関数が用意されている（実装は続く）。

Changed
- 設計/挙動
  - データベース運用ポリシー:
    - 監視（monitoring）は環境にかかわらず監視用の sqlite_path を使用し、本番/ペーパーを分離する方針を明確化（run_monitoring.py）。
    - run_execution.py は KABUSYS_ENV=paper_trading 時に専用の PAPER_TRADING_SQLITE_PATH を使用し、発注ログ等を本番 DB から完全分離。
  - ログ出力:
    - stdout を標準出力として使用する（cron / scheduler のログリダイレクトを想定）点を明示（logging_setup）。
  - .env 自動ロード:
    - プロジェクトルート検出によりパッケージ配布後も .env 自動ロードが安定して動作するよう改善（config._find_project_root）。

Fixed
- 例外処理 / ロバストネス
  - run_monitoring.py と run_execution.py において停止フラグ検知や KeyboardInterrupt を考慮した安全な終了処理を実装。
  - logging_setup: ログディレクトリ作成に失敗した場合でもコンソールログだけで継続できるフォールバックを実装。
  - process_priority と set_cpu_affinity は権限不足や未サポート環境での例外を捕捉して警告ログを出すよう改善。

Notes
- 未実装 / 要注意点
  - research/factor_research.py はファイル終端が途中で切れており、モメンタム計算の実装が未完の可能性あり。実運用前に残りの算出ロジックを実装・テストする必要があります。
  - position_sizing: price が欠損（0.0）の場合にエクスポージャーが過少評価される点をコメントで指摘しており、将来的にフォールバック価格（前日終値等）の導入を検討する必要あり。
  - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。CI/テスト環境ではこのフラグを利用することを推奨。
  - PAPER_FILL_MODE やその他環境変数は厳密な値チェックを行うため、.env 設定時に誤った値を与えると起動時に例外が発生します。validate_config や config_setup での検証を推奨。

Acknowledgements / Implementation notes
- DuckDB と sqlite3 を組み合わせた設計により、高速分析（DuckDB）と軽量なトランザクション/履歴（SQLite）を使い分けるアーキテクチャを採用。
- psutil を利用して OS 毎の差異を吸収しているため、psutil のインストールと適切な権限が運用環境に必要です。
- YAML の検証は PyYAML が存在する環境でのみ有効になります（validate_config）。

--- 

この CHANGELOG はソースコードからの推測に基づいて作成しています。実際のリリースノート作成時は実運用の変更履歴やコミットログを参照して調整してください。