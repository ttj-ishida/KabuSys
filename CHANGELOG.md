Changelog
=========

すべての変更は Keep a Changelog の形式に従っています。
リリースバージョン: Semantic Versioning を想定しています。

[Unreleased]
-------------

- （なし）

0.1.0 - 2026-04-20
-----------------

Added
- 実行・監視の起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを提供。プロセス優先度を高に設定し、BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動・停止制御を実装。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離してペーパートレードが行える設計。
    - 起動・停止のためのフラグファイルを利用（data/stop_requested.flag の検出で安全に停止）。
    - エンジンの PID ファイル出力（data/execution.pid）対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず production の sqlite_path（デフォルト: data/monitoring.db）を使用。
    - duckdb 接続も併用している。

- 設定管理・自動読み込み
  - config.py: .env の自動読み込み（プロジェクトルートの .env / .env.local）を実装。OS 環境変数の保護（既存値を上書きしない / .env.local は上書き可）や自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）に対応。
  - .env パーサーは export 文、クォート（シングル/ダブル）のエスケープ、行末コメントの取り扱いなどを考慮した堅牢な実装。
  - Settings クラスを提供し、各種環境変数（J-Quants / kabu API / DB パス / 監視閾値 / PAPER_FILL_MODE 等）をプロパティで取得。入力値のバリデーション（例: KABUSYS_ENV、PAPER_FILL_MODE、LOG_LEVEL）を行う。

- 設定支援ツール
  - config_setup.py: 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。秘密項目はマスク表示、入力キャンセルや既存値の再利用に対応。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数や KABUSYS_ENV、DB パス、config/*.yaml の存在や YAML パースをチェック（PyYAML 未インストール時は警告）。--strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 全起動スクリプトで共有するログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と 日次ローテート（TimedRotatingFileHandler）を組み合わせた標準構成を提供。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベル / ログディレクトリの解決順序を仕様化。
  - utils/process_priority.py: psutil を用いたクロスプラットフォームのプロセス優先度制御を追加（Windows の PriorityClass / POSIX の nice 対応）。CPU affinity を最初の N コアに固定するユーティリティも実装。失敗時は警告ログでスキップする堅牢性あり。

- ポートフォリオ構築・リスク調整・ポジションサイジング
  - portfolio/portfolio_builder.py: シグナル選別と重み計算（等分配・スコア加重）を実装。スコアが全て 0 の場合は等分配にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）および市場レジームに応じた乗数（calc_regime_multiplier）を提供。未知レジームに対するフォールバックと警告あり。
  - portfolio/position_sizing.py: 株数決定ロジックを実装（risk_based / equal / score の各方式）。
    - 損切り率・リスク率に基づくリスクベースのサイズ算出、最大ポジション比率・単元株（lot_size）丸め、コストバッファを考慮した aggregate cap（利用可能現金に応じたスケーリング）、残差に基づく追加配分ロジックなどを含む。

- ツール: Paper Trading 検証レポート
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95））を集計してレポート出力する CLI を追加。日付範囲フィルタと DB パスオプションをサポート。判定閾値（稼働率 99% 等）による PASS/FAIL 出力を行う。

- リサーチ基盤（ファクター計算）
  - research/factor_research.py: DuckDB を利用したファクター計算モジュールを追加（モメンタム・MA・ATR 等の計算設計方針と定数を実装開始）。（ファイル末尾で未完の箇所あり、以降の計算ロジックは継続実装予定）

Changed
- パッケージ初期化
  - kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。

Fixed
- （この初期リリースでは明確なバグ修正履歴は無し。実装時点での堅牢性（例: ファイル作成失敗時のフォールバック、psutil のエラー処理、.env パースの堅牢化など）に配慮）

Notes / その他
- 停止フラグ・Kill Switch
  - 停止フラグはプロジェクトルート配下の data/stop_requested.flag を用いる実装（run_monitoring/run_execution での検出・対応）。
  - Settings で kill_flag_path / kill_flag_clear_on_start 等の設定を提供しているため、運用時の Kill Switch 挙動は設定可能。

- DB の使い分け
  - 監視系（monitoring）は KABUSYS_ENV にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用する旨が明記されている一方、実行系は paper_trading モード時に専用 DB（paper_sqlite_path）を使って本番 DB と分離する設計。

- 将来の拡張点（コード内コメントより）
  - position_sizing: 銘柄別単元（lot_size）の導入や、価格欠損時のフォールバック価格採用などの改善余地が注記されている。
  - factor_research: DuckDB ベースの計算ロジックは継続実装が必要（ファイル末尾が途中で切れているため、完全実装は今後の作業）。

Security
- API シークレット等は .env に保存する設計。config_setup が .env を生成する旨を注意喚起（.env を Git にコミットしないことを README に追記することを推奨）。

---

注記:
- 本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。