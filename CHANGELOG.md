# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。

なお、本変更履歴は提示されたコードベースの内容から推測して作成したものであり、実際のコミット履歴ではありません。

## [Unreleased]

（現時点では未リリースの変更はありません）

---

## [0.1.0] - 2026-04-21

初回リリース。日本株自動売買システム「KabuSys」の基本機能群を実装しました。

### Added
- 全体
  - パッケージメタ情報にバージョンを追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - DuckDB / SQLite を用いたデータ格納・分析基盤の統合（Settings に DUCKDB_PATH / SQLITE_PATH の設定）。
  - プロジェクトルート検出ロジックを導入し、.env 自動読込（.env / .env.local）に対応（src/kabusys/config.py）。
  - 環境変数の柔軟なパース実装（クォート、エスケープ、export プレフィックス、インラインコメント処理に対応）（src/kabusys/config.py）。

- 実行スクリプト / デーモン管理
  - 監視用ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
    - 停止はプロジェクト内の `data/stop_requested.flag` ファイル検知で行う。
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、paper_trading 専用 DB（デフォルト `data/paper_trading.db`）に完全分離して記録。
    - PID ファイル管理・停止フラグ検知により安全に停止可能。

- 設定管理・CLI
  - 対話式環境設定ウィザードを追加（src/kabusys/config_setup.py）。
    - `.env` の初期作成・更新を補助。機密値はマスク表示。
  - 起動前設定検証ツールを追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、パス/ファイル存在チェック、YAML パース（PyYAML 利用時）、本番環境（live）向けガードなどを実行。
    - `--strict` モードで警告もエラー扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - コンソール出力（stdout）と日次ローテーションファイル出力（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX を抽象化し psutil 経由で優先度設定（high/normal/low）および CPU コア固定をサポート。
    - 権限不足や未対応 OS では警告を出して安全にスキップ。

- Execution / Risk / Order 管理（インテグレーション）
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager など実行系コンポーネントの組み立てと実行フローを実装（src/kabusys/run_execution.py から使用）。
  - RiskConfig のデフォルト値を設定。初期ポートフォリオ値はブローカーの利用可能現金から取得して初期化。

- 監視（Monitoring）
  - 監視 DB 初期化ヘルパー呼び出しを導入（init_monitoring_db を使用して監視テーブルの存在を保証）。
  - SystemMonitor クラスを起動して周期的に check_once() を実行するループを実装。

- ポートフォリオ構築・リスク調整・ポジションサイズ計算
  - 候補選定・重み計算を実装（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates（スコア降順 + タイブレーク）、calc_equal_weights、calc_score_weights（スコアが全て 0 の場合は等分配へフォールバック）。
  - セクター集中制限（apply_sector_cap）および市場レジーム乗数（calc_regime_multiplier）を実装（src/kabusys/portfolio/risk_adjustment.py）。
    - レジームに応じた投下資金乗数（bull/neutral/bear）を定義。未知レジームは警告を出して 1.0 でフォールバック。
    - セクター不明 ("unknown") は上限適用対象外とする挙動。
  - 株数決定ロジックを実装（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method に `risk_based` / `equal` / `score` をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウン）、残差を考慮した追加配分ロジックを実装。
    - cost_buffer による手数料/スリッページの保守的見積りを考慮。

- 解析・検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（avg/max/P95）などを算出して標準出力にレポート出力。
    - P95 計算、期間フィルタ（--from / --to）、DB パス引数/環境変数対応。
    - 判定基準（閾値）を定義して PASS/FAIL 判定を行う。

- 研究モジュール（WIP）
  - ファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity を想定した定数と関数インターフェースを準備。
    - DuckDB 接続を受ける設計で、prices_daily / raw_financials のみ参照する方針。

### Changed
- デザイン方針として、監視（monitoring）部分は環境設定に依らず本番用の sqlite_path を使用するよう明示（run_monitoring）。
- ロギング設定で stdout を使用するように統一（cron / Task Scheduler と相性向上）。
- .env ロード順を OS 環境変数 > .env.local > .env として明確化し、OS 環境変数を保護するための上書き禁止処理を実装（config.py）。

### Fixed
- 環境変数パースの堅牢化：
  - クォート内のバックスラッシュエスケープや対応する閉じクォート処理を実装。
  - export プレフィックスやインラインコメント（#）の扱いを改善（config._parse_env_line）。
- ログディレクトリ作成失敗時はファイルハンドラ作成をスキップし、コンソール出力のみで継続するようにして起動失敗リスクを低減（logging_setup）。

### Deprecated
- なし

### Removed
- なし

### Security
- 秘匿情報取り扱い：
  - 対話ウィザードや設定ファイル出力でシークレット値はマスク表示し、.env を Git にコミットしないようドキュメントで注意喚起（config_setup）。

---

注記 / 既知の制約・TODO
- research/factor_research.py は機能の骨格が実装されている一方で一部（calc_momentum の本体など）未完成の箇所が存在します。実際のファクター計算ロジックは追加実装が必要です。
- apply_sector_cap 内で price が欠損 (0.0) の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。前日終値等でのフォールバック実装が将来的に必要。
- position_sizing では lot_size を全銘柄共通で扱っているが、将来的に銘柄別単元対応への拡張を予定（TODO コメントあり）。
- process_priority の優先度設定は権限やプラットフォームに依存するため、権限不足時には警告でスキップされる。

もし、特定のモジュールやファイル単位でのより詳細な変更点（関数毎の変更や実装上の注意点）を反映したい場合は、対象ファイルを指定していただければ、より詳細な CHANGELOG エントリを追記します。