# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このリポジトリの初回リリースを以下のように記録します。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 基本パッケージ情報
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として公開。

- 起動スクリプト
  - run_execution: 実行エンジン起動スクリプトを追加。  
    - プロセス優先度設定、SQLite / DuckDB 接続、ブローカークライアント生成、OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine のスレッド実行、停止フラグによる安全停止をサポート。  
    - KABUSYS_ENV が `paper_trading` の場合は paper 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は環境にかかわらず本番の sqlite_path を使用する設計（監視専用 DB 初期化を実施）。  
    - 停止フラグファイル検出で安全終了、例外はログに記録して次ループへ継続。

- 環境設定・検証ツール
  - config_setup: 対話式 .env 作成／更新ウィザードを追加。必須項目・デフォルト値・秘密値マスク表示に対応し、.env を生成。
  - validate_config: 起動前に .env および config/*.yaml の検証を行う CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、YAML ファイルの存在とパース検証（PyYAML が利用可能な場合）、本番環境 (live) に対する追加ガードを実装。  
    - `--strict` オプションで警告をエラー扱いにできる。

- 環境設定管理
  - config.Settings クラスを追加。環境変数から設定値を読み取り、各種プロパティ（J-Quants トークン、kabu API パスワード、DB パス、paper_trading 用設定、監視しきい値、環境判定など）を提供。  
    - KABUSYS_ENV / LOG_LEVEL のバリデーション、paper_trading 用 fill モードの妥当性チェックなどを含む。
  - 自動 .env ロード機構を実装（プロジェクトルートを .git または pyproject.toml から探索し、`.env` と `.env.local` を OS 環境変数に重複保護付きで読み込む。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

- ロギング・プロセスユーティリティ
  - utils.logging_setup.setup_logging を追加。  
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル・ログディレクトリの解決順をサポート。
  - utils.process_priority を追加。  
    - Windows / POSIX を抽象化してプロセス優先度（high/normal/low）を設定。psutil を用いた CPU affinity 設定関数も提供。アクセス権限や未サポート環境では警告を出してスキップ。

- ポートフォリオ構築関連
  - portfolio モジュールを追加（純粋関数群、DB 参照なし）。エクスポート済み関数:
    - select_candidates: BUY シグナルをスコア降順＋タイブレークで上位 N を選出。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分。スコア合計が 0 の場合は等配分にフォールバック。
    - apply_sector_cap: セクター集中上限チェック（既存保有・当日売却予定を考慮、"unknown" セクターは適用除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数 (bull/neutral/bear) を返す（未知レジームは警告して 1.0 にフォールバック）。
    - calc_position_sizes: allocation_method（risk_based / equal / score）に従う株数決定、単元株丸め、per-stock / aggregate cap、cost_buffer を考慮したスケーリングロジックを実装。

- Paper Trading 検証ツール
  - tools.paper_verification_report: Paper Trading の SQLite ログから検証レポートを生成する CLI を追加。  
    - 指標: 稼働率 (uptime)、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシなど。  
    - デフォルト基準値（合格ライン）を定義（稼働率 99%、fill 90%、send 95%、P95 レイテンシ <= 200 ms）。  
    - 日付フィルタ（--from / --to）と DB パス指定（--db または PAPER_TRADING_SQLITE_PATH）に対応。

- 監視 DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を利用する起動フローを run_* スクリプトで採用（監視テーブルの存在を保証）。

- 研究用ファクター計算のスケルトン
  - research.factor_research にファクター計算の骨子を追加（モメンタム / MA200 / ATR / ボリューム等を計算する方針と定数を定義）。DuckDB 経由で prices_daily / raw_financials を参照する設計。注: 実装は途中（ファイル末尾が未完）。

### 変更 (Changed)
- ログ出力の標準出力を stdout に統一
  - setup_logging で StreamHandler を stdout に設定（cron/task scheduler からのリダイレクトを想定）。

- .env 読み込みの堅牢化
  - シングルクォート・ダブルクォート内のバックスラッシュエスケープ、`export KEY=val` 形式、インラインコメントの扱いを考慮したパーサを実装。

### 修正 (Fixed)
- 実行フローの安全性向上
  - run_execution / run_monitoring でプロセス優先度を起動直後に設定するようにし、起動中の stop flag / KeyboardInterrupt に対するクリーンアップ（DB 接続クローズ）を確実に実行。

### 注意点 / 既知の問題 (Known issues)
- research.factor_research の実装は途中で終了しており、完全なファクター計算ロジックが未実装（今後の作業課題）。
- 一部の価格欠損（price が 0.0）の取り扱いに TODO コメントあり（現状では exposure が過少見積りされる可能性）。将来的にフォールバック価格取得を検討する必要あり。
- process_priority / set_cpu_affinity は環境依存（権限・OS サポート）により実行できない場合があり、その場合はログ警告を出してスキップする設計。

---

今後の予定（非正規項目）
- factor_research の完成（DuckDB クエリ + 正規化ユーティリティ統合）。
- ExecutionEngine / RiskManager の統合テストと paper_trading シミュレーション検証。
- config/*.yaml のサンプル生成スクリプトの整備および CI での validate_config 実行。