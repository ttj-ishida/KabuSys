# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
安定版リリースのバージョニングは semver に準拠します。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-18
最初の公開リリース。シンプルな自動売買基盤のコア機能、設定管理、実行・監視ランタイム、ポートフォリオ構成ロジック、ユーティリティ群、および運用支援ツールを実装。

### Added
- コアパッケージ
  - パッケージのメタ情報を追加（`kabusys.__version__ = "0.1.0"`）。

- 設定管理
  - Settings クラス（`kabusys.config`）を実装。環境変数経由で各種設定値（J-Quants / kabu API / DBパス /監視閾値 /実行環境など）を取得するプロパティ群を提供。
  - .env 自動読み込み機能を追加（プロジェクトルートを .git / pyproject.toml で検出し、`.env` と `.env.local` を読み込む。OS 環境変数は保護）。
  - .env パースロジックを充実（export プレフィックス対応、クォート内エスケープ、インラインコメント処理等）。

- 設定ユーティリティ（CLI）
  - 対話式設定ウィザード（`kabusys.config_setup`）を追加。`.env` の作成・更新を支援。シークレットのマスク表示、選択肢・デフォルト対応あり。
  - 設定検証ツール（`kabusys.validate_config`）を追加。必須環境変数・KABUSYS_ENV の妥当性・DB パス存在（親ディレクトリ）・config/*.yaml の存在とパース（PyYAML インストール時）・本番向けガードなどをチェック。`--strict` フラグで警告を失敗扱いにできる。

- 実行・監視ランタイム
  - Execution エンジン起動スクリプト（`kabusys.run_execution`）
    - Paper Trading 環境では paper 用の SQLite（`PAPER_TRADING_SQLITE_PATH` / `data/paper_trading.db`）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory を利用してブローカークライアントを作成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をデーモンスレッドで起動。停止フラグ（data/stop_requested.flag）や PID ファイルの扱いを実装。
  - Monitoring 起動スクリプト（`kabusys.run_monitoring`）
    - 環境（KABUSYS_ENV）に依らず監視は本番 sqlite_path を使用する設計。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（不正値時はデフォルト 60 秒へフォールバック）。
    - SystemMonitor の単発チェック `check_once()` を定期実行し、例外時はログへ出力して次回に継続。

- データベース・分析
  - DuckDB と SQLite の両方に接続する仕組みを実装（`Settings.duckdb_path`, `Settings.sqlite_path`）。
  - 監視用テーブルの初期化保障用ユーティリティ（`init_monitoring_db` の利用場所を各起動スクリプトで呼び出し、冪等にテーブル存在を保証）。

- ロギング・プロセス制御
  - 統一ロギング設定ユーティリティ（`kabusys.utils.logging_setup.setup_logging`）
    - stdout へ StreamHandler、日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーへ設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - ログレベル決定順（引数 > 環境変数 LOG_LEVEL > デフォルト）。
  - プロセス優先度・CPU affinity ユーティリティ（`kabusys.utils.process_priority`）
    - Windows/Linux/macOS に対応した優先度設定（`set_process_priority`）と、最初 N コアに固定する `set_cpu_affinity`。権限不足や未対応 OS の場合は警告を出して安全にフォールバック。

- ポートフォリオ構築
  - 銘柄選定・重み計算（`kabusys.portfolio.portfolio_builder`）
    - select_candidates: スコア降順で上位 N を選抜（同点時に signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分。全銘柄スコアが 0 の場合は等金額にフォールバックして警告。
  - セクター集中制限とレジーム乗数（`kabusys.portfolio.risk_adjustment`）
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、新規候補を除外（"unknown" セクターは適用除外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear のマップと未知レジームのフォールバック）。
  - 株数決定・リスク制限（`kabusys.portfolio.position_sizing`）
    - risk_based / equal / score の allocation 方法をサポート。lot_size（単元）丸め、1銘柄上限、aggregate cap（利用可能現金に対するスケーリング）、cost_buffer（手数料・スリッページの保守見積り）を考慮したスケールダウンロジックを実装。

- 解析・研究
  - ファクター計算モジュール（`kabusys.research.factor_research`）の骨格を追加。DuckDB を受け取り prices_daily / raw_financials を用いてモメンタム／ボラティリティ等を計算する設計（実装は部分的）。

- 運用ツール
  - Paper Trading 検証レポート生成ツール（`kabusys.tools.paper_verification_report`）
    - SQLite（paper_trading DB）から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計し、閾値に基づく PASS/FAIL 判定を表示。
    - P95 の計算、期間フィルタ（--from/--to）、DB が存在しない場合の友好的なエラーメッセージを実装。
    - デフォルト閾値（稼働率 99%、成功率 90% など）を定義。

### Changed
- 起動順序と安全確保
  - 監視/実行スクリプトでプロセス優先度を起動直後に "high" に設定するように統一して呼び出し（`set_process_priority("high")`）。権限不足時は警告のみで続行。

- DB パス挙動の明示
  - Monitoring は環境にかかわらず本番の sqlite_path を参照する設計として明文化（監視データは本番 DB で一元管理する意図）。

### Fixed
- 環境変数パースの堅牢化
  - .env パーサでクォート内のエスケープや export プレフィックス、コメント位置の扱いを改善し、実運用での多様な .env 形式に対応。

### Security
- シークレット管理
  - config_setup の対話でシークレット項目（J-Quants トークン、kabu API パスワード）をマスク表示する UX を採用。`.env` を誤ってコミットしないよう注意喚起を出力。

### Notes
- 仕様上の重要点
  - Paper Trading と Live は DB を分離（paper_trading 用 DB を使用）することで、本番データとの完全分離を確保。
  - 監視ループは stop フラグ（data/stop_requested.flag）と KeyboardInterrupt による安全停止をサポート。
  - Logging は標準出力（stdout）を使用するため、タスクスケジューラや cron でのリダイレクト運用に適した設計。

---

開発中・改善予定の点（今後のリリース候補）
- factor_research の各ファクター計算の完成、ユニットテスト充実。
- 銘柄別の lot_size マスタ対応（position_sizing の拡張）。
- モニタリングや ExecutionEngine のより詳細なメトリクス収集・アラート連携（LINE 通知等）の実装強化。
- より詳細なドキュメント（API 仕様、運用手順、設定例）の整備。

--- 

作成: 自動生成（コードベースの解析に基づいて推測）