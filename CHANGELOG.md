# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
慣例: バージョンは package の __version__（現時点: 0.1.0）に対応しています。日付はリリース日です。

## [Unreleased]
- 既知の注意点 / TODO
  - portfolio/risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。将来的に前日終値や取得原価などのフォールバック価格を使う改善が予定されています。
  - research/factor_research.calc_momentum の実装が途中で切れている（ファイル末尾が不完全）。ファクター計算モジュールの残り実装が必要です。
  - 単元株（lot）や銘柄別 lot_map への拡張はコメントとして示されており、将来の改善候補です。

---

## [0.1.0] - 2026-04-23

### Added
- 基本機能の初期実装（初回公開相当）
  - 環境・設定管理
    - Settings クラスによる環境変数アクセスラッパーを実装。
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を起点）。
    - .env パーサ実装: export 形式対応、クォート内のバックスラッシュエスケープやインラインコメント処理、コメント/空行無視など堅牢なパース。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプションサポート。
    - paper_trading 用設定（PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE）やログ・監視しきい値等のキーを用意。
  - CLI / ユーティリティ
    - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加（秘密項目はマスク表示、保存前確認あり）。
    - validate_config.py: .env および config/*.yaml の検証ツールを追加。--strict モードで警告を失敗扱いにできる。
    - tools/paper_verification_report.py: ペーパートレード DB から稼働率・注文成功率・レイテンシ等を集計する検証レポートを実装。日付フィルタや DB パス上書き (--db / 環境変数) をサポート。
  - 実行 / 監視ランナー
    - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用し、本番 DB と分離。停止フラグ（data/stop_requested.flag）の検出、実行中 PID 管理、スレッドベースのエンジン実行をサポート。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL でポーリング間隔の上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する挙動を明示。
  - ポートフォリオ構築ロジック（純粋関数群）
    - portfolio.portfolio_builder:
      - select_candidates: スコア降順で候補選別（タイブレーク: signal_rank）。
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコア 0 の場合は等金額にフォールバック）。
    - portfolio.risk_adjustment:
      - apply_sector_cap: セクター集中上限チェック（売却予定銘柄除外対応、unknown セクターは除外対象外）。
      - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数。
    - portfolio.position_sizing:
      - calc_position_sizes: risk_based / equal / score の各配分方式を実装。lot_size（単元）丸め、per-stock 上限、aggregate cap（利用可能現金に対するスケールダウン）、cost_buffer（手数料・スリッページ見積り）、残差を考慮した追加配分ロジックを実装。
  - 実行コンポーネント骨格
    - run_execution から使用される ExecutionEngine/OrderManager/OrderRepository/Reconciler/RiskManager 等の組み立てロジック（EngineConfig, RiskConfig の利用）。
    - BrokerClientFactory によるブローカークライアント抽象化（paper_trading と実口座の分離を想定）。
  - DB / 分析
    - sqlite（監視/履歴）および DuckDB（分析）接続を利用する設計。init_monitoring_db を用いて監視テーブルの存在を保障する（冪等）。
  - ロギング / プロセス管理
    - utils.logging_setup.setup_logging: stdout ストリームハンドラと TimedRotatingFileHandler（日次ローテーション・30日保持）を組み合わせた統一ロギング設定。ログディレクトリ作成失敗時のフォールバック対応。
    - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定ユーティリティを実装。権限不足や未対応 OS の場合は警告を出してスキップ。

### Changed
- （初期リリースにつき該当なし）

### Fixed
- （初期リリースにつき該当なし）

### Removed
- （初期リリースにつき該当なし）

### Security
- 環境変数ファイル (.env) の生成時に「絶対に Git にコミットしないこと」を明示するヘッダを .env に書き込む。

---

注記:
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず settings.sqlite_path（本番用監視 DB）を使用する挙動に注意してください（設計上の意図として監視は環境の隔離を行わない）。
- PAPER_TRADING 環境では run_execution が paper_sqlite_path を使用することで発注履歴等を本番 DB と分離します。
- 一部モジュールに実装途中の箇所（research モジュール等）や将来改善を示す TODO コメントがあります。実運用前にそれらを確認してください。