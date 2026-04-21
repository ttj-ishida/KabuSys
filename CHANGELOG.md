# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の書式に従います。  

※以下はリポジトリ内のソースコードから推測して作成した変更履歴です。

## [0.1.0] - 2026-04-21

### 追加
- 全体
  - 初回リリース相当の機能セットを追加。モジュール構成、CLI、ユーティリティ類、ポートフォリオ構築ロジック等を収録。
  - パッケージ バージョンを `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。

- 起動スクリプト
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - プロセス優先度を高に設定して起動。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の専用 SQLite（`data/paper_trading.db` がデフォルト）を使用し、MockBrokerClient を用いた分離された動作をサポート。
    - Engine をスレッドで実行し、プロジェクトルートの stop フラグ（data/stop_requested.flag）で安全に停止可能。
    - PID ファイル出力用パスを扱う（data/execution.pid のデフォルト）。
  - 監視ポーリングループ起動スクリプト `run_monitoring.py` を追加。
    - SystemMonitor を初期化し、監視ループを定常実行。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は環境に関わらず本番用の sqlite_path を使用して監視データを保存。
    - stop フラグ検出でループを終了し、KeyboardInterrupt にも対応。

- 設定管理 / CLI
  - 設定読み込み・管理モジュール `config.py` を追加。
    - プロジェクトルート（.git または pyproject.toml）を基に自動で .env / .env.local を読み込む仕組みを実装。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` のパースは `export ` プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントに対応。
    - 必須環境変数チェック用の `_require()`、各種設定プロパティ（DB パス、ペーパートレード設定、監視閾値、環境種別判定など）を提供。
  - 設定検証 CLI `validate_config.py` を追加。
    - `.env` と `config/*.yaml` の存在・基本妥当性チェックを実施。
    - 必須環境変数の未設定検出、KABUSYS_ENV の妥当性チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェックを行う。
    - PyYAML が無ければ YAML 内容検証をスキップし警告を出力。
    - `--strict` オプションで警告を失敗扱い（exit code 1）にできる。
  - 環境設定ウィザード `config_setup.py` を追加。
    - 対話式で .env を作成・更新するウィザード。J-Quants トークンや API パスワード等の必須項目、ログレベル、KILL フラグ設定などを対話的に設定可能。
    - 既存 .env の読み込みと既存値の再利用をサポート、保存前に確認プロンプトを表示。

- モジュール（ポートフォリオ / 受注設計等）
  - ポートフォリオ構築関連モジュールを追加（pure functions）。
    - `portfolio.portfolio_builder`:
      - 候補選定（score 降順、タイブレークに signal_rank）select_candidates
      - 等金額配分 calc_equal_weights
      - スコア加重配分 calc_score_weights（スコア合計が 0 の場合に等金額にフォールバック）
    - `portfolio.risk_adjustment`:
      - セクター集中上限適用 apply_sector_cap（既存保有を考慮、"unknown" セクターは制限対象外）
      - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマップし、未知のレジームは警告して 1.0 にフォールバック）
    - `portfolio.position_sizing`:
      - 各銘柄の発注株数計算 calc_position_sizes（allocation_method に "risk_based"/"equal"/"score" をサポート）
      - 単元株（lot_size）丸め、per-position 上限、aggregate cap、コストバッファ適用、スケーリングと残差に基づく追加配分ロジックを実装。
  - これらはすべてメモリ内純粋関数として実装され、DB 参照は行わない設計。

- ユーティリティ
  - ロギング設定ユーティリティ `utils/logging_setup.py` を追加。
    - ルートロガーを統一設定、StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app>.log、30日保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決順を定義。既存ハンドラのクリーンな置換処理を行う。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - プロセス優先度・CPU affinity ユーティリティ `utils/process_priority.py` を追加。
    - Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定。psutil を利用し、権限不足や未対応プラットフォームは警告でスキップ。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供（引数 None で何もしない）。エラーは警告でスキップ。

- 実行関連ロジック
  - Execution 側で以下のコンポーネント組み立てを実装（ファクトリ等を利用）:
    - BrokerClientFactory（設定に応じたブローカークライアント生成）
    - OrderRepository（SQLite 接続を利用）
    - OrderManager、RiskManager（デフォルトの RiskConfig 値を設定）、Reconciler
    - ExecutionEngine を起動して run_session を別スレッドで実行。stop フラグ検出で engine.stop を呼ぶ仕組み。

- 監視関連
  - 監視 DB 初期化関数 init_monitoring_db を使用して監視テーブルの存在を保証（冪等）。
  - SystemMonitor（監視ロジック）は起動時に SQLite と DuckDB の接続を受け取る設計。

- ツール
  - Paper Trading の検証レポート生成スクリプト `tools/paper_verification_report.py` を追加。
    - 指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg / max / P95）等を集計してレポート出力。
    - デフォルト DB パスは `data/paper_trading.db`。`PAPER_TRADING_SQLITE_PATH` 環境変数または `--db` オプションで上書き可能。
    - P95 の算出、欠損データに対する N/A 表示、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）による PASS/FAIL 判定を実装。

- リサーチ
  - 基本的なファクター計算モジュール `research/factor_research.py` の骨組みを追加（Momentum / Value / Volatility / Liquidity 等を計算する設計、DuckDB を利用）。（ファイルの途中で実装が続く設計になっている）

### 変更
- 環境変数パースの改良（config._parse_env_line）
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応し、より柔軟な .env パースを実現。
- 自動 .env 読み込みの挙動
  - OS 環境変数を保護するため、先に存在する環境変数は上書きされない。`.env.local` は上書きモードでロード（ただし OS 環境変数は保護）。
- ログ設定
  - stdout を使用する StreamHandler を採用（cron 等で stdout/stderr を一本化する運用を考慮）。
  - 既にハンドラが存在する場合は一旦閉じてから再設定する仕様に変更。

### 修正（バグ修正 / 安全性向上）
- ポーリング間隔の妥当性チェック
  - `MONITOR_POLL_INTERVAL` の不正値（負数やゼロ、非数）を検出して警告後にデフォルトへフォールバックするように修正（run_monitoring.py）。
- DB 周りの冪等性
  - 監視テーブル初期化（init_monitoring_db）を起動時に必ず呼び、テーブルが存在しない場合も起動できるようにした（run_monitoring.py / run_execution.py）。
- ペーパートレードと本番 DB の分離
  - `run_execution.py` では paper_trading 環境のとき専用 SQLite を使用し、本番監視 DB と完全に分離するよう設計変更。
- エラー耐性
  - SystemMonitor.check_once() 実行中に例外が発生しても監視ループは継続し、例外情報をログ出力して次のポーリングまで待機するように安全化。
  - バックグラウンドスレッド実行中に stop フラグを検出した場合は ExecutionEngine.stop() を呼んで安全に終了するフローを実装。

### ドキュメント / メタ
- 各モジュールに関数・クラスの docstring を充実させ、動作仕様・引数・返り値・副作用（DBアクセスの有無等）を明記。
- config_setup による .env のテンプレート生成ロジックを追加（保存時の注意喚起を含む）。

### 既知の制約 / TODO（実装上の注意）
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合、エクスポージャーが過小見積りとなる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO コメントあり。
- research/factor_research.py はファイル途中で実装が継続する想定（未完の部分あり）。完全実装は今後の課題。
- ロギング用ディレクトリ作成やプロセス優先度設定で権限不足が起きた場合は警告を出して処理を継続する設計（ファイル出力無効化や優先度設定スキップ）。

---

今後のリリースでは下記を想定しています（例）:
- research/factor_research の完全実装とテスト追加
- ExecutionEngine / BrokerClient の統合テスト、MockBroker の拡張
- モニタリング・アラート（LINE 通知）実装の拡充
- config/*.yaml のスキーマ検証追加と CI 連携

（この CHANGELOG はソースコードの内容からの推測に基づき作成しています。実際の変更履歴が別にある場合はそちらを優先してください。）