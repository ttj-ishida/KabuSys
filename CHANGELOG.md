# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。  
このプロジェクトではセマンティックバージョニングを採用します。

現在のバージョン: 0.1.0

## [0.1.0] - 2026-04-20

### 追加
- 基本アプリケーションパッケージを追加（kabusys）。
  - バージョン情報を `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - `run_execution.py`：ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合に専用の Paper Trading SQLite DB（`data/paper_trading.db`、環境変数で上書き可）を使用するよう分離。
    - 起動時にプロセス優先度を High に設定。
    - 停止フラグ（`data/stop_requested.flag`）を監視して安全にエンジンを停止。
    - ExecutionEngine をデーモンスレッドで実行し、スレッド生存監視で停止フラグを検出。
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境に関わらず本番 `sqlite_path` を使用（監視テーブルの初期化処理を実行）。
    - 停止フラグ検出でループ終了、KeyboardInterrupt に対応。

- 設定管理
  - `config.py`：.env 自動ロード機構と Settings クラスを実装。
    - プロジェクトルートを `.git` または `pyproject.toml` で検出して `.env` / `.env.local` を自動読み込み（OS 環境変数を保護）。
    - `.env` のパースは `export KEY=val`、シングル/ダブルクォート、エスケープ、インラインコメントなどに対応した堅牢な実装。
    - 各種設定値（DB パス、API キー、モードフラグ、監視しきい値など）をプロパティとして提供し、入力値検証を行う（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。
    - `settings = Settings()` を提供。

  - `config_setup.py`：対話式の .env 生成/更新ウィザードを追加。
    - 各設定項目定義、既存 .env 読み込み、シークレットマスキング、保存確認機能を提供。
    - `.env` 書き出し時にコメントヘッダを付与（.env をコミットしない旨の注意）。

  - `validate_config.py`：設定検証 CLI を追加。
    - 必須環境変数や KABUSYS_ENV、DB パス、config/*.yaml の存在・パースを検証。
    - `--strict` モードで警告をエラー扱いにできる。
    - PyYAML の有無による挙動（インストールされていない場合は YAML 検証スキップ）に対応。
    - 本番環境向けのガード（LINE 通知設定や Kill Switch の自動クリア設定の警告）を実装。

- ポートフォリオ構築関連（純粋関数群）
  - `portfolio/portfolio_builder.py`：候補選定と重み付け（等金額・スコア加重）を実装。
    - スコア同値時の tie-breaker（signal_rank）を実装。
    - 全スコア 0 の場合に等金額配分へフォールバックして警告を出力。
  - `portfolio/risk_adjustment.py`：セクター集中制限とレジーム乗数を実装。
    - apply_sector_cap：既存保有のセクター比率に基づき新規候補を除外。
    - calc_regime_multiplier：レジーム（bull/neutral/bear）に応じた投下資金乗数を返却。未知レジームは 1.0 にフォールバックして警告。
  - `portfolio/position_sizing.py`：株数決定ロジックを実装。
    - allocation_method に応じた計算（risk_based / equal / score）。
    - lot_size（単元）で丸め、1 銘柄上限・aggregate 上限の両方を考慮。
    - available_cash を超える場合はスケーリングして端数は残差ロジックで再配分。
    - cost_buffer（手数料・スリッページ見積り）を考慮した保守的評価。

- 実行ユーティリティ
  - `utils/logging_setup.py`：統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）を組み合わせて設定。
    - ログディレクトリ自動作成（失敗時はファイルハンドラをスキップしてコンソール出力のみ）。
    - ログレベルとログディレクトリの解決順を明示。
  - `utils/process_priority.py`：プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分を吸収して high/normal/low の抽象レベルで設定。
    - 設定に失敗した場合は警告でフォールバック。
    - CPU affinity 固定用の set_cpu_affinity 関数を提供。

- 実行時の依存連携（概念実装）
  - `execution/*`（ファイル参照）：BrokerClientFactory、ExecutionEngine、OrderManager、RiskManager、Reconciler など起動時に組み立てる構成を想定（実装は別ファイル群）。
  - `monitoring/*`（ファイル参照）：SystemMonitor と監視 DB 初期化を呼び出すフローを実装。

- ツール
  - `tools/paper_verification_report.py`：Paper Trading の検証レポート生成スクリプトを追加。
    - system_status/trade_logs/risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出して表示。
    - CLI 引数で期間指定（--from / --to）と DB 指定（--db）をサポート。
    - Pass/Fail 基準値（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）を定義し判定を出力。

- 研究/ファクター計算
  - `research/factor_research.py`：ファクター計算モジュールの骨組みを追加（Momentum 等の定義・定数を含む）。
    - DuckDB 接続を受け、prices_daily / raw_financials を参照して因子を計算する設計。
    - モメンタム（1/3/6M）、MA200乖離、ATR、出来高系等を想定した定数を実装（実装は継続中）。

### 変更
- 環境変数の自動ロード挙動
  - OS 環境変数を保護しつつ `.env` → `.env.local` の順で読み込む仕様とした（`.env.local` は上書き可能。ただし OS 環境変数は上書きされない）。

- ロギングの既定動作
  - ログは標準出力（stdout）とファイルへ出るように統一。ファイルは日次ローテーションで最大 30 世代保持。

### 修正（バグ修正相当・堅牢化）
- .env パーサの堅牢化
  - `export` キーワード対応、クォート文字内のバックスラッシュエスケープ、インラインコメントの取り扱いなど実環境でよくあるパターンに対応。
  - 空行・コメント行を無視する実装により .env の読み取りが安定。

- process_priority と CPU affinity でのエラー耐性向上
  - 管理者権限不足や未対応プラットフォームでの例外を警告にフォールバックしてプロセス継続可能にした。

- 起動スクリプトのリソースクリーンアップ
  - run_monitoring / run_execution の終了時に SQLite / DuckDB コネクションを確実にクローズするようにした。

### 既知の制限 / 注意点
- research/factor_research.py は一部実装が継続中（ファイル末尾が途中で切れているため、いくつかの関数は未完成）。
- ExecutionEngine / BrokerClient 等の詳細実装は別モジュールに依存しており、本リリースでは起動フローの組み立てとハンドリングに焦点を当てています。
- .env ファイルは機密情報を含むため、リポジトリにコミットしないでください（config_setup の出力ヘッダにも注意喚起あり）。

### 互換性（Breaking Changes）
- 本リリースは初期リリースのため既存互換性の問題はありません。

---

今後の予定（短期）
- research/factor_research の完全実装（各ファクター計算ロジックの実装・テスト）。
- ExecutionEngine 周りの統合テスト、Broker クライアントのモック整備。
- CI での設定検証（validate_config）と自動テストの整備。