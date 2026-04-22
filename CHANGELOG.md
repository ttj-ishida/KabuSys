# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。

## [0.1.0] - 初回リリース
リリース日: (未指定)

概要: 初期機能実装リリース。自動売買システム KabuSys のコアユーティリティ、ランタイムスクリプト、ポートフォリオ構築ロジック、設定管理・検証ツール、およびペーパートレード検証ツールを導入しました。

### 追加 (Added)
- 基本メタ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定管理
  - .env 自動読み込み機構を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 簡易だが堅牢な .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープに対応）。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - Settings クラスを導入:
    - J-Quants / kabu API / LINE / DB パス等のプロパティを提供。
    - `KABUSYS_ENV` / `LOG_LEVEL` / `PAPER_FILL_MODE` 等のバリデーションを実施。
    - Paper Trading 用の `paper_sqlite_path`（環境変数 `PAPER_TRADING_SQLITE_PATH` で上書き可能）を提供。
    - 監視関連設定（PID ファイル、kill フラグパス、閾値等）をプロパティ化。

- 設定ウィザード & 検証 CLI
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加。
    - シークレット項目はマスク表示、選択肢・デフォルト対応、保存前の確認機能あり。
  - validate_config: .env と config/*.yaml の事前検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、YAML の存在・パース検証（PyYAML があれば内容も検証）。
    - `--strict` オプションで警告を失敗扱いにできる。

- ログ設定ユーティリティ
  - setup_logging を提供:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - ログディレクトリ作成に失敗した場合は標準出力のみで継続。
    - ログレベル・ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
    - stdout を使用することで cron 等からのリダイレクト運用を容易に。

- プロセス優先度 / CPU affinity ユーティリティ
  - set_process_priority(level)：
    - Windows / POSIX を透過してプロセス優先度を設定（psutil を利用）。
    - 権限不足や未サポート環境時は警告ログを出力してスキップ。
  - set_cpu_affinity(cpu_count)：
    - 指定コア数にプロセスをピン留め（利用可能コア数を超える場合は全コア使用、例外をハンドル）。

- ランタイム起動スクリプト
  - run_monitoring:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告の上デフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視用 DB 初期化呼び出しを含む）。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全に終了。
    - プロセス優先度を起動時に高く設定。
  - run_execution:
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用 DB（data/paper_trading.db など）に記録し本番 DB と分離。
    - ExecutionEngine の依存コンポーネント（BrokerFactory、OrderRepository、OrderManager、RiskManager、Reconciler）を組み立ててスレッドで実行。停止フラグにより安全停止。
    - 起動時に PID ファイルを管理。

- 監視 DB 初期化
  - init_monitoring_db を呼び出して、必要な監視テーブルが存在することを冪等に保証（monitoring モジュールとの連携）。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で並べ上位を選定（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（スコア全0 の場合は警告して等金額にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: 既存保有のセクター集中度に基づき新規候補を除外するロジック。unknown セクターは除外対象外。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた資金乗数（デフォルト値とフォールバック含む）。
  - position_sizing:
    - calc_position_sizes: allocation_method = "risk_based" | "equal" | "score" をサポート。
      - risk_based: 許容リスク(risk_pct)、損切り(stop_loss_pct)に基づく株数計算。
      - equal/score: 重みと max_utilization を用いる計算。
      - 単元株（lot_size）で丸め、1銘柄上限（max_position_pct）を考慮。
      - aggregate cap の際のスケールダウン実装と、余り（fractional remainder）に基づく追加配分アルゴリズムを導入。
      - price が欠損する場合はスキップしログ出力。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py を追加:
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH で指定可）から指標を抽出してレポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
    - デフォルト閾値を定義（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200ms）と PASS/FAIL 判定ロジック。
    - CLI 引数 --from / --to / --db をサポート。

- データ分析 / リサーチ（部分実装）
  - research/factor_research.py にモメンタム等のファクター計算の骨子を実装（DuckDB 接続を受けて prices_daily / raw_financials を参照する設計）。複数の定数と関数（P95 算出等）の導入を開始。

### 変更 (Changed)
- なし（初期リリースのため該当なし）

### 修正 (Fixed)
- なし（初期リリースのため該当なし）

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- なし

### 注意点・運用メモ
- run_monitoring は監視用 DB として Settings.sqlite_path を常に使用します（KABUSYS_ENV に依存しない挙動）。一方、run_execution は Paper Trading 環境時に専用の paper_sqlite_path を使用して本番 DB と分離します。環境設定に注意してください。
- .env は絶対に Git にコミットしないでください（config_setup のヘッダにも注意喚起を記載）。
- process priority / cpu affinity の設定は権限や OS に依存するため、失敗時はログ警告を出して安全にスキップします。
- PAPER_FILL_MODE の値は "instant" | "partial" | "never" | "reject" のいずれかである必要があります。無効値では ValueError を送出します。

---

今後の予定（例）
- research/factor_research の完全実装（ファクター計算の SQL 実装完了）。
- Strategy/Execution のユニットテスト強化、モックを用いた統合テスト追加。
- 単体銘柄ごとの lot_size をマスタ化し position_sizing の拡張。
- ログ出力に関するさらなる運用改善（クラウド向け送信など）。

もし特定の変更点をより詳しく分解したい、あるいは別バージョン向けに分割してほしい箇所があれば教えてください。