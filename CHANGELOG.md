# Changelog

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」準拠の形式を想定しています。リリース日はコードベースから推測した日付を記載しています。

フォーマットの説明:
- Added: 新規追加された機能やモジュール
- Changed: 既存機能の振る舞い変更や設計上の決定
- Fixed: バグ修正（該当する場合）
- Deprecated / Removed / Security: 該当時に記載

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-23
初期リリース想定。自動売買システム「KabuSys」のコアユーティリティ、実行・監視用スクリプト、ポートフォリオ構築ロジック、設定用 CLI、解析ツールなどをまとめて追加。

### Added
- パッケージバージョンを定義
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 実行・監視エントリポイント
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離して動作可能。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて実行スレッドで稼働。
    - 停止制御: data/stop_requested.flag の検知で安全に停止。PID ファイル (data/execution.pid) を扱う。
    - 起動時にプロセス優先度を "high" に設定。

  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出力。
    - 監視用 DB は環境にかかわらず設定上の sqlite_path（本番監視 DB）を使用。
    - 停止制御: data/stop_requested.flag の検知でループを終了。
    - 起動時にプロセス優先度を "high" に設定。

- 環境設定・管理
  - src/kabusys/config.py
    - .env/.env.local の自動ロード機構（プロジェクトルート検出: .git または pyproject.toml）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env の行パース実装（export プレフィックス、クォート、インラインコメントの扱いを含む）。
    - Settings クラスを通した環境変数アクセスラッパ（J-Quants / kabuステーション / DB パス / 各種閾値 / KABUSYS_ENV, LOG_LEVEL のバリデーション等）。
    - Paper Trading に関する設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等）。

  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を新規作成・更新する CLI。
    - J-Quants / kabu API / DB パス / LOG_LEVEL / Kill Flag 設定などの項目を対話で編集・保存。

  - src/kabusys/validate_config.py
    - 起動前チェック CLI。必須環境変数の有無、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および PyYAML があればパース検証を実施。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純関数群、DB に依存しない）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソート（同点は signal_rank でブレーク）と上位 N 抽出。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比率で正規化した重み。全スコアが 0 の場合は等金額配分にフォールバック（WARNING）。

  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用し、既存保有比率で上限超過するセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバック）。

  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: 重み・候補・価格情報・現金量・制約（risk_pct、stop_loss_pct、max_position_pct、max_utilization、単元株 lot_size、cost_buffer 等）を考慮して銘柄ごとの発注株数を算出。risk_based / equal / score の配分方式に対応。aggregate cap を満たすためのスケーリングと lot 単位での再配分ロジックを実装。

  - src/kabusys/portfolio/__init__.py
    - 上記関数群をエクスポートしてモジュールとして公開。

- ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一的なログ初期化ユーティリティ。
    - stdout 出力用 StreamHandler（stdout を使用）と、日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト INFO。
    - ログディレクトリ解決順: 引数 > 環境変数 LOG_DIR > デフォルト logs/。ディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。

  - src/kabusys/utils/process_priority.py
    - プロセス優先度設定ユーティリティ（Windows の優先度定数と POSIX の nice 値を吸収）。
    - set_process_priority(level) により "high"/"normal"/"low" を指定可能。権限不足時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) で最初の N コアにピンニング（対応しない環境では警告）。

- 監視関連
  - src/kabusys/monitoring/* 関連の初期化呼び出しを各スクリプトで行う（init_monitoring_db を使用して監視テーブルの存在を保証）。

- ペーパートレード検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）からデータを集計して検証レポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数など。
    - 閾値に基づく PASS/FAIL 判定を実装（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms）。
    - 日付フィルタ (--from / --to)、DB パスのオーバーライド (--db) をサポート。

- 研究用モジュール（ファクター計算の基盤）
  - src/kabusys/research/factor_research.py
    - モメンタム / Value / Volatility / Liquidity 等のファクター計算方針と定数を追加。DuckDB 経由で prices_daily / raw_financials を参照する設計。
    - （コード中に計算ヘルパーや定数が用意されているため、ファクター計算の基盤が実装されていることを意図）。

### Changed
- ログ出力のデフォルトと振る舞い
  - logging_setup により全起動スクリプトが統一的にログ設定を行う設計になり、ファイルハンドラ作成失敗時にコンソールのみで継続する挙動を明確化。

- 環境変数ロードの設計
  - config.py にて OS 環境変数を保護しつつ .env/.env.local を自動で読み込む仕組みを導入（.env.local の上書き、OS 環境変数は保護）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

### Fixed
- （初期リリース想定のため明確なバグ修正はなし。実行環境や権限によりファイル/ディレクトリの作成やプロセス優先度設定が失敗する場合に、警告を出して安全にフォールバックするロバストネスが追加されている点を含む。）

### Notes / Implementation details（重要）
- 停止フラグ:
  - 実行/監視プロセスはプロジェクトルート直下の data/stop_requested.flag を監視して安全停止する設計。
- Paper Trading の分離:
  - run_execution は paper_trading モードで専用の SQLite DB を参照するため、本番の監視 DB とデータ分離が可能。
- 設定検証:
  - validate_config は config/*.yaml の存在確認と、PyYAML がある場合は YAML の安全パースまで行う。PyYAML が未インストールの場合はパース検証をスキップして警告を出す。
- ロギング:
  - コンソールは stdout を使用（stderr ではない）。これにより cron 等で stdout/stderr を一本化してリダイレクトする運用に配慮。
- 一部モジュール・関数（研究用の calc_momentum 等）はファイル中に長い説明や設計方針が記述されており、追加実装・テストにより完全機能化されることが期待される。

---

今後のリリースでは以下が想定されます:
- ExecutionEngine / SystemMonitor の詳細実装に対するテスト追加およびドキュメント整備
- factor_research の完全実装（SQL/計算ロジックの実装完了）
- さらなる健全性テストとエラー処理の強化

（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートはリポジトリの git 履歴や作者の意図に基づいて調整してください。）