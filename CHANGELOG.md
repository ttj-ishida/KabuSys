CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従って記載しています。  
セマンティックバージョニングに準拠します。

Unreleased
----------

（現在のスナップショットに基づく初回リリースを作成しました。今後の変更はここに記載してください。）

0.1.0 - 2026-04-18
------------------

Added
- 全体
  - 初期リリース。パッケージバージョンを __version__ = "0.1.0" に設定。
- 実行 / 常駐プロセス
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用して本番 DB と分離する設計を実装（Mock ブローカークライアント利用を想定）。
    - プロセス起動時にプロセス優先度を "high" に設定（set_process_priority を呼び出し）。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応し、安全に停止できるループを実装。
    - BrokerClientFactory を使用してブローカークライアントを抽象化。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず「本番」用 sqlite_path を使用する設計（監視データは本番 DB を想定）。
    - 停止フラグ（data/stop_requested.flag）検知で graceful shutdown。
- 設定 / 環境変数
  - config.py: Settings クラスを実装。
    - .env 自動読み込み機能を実装（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env / .env.local の読み込み順序（OS 環境 > .env.local > .env）と保護（OS 環境変数を上書きしない）に対応。
    - 環境変数パーサで export 形式、クォート（シングル/ダブル）やバックスラッシュエスケープ、インラインコメントの扱いに対応。
    - 各種プロパティを提供（J-Quants / kabuAPI / LINE / DB パス / 監視しきい値 / 環境種別判定 等）。
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）や KABUSYS_ENV / LOG_LEVEL の検証を実装。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 対話的に .env を作成・更新する run_wizard を提供。
    - 秘密値はマスク表示、選択式項目・デフォルト・説明文をサポート。
    - 書き込みテンプレートはコメント付きで生成し、`.env を絶対に Git にコミットしない` 注意を出力。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の有無、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML が有れば）パース検証、live 環境向けの注意喚起などの検査を実装。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler（stdout 使用）と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソールのみで継続。
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）を実装。
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度 / CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）に対応した優先度設定（nice / HIGH_PRIORITY_CLASS などのラップ）。
    - set_cpu_affinity により最初の N コアにプロセスをピン留め可能（アクセス拒否等は警告でスキップ）。
- ポートフォリオ構築 (Portfolio)
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順（同点時 signal_rank 昇順）で上位 N を選択する純関数を実装。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア正規化配分を実装。すべてのスコアが 0.0 の場合は等配分にフォールバックして警告をログ出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を適用し、過剰セクターの新規候補を除外するロジックを実装（"unknown" セクターは上限適用外）。
    - calc_regime_multiplier: market レジームに応じた乗数（bull/neutral/bear）を返す関数を実装。未知レジームは 1.0 でフォールバックし警告。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 発注株数計算ロジック（allocation_method: risk_based | equal | score）を実装。
      - risk_based: リスク％、stop_loss％を用いた株数算出。
      - equal/score: weight に基づく割付と 1銘柄上限、lot_size（単元株丸め）を考慮。
      - aggregate cap: 合計投下資金が available_cash を超える場合はスケールダウンし、端数（lot 単位）の再配分を残差順に行う。
      - cost_buffer（手数料・スリッページ見積）を価格に乗じて保守的に見積る。
      - 価格欠損時はスキップし、ログ出力で通知。
- リサーチ / ファクター
  - research/factor_research.py: ファクター計算モジュールの基盤を追加。
    - モメンタム / MA200 / ATR / 流動性などを計算する設計方針と定数を定義（モメンタム計算の実装開始を含む）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算することを想定（外部 API 非依存）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
    - SQLite（PAPER_TRADING_SQLITE_PATH）からシステム安定性、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計して標準出力に整形レポートを出力。
    - PASS/FAIL 判定閾値を設定（稼働率 99% など）し、CLI 引数 --from / --to / --db をサポート。
    - P95 算出、NULL/データ欠損時の扱い、エラーハンドリングを実装。
- パッケージ初期化
  - kabusys/__init__.py: __all__ で主要サブパッケージを公開。

Changed
- なし（初回リリースのため変更点は追加のみ）。

Fixed
- なし（初回リリース）。

Deprecated
- なし。

Removed
- なし。

Security
- なし（特記事項なし）。

Notes / Known limitations
- research/factor_research.py はモメンタム計算の実装を含むが、スナップショット末尾で切れており未完成箇所がある可能性があります。実務での利用前に関数群の完全実装とテストを推奨します。
- 一部の機能（例: BrokerClientFactory の実装、SystemMonitor の実装、ExecutionEngine 内部、duckdb/sqlite テーブルスキーマ等）はこのスナップショットでは参照のみで完全実装箇所は別モジュールに依存しています。実行時にはそれらのモジュールと DB スキーマの整合性確認が必要です。
- OS 権限や psutil に依存する機能（プロセス優先度設定、CPU affinity）は環境により失敗する可能性があり、その場合は警告を出してスキップする設計です。

今後の予定（提案）
- factor_research の完全実装とユニットテスト追加
- ExecutionEngine / SystemMonitor の統合テストと E2E 検証スイート
- ドキュメント（README / Operation Guide / DB schema）の整備
- ログ収集・メトリクス送信（Prometheus / external monitoring）連携

---- 

（必要であれば、各ファイルごとの変更点をより詳細に分割してバージョン履歴へ反映します。ほしい粒度を教えてください。）