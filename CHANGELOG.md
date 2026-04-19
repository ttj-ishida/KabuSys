# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
重要な変更は Breaking Changes として明記します。

## [Unreleased]

## [0.1.0] - 2026-04-19
初期リリース。日本株自動売買フレームワーク「KabuSys」の基盤機能を実装しました。主な追加点は以下の通りです。

### Added
- 全体
  - パッケージの初期バージョンを設定（src/kabusys/__init__.py の __version__ = "0.1.0"）。
  - DuckDB / SQLite を組み合わせたデータ処理・監視・分析基盤をサポート。
  - プロジェクトルート自動検出、.env 自動読み込み機構を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。(src/kabusys/config.py)
  - Settings クラスを実装し、環境変数をプロパティとして安全に取得可能に（各種 API トークン・DB パス・監視閾値・環境判定など）。(src/kabusys/config.py)

- 起動スクリプト / ランタイム
  - 実行エンジン起動スクリプトを追加（run_execution）。プロセス優先度設定、高優先度での実行、paper_trading 環境時の専用 DB を使用する仕組みを実装。停止フラグ・PID ファイルの扱いを実装。(src/kabusys/run_execution.py)
  - 監視ループ起動スクリプトを追加（run_monitoring）。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能、監視は環境に依存せず本番の sqlite_path を利用。停止フラグ検知でループ終了。(src/kabusys/run_monitoring.py)

- 設定周りのユーティリティ
  - 設定ウィザード CLI を追加（config_setup）。対話式で .env の作成・更新を支援し、既存値の読み込みやシークレット項目のマスク表示等をサポート。(src/kabusys/config_setup.py)
  - 設定検証 CLI を追加（validate_config）。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml 存在・パース（PyYAML があれば）などを検証。--strict オプションで警告を FAIL 扱いにできる。(src/kabusys/validate_config.py)

- ログ / プロセス制御
  - 統一ロギングセットアップユーティリティを追加（setup_logging）。コンソール（stdout）と日次ローテートファイル出力を設定、ログディレクトリ作成失敗時はファイル出力をフォールバック。LOG_LEVEL / LOG_DIR を尊重。(src/kabusys/utils/logging_setup.py)
  - プロセス優先度・CPU affinity 設定ユーティリティを実装（set_process_priority, set_cpu_affinity）。Windows / POSIX の差分を吸収し、権限不足や未対応 OS の場合は警告を出してスキップ。(src/kabusys/utils/process_priority.py)

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算モジュールを追加（portfolio.portfolio_builder）。
    - select_candidates: スコア降順で上位 N を選択。
    - calc_equal_weights, calc_score_weights: 等金額配分およびスコア加重配分（スコア全体が 0 の場合は等配分にフォールバック）。(src/kabusys/portfolio/portfolio_builder.py)
  - セクター集中制限・レジーム乗数を追加（portfolio.risk_adjustment）。
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合、新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じた資金乗数を返却（unknown はフォールバックで 1.0）。(src/kabusys/portfolio/risk_adjustment.py)
  - ポジションサイズ決定ロジックを追加（portfolio.position_sizing）。
    - allocation_method に応じた株数算出（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合はスケールダウン）をサポート。
    - cost_buffer による手数料・スリッページ見積の考慮と残余の配分ロジックを実装。(src/kabusys/portfolio/position_sizing.py)
  - portfolio パッケージの公開インターフェースを整備（src/kabusys/portfolio/__init__.py）。

- 研究・分析
  - ファクター計算（factor_research）モジュールを追加（duckdb を使った価格・財務データに基づくモメンタム等の計算設計を実装開始）。（実装はファイル末尾で継続中）(src/kabusys/research/factor_research.py)

- ペーパートレード検証
  - Paper Trading 検証レポート生成ツールを追加（tools/paper_verification_report.py）。
    - system_status、trade_logs、risk_logs などから稼働率・注文成功率・送信率・レイテンシを集計し、PASS/FAIL 判定を行う。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）をサポート。(src/kabusys/tools/paper_verification_report.py)

- DB 初期化
  - 監視用テーブルの初期化を保証する init_monitoring_db 呼び出しを実装（run_execution/run_monitoring 内）。(import: kabusys.monitoring.monitoring_db)

- Execution コンポーネントの組み立て（起動スクリプト内）
  - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てを run_execution に実装。RiskConfig のデフォルト値と initial_portfolio_value を broker.get_available_cash() で初期化する仕様を採用。

### Changed
- ログ出力
  - コンソールの標準出力先を stderr ではなく stdout に明示的に設定（cron/task 環境で stdout/stderr 統一リダイレクトしやすくするため）。(src/kabusys/utils/logging_setup.py)

### Fixed
- .env パーサーの堅牢化
  - export プレフィックス、クォート付き値のエスケープ、インラインコメントの処理などに対応した .env パーサーを実装。コメントや空行を正しく扱うよう改善。(src/kabusys/config.py, src/kabusys/config_setup.py)

### Security
- シークレット表示抑制
  - 設定ウィザードでトークン/パスワード等のシークレットはマスクして表示（表示時は "****"）。(src/kabusys/config_setup.py)

### Notes / Implementation details
- paper_trading 環境は本番 DB と完全分離（paper_trading 用 SQLite を使用）。(run_execution, Settings.paper_sqlite_path)
- 監視は KABUSYS_ENV に依らず production sqlite_path を使用する設計（run_monitoring）。
- run_* スクリプトは停止フラグ（data/stop_requested.flag）や PID ファイルを使って安全に起動/停止できる仕組みを提供。
- 一部モジュール（research/factor_research.py）は大枠を実装済みで、ファクター計算の細部は今後の追加実装で完了予定。

## Breaking Changes
- なし（初回リリース）

---

将来的な変更やバグ修正はこのファイルに追記していきます。新機能追加や API 変更があれば Breaking Changes セクションに明確に記載します。