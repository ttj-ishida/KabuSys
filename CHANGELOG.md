# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

全てのリリースは Semantic Versioning に従います。

## [0.1.0] - 2026-04-19

初回公開リリース。

### 追加
- 実行／運用用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を利用することで本番 DB と完全に分離。
    - エンジンは別スレッドで実行され、data/stop_requested.flag により外部停止を検知して安全終了できる。
    - 実行時に PID ファイル (data/execution.pid など) を指定してプロセス管理可能。
    - RiskManager のデフォルト安全設定を組み込み（max_position_pct、max_utilization、rate_limit など）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用（監視データは一元化）。
    - data/stop_requested.flag によりループを終了。KeyboardInterrupt もハンドルして安全に DB をクローズ。

- 設定・環境管理
  - config.py: Settings クラスを実装。
    - .env 自動読み込み機能（プロジェクトルートの判定: .git または pyproject.toml を探索）。
    - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 必須/任意の環境変数をプロパティで提供（J-Quants / kabu API / DB パス / ログ設定 / 監視閾値等）。
    - Paper Trading 向けオプション: `paper_sqlite_path`, `paper_fill_mode`（有効値: "instant"、"partial"、"never"、"reject"）。
    - `is_live` / `is_paper` / `is_dev` 等のヘルパープロパティ。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 初期 .env 作成や既存 .env の更新を対話形式で支援。
    - 秘匿項目のマスク表示・選択肢・デフォルト値対応。
    - 保存前に確認を行い、.env を自動生成する。

- 設定検証ツール
  - validate_config.py: 起動前チェック CLI を追加。
    - 必須環境変数の有無、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML が存在する場合）を検証。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 本番（live）用の追加ガード（LINE 通知設定や Kill Switch 設定の警告）を実装。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py:
    - 統一的なログ設定ユーティリティを追加。
    - stdout へ StreamHandler、日次ローテーション（TimedRotatingFileHandler）でログファイル出力（デフォルト logs/<app_name>.log）、30日分保持。
    - LOG_DIR / LOG_LEVEL の環境変数や引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py:
    - プロセス優先度設定関数を追加（set_process_priority）。
    - Windows / POSIX (Linux, macOS 等) を吸収する実装。権限不足等は警告で無視。
    - CPU affinity 設定関数 set_cpu_affinity も提供。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコアでソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分を実装。スコア合計が 0 の場合は等分配へフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限のチェックと候補除外ロジックを実装（unknown セクターは除外しない）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知のレジームは 1.0 でフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: リスクベース / 等分配 / スコア配分に対応した株数算出ロジックを実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash に基づくスケーリング）、コストバッファの考慮、端数配分ロジックなどを実装。

- 解析・検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード DB を解析して検証レポートを出力する CLI を追加。
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、P95 レイテンシ等を算出し、閾値に基づき PASS/FAIL 判定を行う。
    - CLI 引数で期間指定 (--from/--to) と DB パス指定 (--db) に対応。
    - デフォルト DB パスは data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を使用。

- 研究用モジュール（プロトタイプ）
  - research/factor_research.py:
    - DuckDB を用いたファクター計算モジュール（Momentum / Value / Volatility / Liquidity）の骨子を追加（prices_daily / raw_financials を参照）。
    - 構成と計算方針、パラメータ定義を実装。関数インターフェースを用意（calc_momentum 等、実装継続中）。

- パッケージメタ
  - kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。

### 変更
- 監視・実行スクリプトの挙動
  - run_monitoring と run_execution の起動時にプロセス優先度を "high" に設定してから主要処理を開始するように統一。
  - 監視用 DB の初期化（init_monitoring_db）を起動時に行い、監視テーブルが存在することを保証（冪等）。

### 修正（設計上の注意・既知の制約）
- .env パーサーの実装
  - クォート付き値のバックスラッシュエスケープ処理、コメントの解釈ルール（クォートなしは '#' の直前が空白/タブの場合のみコメント扱い）など、現実的な .env フォーマットに対応。ただし極端なフォーマットは未検証。
- position_sizing の価格欠損時の挙動
  - open_prices に欠損（または 0.0）の場合はスキップする。将来的に前日終値や取得原価をフォールバックする拡張を検討。

### 既知の問題 / 今後の改善予定
- research/factor_research.py は実装途中（ファイル末尾が途中で切れている）。ファクター計算の完全実装とユニットテストの追加を予定。
- 単体テストや統合テストの追加、CI 設定は今後のタスク。
- 発注ロジックやブローカークライアント周りのエラーハンドリング、再試行ポリシー、監視アラート送信 (LINE) の実装強化予定。

---

このリリースは初期版のため機能が揃っている箇所と未完の箇所が混在します。運用・本番導入の際は validate_config による事前チェックを実行し、必要な環境変数（特に JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）や本番向けの設定を十分に確認してください。