# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
（コードベースから推測して作成しています。実装の意図や振る舞いを元にまとめた初期リリース向けの変更履歴です）

## [0.1.0] - 2026-04-20

### Added
- 全体
  - 初期リリース。自動売買システム「KabuSys」のコアユーティリティ、実行・監視スクリプト、ポートフォリオ構築ロジック、およびいくつかのツールを追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用専用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と完全分離して動作する設計を導入。
    - BrokerClientFactory を用いてブローカークライアントを生成（Mock/実 API を切替）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで実行。停止フラグ検出時に Engine.stop() を呼ぶ実装。
    - 実行 PID を `data/execution.pid` に保存する仕様を想定（pid_file パスを ExecutionEngine に渡す）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 停止フラグファイル（`data/stop_requested.flag`）を検知してループを安全に終了。
    - 監視用 DB は環境に関わらず本番の sqlite_path を使用する設計（監視は本番 DB を参照する想定）。

- 設定管理
  - config.py: 環境設定管理クラス `Settings` を追加。
    - .env 自動読み込み機構を導入（プロジェクトルートを `.git` または `pyproject.toml` で探索）。
    - 読み込み順: OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - .env の行パースに対応：`export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などをサポート。
    - 必須/オプションの環境変数、DB パス、paper trading 用設定、監視閾値（CPU/Mem/Disk）などをプロパティで提供。`KABUSYS_ENV` / `LOG_LEVEL` のバリデーション実装。
  - config_setup.py: 対話式ウィザードで `.env` を初期作成・更新する CLI を追加。
    - 秘匿入力（マスク表示）や選択肢サポート、既存 `.env` の読み込み再利用、最終確認後に `.env` を書き出す機能を提供。
    - 書式テンプレートはコミット禁止の注意書き付きで保存。

- 設定検証
  - validate_config.py: 起動前に .env と config/*.yaml の整合性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在確認と PyYAML によるパースチェック（PyYAML 未インストール時は警告でスキップ）。
    - `--strict` オプションで警告も失敗扱い（exit 1）にできる。

- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一設定ユーティリティを追加。
    - stdout へ StreamHandler、日次ローテーションの TimedRotatingFileHandler（`logs/<app_name>.log`、30 日保持）を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する安全策を実装。
    - ログレベル・ログディレクトリの解決順を明示。
  - utils/process_priority.py: プロセス優先度と CPU affinity を抽象化するユーティリティを追加。
    - Windows / POSIX（Linux/Mac 等）差分を吸収し、`set_process_priority("high"|"normal"|"low")` で優先度を設定。
    - `set_cpu_affinity(n)` で最初の n コアに固定する機能（アクセス権限や未対応 OS は警告でスキップ）。
    - psutil の権限不足や未対応機能に対する例外ハンドリングとログ出力。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py:
    - 候補選定 select_candidates（スコア降順、タイブレークは signal_rank）、等金額 calc_equal_weights、スコア加重 calc_score_weights（スコア合計0時に等金額へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存保有時価に基づき、上限超過セクターの新規候補除外）。unknown セクターは上限適用除外。
    - calc_regime_multiplier: 市場レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 各銘柄の発注株数を計算する包括的ロジックを実装。
      - allocation_method: "risk_based"（リスクベース）/ "equal" / "score" をサポート。
      - 単元株丸め（lot_size、デフォルト 100）、1 銘柄上限（max_position_pct）、総投下上限（max_utilization）、cost_buffer（手数料・スリッページ見積り）を考慮。
      - aggregate cap 適用時はスケーリングと fractional 残差処理（lot 単位で再配分）を実装。
      - 価格欠損や価格 <=0 の銘柄はスキップ。TODO コメントで将来的な拡張点を明示。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成ツールを追加。SQLite（Paper Trading DB）から集計して以下を判定・表示:
      - システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）など。
    - デフォルトしきい値: 稼働率 >= 99.0%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
    - 日付フィルタ（--from/--to）や DB パス指定（--db）をサポート。DB が存在しない場合のエラーメッセージを出力。

- データ分析（着手）
  - research/factor_research.py: ファクター計算モジュールを追加（Momentum・Value・Volatility・Liquidity などの計算設計が記載）。
    - DuckDB を利用し prices_daily / raw_financials テーブルのみ参照する設計。関数インタフェースと定数が追加されているが、ファイル末尾が途中で切れており実装は続行中（WIP）。

### Changed
- なし（初期リリースのため新規追加が中心）

### Fixed
- なし（初期リリース）

### Known issues / Work in progress
- research/factor_research.py が途中で切れており、モメンタム計算関数の実装が未完。今後のリリースで完成予定。
- position_sizing の価格欠損処理に関する注記（TODO）あり: price が欠損した場合のフォールバック戦略（前日終値等）は未実装。
- 実際のブローカー連携部分（BrokerClientFactory、ExecutionEngine 内の細部）はこの差分からは外部実装依存のため、実稼働前に実ブローカー/モックの動作確認が必要。
- 一部ファイル（例: config/*.yaml 生成スクリプトや ExecutionEngine の挙動の詳細）は config と合わせて運用手順のドキュメント整備が推奨。

---

以上がコードベースから推測して作成した CHANGELOG（初期リリース 0.1.0）です。追って実装が進む箇所（WIP）や運用上の注意点があれば、次のリリースで詳細を追加してください。必要であれば各変更点に対応するファイル・関数の参照一覧や、運用手順ドキュメント（起動手順、環境変数設定例、ログ/DB の配置例）も作成できます。どの範囲を詳細化するか指示ください。