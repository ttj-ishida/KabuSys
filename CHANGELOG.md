# Changelog

すべての正常性のために: このファイルは Keep a Changelog の規約に沿って作成されています。
変更履歴は主にコードベースから推測して記載したため、実際のコミット単位や作者コメントとは差異がある場合があります。

注: 現在のパッケージバージョンは src/kabusys/__init__.py に従って 0.1.0 です。

## [Unreleased]

- 細かなログ/警告メッセージやエラーハンドリングの改善（ログ出力の保守性向上、ファイルハンドラ作成失敗時のフォールバックなど）。
- process_priority / CPU affinity 設定で非対応 OS の扱いと例外時の警告を追加。
- その他実行時の安全停止フラグ検知ロジック周りの堅牢性向上。

## [0.1.0] - 2026-04-19

Added
- 実行/監視用エントリスクリプトを追加
  - run_execution.py
    - ExecutionEngine の起動スクリプト。起動時にプロセス優先度を設定し、Engine をスレッドで実行。
    - 停止は data/stop_requested.flag で検知して安全に停止可能。
    - ペーパートレード時は専用の SQLite（data/paper_trading.db）へ完全分離して記録する。
    - 起動時に停止フラグが立っている場合は起動をスキップする挙動を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了する。

- 設定管理・セットアップ・検証用 CLI を追加
  - config.py
    - .env 自動ロード（プロジェクトルート検出: .git or pyproject.toml 基準）。
    - 環境変数取得用 Settings クラスを提供（J-Quants / kabu API / DB パス / 監視閾値など）。
    - 環境変数の必須チェックや値検証ロジックを実装（KABUSYS_ENV, LOG_LEVEL 等）。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等のペーパートレード用設定を追加。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加（python -m kabusys.config_setup）。
    - 秘匿値はマスク表示、既存 .env の読み込み・デフォルト利用に対応。
  - validate_config.py
    - .env と config/*.yaml の起動前チェック用 CLI を追加（python -m kabusys.validate_config）。
    - --strict オプションで警告を失敗扱いにできる。
    - PyYAML が無い場合は YAML 検証をスキップして警告を出力。

- ポートフォリオ構築関連モジュールを追加（純粋関数群、DB参照なし）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額・スコア加重の重み計算（calc_equal_weights, calc_score_weights）。
    - スコア合計が 0 の場合のフォールバック（等割合）と警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）。未定義レジームは警告して 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - 各種配分方式対応（risk_based, equal, score）による発注株数計算。
    - 単元株（lot_size）丸め、ポジション上限・アグリゲート上限、コストバッファを考慮したスケーリング実装。
    - cash が不足する場合のスケールダウンと端数処理ロジックを実装。

- ログ・プロセス管理ユーティリティを追加
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日）を設定。
    - LOG_DIR の作成に失敗した場合はファイル出力をスキップしてコンソール出力のみにフォールバック。
    - ログレベル解決順 (引数 > 環境変数 > デフォルト) を実装。
  - utils/process_priority.py
    - psutil を用いて Windows と POSIX 系（Linux, macOS, FreeBSD）でプロセス優先度（nice/HIGH_PRIORITY_CLASS）を統一的に設定。
    - CPU affinity 設定関数 set_cpu_affinity() を提供。アクセス拒否等は警告でスキップ。

- Paper Trading 検証用ツールを追加
  - tools/paper_verification_report.py
    - ペーパートレード DB（デフォルト: data/paper_trading.db）を集計して検証レポートを生成。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定（閾値はソース内定義）。
    - CLI から期間指定 (--from, --to) と DB パス指定 (--db) に対応。

- 研究用ファクター計算モジュールを追加（research/factor_research.py）
  - DuckDB を用いたモメンタム・ボラティリティ・バリュー等のファクター計算基盤を追加（prices_daily / raw_financials テーブル参照）。
  - 設計方針・定数（期間）をドキュメント化。

Changed
- Execution / Monitoring の DB 接続動作
  - run_monitoring は環境（KABUSYS_ENV）にかかわらず production 用 sqlite_path を使用して監視データを記録する設計。
  - run_execution は KABUSYS_ENV=paper_trading 時に paper_sqlite_path（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。

- ログ出力の標準化
  - すべての起動スクリプトから共通の setup_logging を呼び出すようにしてログ設定を統一。

- .env 自動ロードの振る舞い
  - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env.local は既存 OS 環境変数を保護しつつ上書き可能。

Fixed
- 環境変数パースの堅牢化
  - quote/エスケープ処理、インラインコメント（#）の取り扱い、export KEY=val 形式への対応を実装。
- ポーリング間隔の不正値対応
  - MONITOR_POLL_INTERVAL が整数以外、または 0 以下の場合にデフォルト（60秒）にフォールバックして警告を出すよう修正。
- DB 初期化の冪等性
  - init_monitoring_db() を実行して監視テーブルの存在を保証（既存 DB に対しても安全）。

Security
- 秘匿値の取り扱い
  - config_setup の対話でシークレット項目はマスク表示、.env ファイル生成時に .env をコミットしない旨の注意書きを追加。

Migration notes / 備考
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - KABUSYS_ENV の有効値: development / paper_trading / live
  - PAPER_FILL_MODE の有効値: instant / partial / never / reject
  - MONITOR_POLL_INTERVAL を使って監視ポーリング間隔を変更可能（秒単位）
  - PAPER_TRADING_SQLITE_PATH でペーパートレード DB パスを上書き可能
- 起動方法（例）:
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

参考: 今後の改善候補（コード中 TODO）
- position_sizing: 銘柄別の単元株数（lot_size）を stocks マスタへ持たせるなどの拡張。
- risk_adjustment: price 欠損時のフォールバック価格（前日終値や取得原価）の導入。
- research/factor_research: ファクター計算の完全実装とドキュメント整備。
- ロギング: ファイルハンドラ作成失敗時の詳細復旧手順整備。

---

この CHANGELOG は現行ソースコードの内容から推測して作成しています。差分の正確な履歴は Git のコミットログを参照してください。