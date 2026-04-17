# Changelog

すべての重要な変更は Keep a Changelog の方針に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

全般:
- セマンティクスは semantic versioning に準拠します（本リリースは初回公開として 0.1.0）。

## [0.1.0] - 2026-04-17

Added
- 基本アプリケーション骨格を追加。
  - パッケージ情報:
    - バージョン: `kabusys.__version__ = "0.1.0"`
    - エクスポート: data, strategy, execution, monitoring モジュール群の雛形を含む。

- 環境設定 / 設定管理
  - 自動 .env ロード機能を実装（プロジェクトルートの .env / .env.local）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - ロード時に OS 環境変数は保護され、.env.local は上書き可能。
  - Settings クラス（kabusys.config.Settings）を実装し、アプリケーション設定を環境変数から取得。
    - 必須 / 任意の設定やデフォルト値を管理。
    - サポートする主要環境変数例：
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
      - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
      - KABUSYS_ENV (development / paper_trading / live), LOG_LEVEL
      - PAPER_FILL_MODE (instant|partial|never|reject)
      - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
      - CPU/MEM/DISK 閾値 (CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT)
  - .env パーサーは quoted 値・エスケープ・export プレフィックス・行内コメントを適切に処理。

- 設定ウィザード CLI
  - kabusys.config_setup: 対話式ウィザードで .env を初期作成 / 更新可能。
    - 既存値の読み込み、シークレット項目のマスク表示、保存確認をサポート。
    - デフォルトや選択肢付き項目を定義（KABUSYS_ENV, LOG_LEVEL など）。

- 設定検証 CLI
  - kabusys.validate_config: .env と config/*.yaml の整合性チェックを行う CLI。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、DB パスの親ディレクトリ確認、YAML パース（PyYAML があれば）、
      本番向けの追加警告（LINE 通知設定や Kill スイッチ設定）などを実装。
    - `--strict` オプションで警告も失敗扱い（exit(1)）にできる。

- 実行用エントリポイント
  - run_execution (kabusys.run_execution)
    - ExecutionEngine を起動するためのスクリプト。
    - 起動時にプロセス優先度を「high」に設定（kabusys.utils.process_priority）。
    - DB 接続:
      - 本番環境は `SQLITE_PATH`（monitoring DB）を使用。
      - `KABUSYS_ENV=paper_trading` の場合は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を利用して適切なブローカークライアントを生成（paper_trading 時はモックを利用）。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイルを利用した停止制御とデーモンスレッド管理を実装。

  - run_monitoring (kabusys.run_monitoring)
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 0 以下や不正値はデフォルトにフォールバックし、警告ログを出力。
    - 監視用 DB 初期化（init_monitoring_db）と DuckDB 接続を行い、SystemMonitor.check_once() を定期実行。
    - 停止フラグファイルにより安全に監視ループを終了できる。

- 監視・DB 初期化
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を起動時に呼び出し、監視テーブルの存在を保証（冪等）。

- Paper Trading / 検証ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - SQLite（デフォルト data/paper_trading.db）から統計を抽出し、稼働率、注文成功率、送信率、P95 レイテンシ等を計算して PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ（--from / --to）、しきい値の定義（稼働率 99%、成立率 90% など）を提供。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio:
    - portfolio_builder
      - select_candidates: スコア降順 + signal_rank のタイブレークで候補選定。
      - calc_equal_weights: 等金額配分 (1/N)。
      - calc_score_weights: スコア正規化による重み付け（全スコアが 0 の場合は等配分へフォールバック、警告ログ）。
    - risk_adjustment
      - apply_sector_cap: セクター集中をチェックし、既存保有×価格を用いて上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして警告ログ。
    - position_sizing
      - calc_position_sizes: allocation_method に応じて発注株数を計算（risk_based, equal, score をサポート）。
      - 単元株丸め (lot_size)、per-stock 上限、aggregate cap（available_cash）を考慮したスケーリングロジックを実装。
      - cost_buffer による保守的コスト見積り、スケールダウン時の残差処理（lot 単位での再配分）を実装。
  - すべて DB 非依存の純粋関数として実装され、テスト容易性を重視。

- 研究 / ファクター計算
  - kabusys.research.factor_research: DuckDB の prices_daily / raw_financials を用いたファクター計算モジュールを追加。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（200 日窓）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算（true_range の NULL 伝播を制御して正確に集計）。
    - DuckDB SQL を活用した効率的なウィンドウ集計を利用。

- プロセス優先度 / CPU affinity ユーティリティ
  - kabusys.utils.process_priority:
    - set_process_priority(level): Windows と POSIX（Linux, macOS, FreeBSD）を吸収して優先度を設定。psutil に基づく実装で権限エラー等をハンドリング。
    - set_cpu_affinity(cpu_count): 指定コア数に対して CPU affinity を設定（未対応 OS や権限制約は警告でスキップ）。

Changed
- （新規初版のため該当なし）

Fixed
- （新規初版のため該当なし）

Security
- （新規初版のため該当なし）

Notes / 備考
- ファイルベースの停止フラグ（data/stop_requested.flag）や PID ファイルを用いる運用設計になっており、プロセス制御はファイルシステムを介して行います。運用時は data ディレクトリの配置・権限にご注意ください。
- Paper Trading と本番 DB は分離しており、paper_trading 環境では paper 用 DB（PAPER_TRADING_SQLITE_PATH）を使用して記録・検証を行います。
- YAML パースの検証は PyYAML がインストールされている場合にのみ行われます。インストールされていない環境では警告が出力され、YAML の内容チェックはスキップされます。

今後の予定（非確定）
- strategy / data / execution の詳細実装（実取引ロジック・ブローカー実装・DB スキーマの拡張等）
- 単体テスト・CI の整備とドキュメント拡充
- ロギング・メトリクスの強化（Prometheus 等のエクスポーター）
- ポートフォリオ構築の銘柄ごとの lot_size マスタ対応

--- 
この CHANGELOG はコードベースからの推測に基づいて作成されており、実運用上の詳細はソースコードや関連ドキュメントを参照してください。