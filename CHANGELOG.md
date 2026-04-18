# Keep a Changelog
すべての変更は semver に従って記載します。  
このファイルはコードベースの現在の状態から推測して作成しています。

## [0.1.0] - 初回リリース
初期リリース。システム全体のコア機能、CLI ツール、ユーティリティ、ポートフォリオ構築ロジック、モニタリング/実行プロセス起動スクリプトなどを含む。

### 追加
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 環境/設定管理
  - Settings クラスを実装し、環境変数から設定値を取得可能に。
  - 自動 `.env` ロード機構を追加（優先順: OS 環境 > .env.local > .env）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` 行パーサを強化（`export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの適切な扱いに対応）。
  - 必須/オプション環境変数の取得ヘルパー (`_require`) と値検証ロジック（`KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` など）を実装。
  - Paper Trading 用 DB パス (`PAPER_TRADING_SQLITE_PATH`) と fill mode (`PAPER_FILL_MODE`) を設定可能に。

- CLI ツール
  - config_setup: 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。
    - 秘密項目はマスク表示。デフォルト／既存値の再利用、最終確認、.env 書き出しテンプレートを提供。
    - .env の生成時にコミットしてはいけない旨の注意文を出力。
  - validate_config: 起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV、DB パス、config/*.yaml の存在／パース（PyYAML があれば中身検証）や本番時ガード項目をチェック。`--strict` で警告を失敗扱いにできる。
  - tools/paper_verification_report: Paper Trading の検証レポート生成ツールを追加。
    - レポートはシステム安定性（稼働率等）、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を出力。
    - デフォルト閾値（PASS/FAIL 判定）を定義:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - コマンドライン引数で日付範囲指定、DB パス指定が可能。

- 実行 / 監視用スクリプト
  - run_execution:
    - ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合、Paper Trading 専用の SQLite を使用して本番 DB と完全分離（`data/paper_trading.db` をデフォルト）。
    - BrokerClientFactory 経由で適切なブローカークライアント（Mock含む）を生成。
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag による停止検出、pid ファイル管理、最大 30 秒の待機を実装。
  - run_monitoring:
    - SystemMonitor のポーリングループ起動スクリプトを追加。起動時にプロセス優先度を "high" に設定。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や整数変換失敗）はデフォルトにフォールバックして警告を出す。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する（監視 DB を共通化）。
    - 停止は data/stop_requested.flag の存在検出で行う。

- 監視 DB 初期化
  - monitoring_db 初期化ヘルパー (`init_monitoring_db`) を呼び出し、監視用テーブルが存在することを保証（冪等）。

- DuckDB 統合
  - DuckDB 接続を使用するためのパス取得（Settings.duckdb_path）と接続確立を追加。research/factor_research や ExecutionEngine 等で利用する設計。

- ユーティリティ
  - process_priority ユーティリティを追加:
    - Windows / POSIX の差分を吸収してプロセス優先度を設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
    - 権限不足や未対応環境の場合は警告を出してスキップする安全策を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算。全銘柄のスコア合計が 0 の場合は等金額配分にフォールバックして警告。
  - risk_adjustment:
    - apply_sector_cap: 既存保有を元にセクター集中上限（max_sector_pct）を超えるセクターの新規候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: レジームに応じた投下資金乗数を提供（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして警告。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based","equal","score"）に基づいて発注株数を計算。単元株（lot_size）で丸め、per-position と aggregate の上限を考慮。投資合計が利用可能現金を超える場合はスケーリングし、端数は再配分ロジックで可能な限り補完。cost_buffer により手数料/スリッページを保守的に評価。

- リサーチ（ファクター計算）
  - research/factor_research:
    - DuckDB の prices_daily テーブルを参照してモメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR）、流動性指標等を計算する関数を実装。
    - 欠損データ時の扱い（行数足りない場合は None）を明示。

### 変更
- なし（初期リリースのため該当なし）

### 修正（設計上の注意点・フォールバックを含む）
- .env の自動読み込みで OS 環境変数を保護するため、既存の OS 環境変数は上書きしない（ただし .env.local は override=True で読み込めるが protected により OS 環境は保護）。
- MONITOR_POLL_INTERVAL の不正値（0 以下や文字列）に対してはデフォルト値にフォールバックし、time.sleep に渡して ValueError を避ける堅牢性を確保。
- process_priority の未対応 OS や権限不足時には警告ログを出し処理をスキップすることで起動失敗を防止。
- Paper Trading 環境は本番 DB と分離することで実運用と検証データの混同を避ける設計に。

### セキュリティ
- config_setup により生成される .env ファイルは絶対に Git にコミットしない旨の注記を記載。
- 秘密情報（J-Quants トークン、kabu API パスワード、LINE トークンなど）は Settings 経由で必須項目として管理し、未設定時はエラーを投げる（検証 CLI でも検出）。

---

注: 本 CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際のコミット履歴や意図とは異なる場合があります。必要に応じて日付、著者、より詳細な変更理由を追加してください。