# Changelog

すべての重要な変更は Keep a Changelog の仕様に従って記載します。  
このファイルはコードベースの状態から推測して作成しています（実装やコミット履歴が存在しないため、機能・修正点をコードから読み取れる範囲でまとめています）。

全般的な注意
- バージョンはパッケージ定義（kabusys.__version__ = "0.1.0"）に合わせています。
- 日付は本ファイル作成日（2026-04-18）を使用しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-18
初回リリース。自動売買システム KabuSys の基本コンポーネントを実装。

### Added
- 環境設定・ローディング
  - .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml で検出）。環境変数は OS 環境 > .env.local > .env の優先度で読み込まれる。
  - 強力な .env パーサを追加（export 付き、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - Settings クラスを追加し、アプリケーション構成値を属性として取得できるようにした（J-Quants / kabuステーション / DB パス /監視閾値 /各種フラグ等）。
  - PAPER_FILL_MODE など入力値のバリデーションを実施（無効値は例外）。

- 設定関連 CLI
  - config_setup: 対話式ウィザードで .env を生成・更新する CLI を追加（項目定義、既存値の読み込み、シークレット扱い、保存の確認など）。
  - validate_config: 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在・パース（PyYAML があれば内容検証）や本番環境向けガードをチェック。--strict モードをサポート（警告を FAIL 扱い）。

- 実行コンポーネント起動スクリプト
  - run_execution: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite DB（data/paper_trading.db、環境変数で上書き可）を使用し、本番 DB と分離。
    - BrokerClientFactory の利用による本番/モック切替を組み込んだブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine 起動。PID ファイルおよび停止フラグ(stop_requested.flag)による安全停止処理を実装。
    - RiskManager の既定パラメータを設定（最大ポジション割合、利用率、レート制限、サーキットブレーカー等）。initial_portfolio_value を broker.get_available_cash() から取得して初期化。

  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値はデフォルトにフォールバックして警告を出力。
    - 監視は常に（環境にかかわらず）本番用 sqlite_path を使用する仕様。
    - stop_requested.flag の検出による安全なループ終了、KeyboardInterrupt のハンドリング、例外発生時のログ出力と次ポーリング継続処理を実装。

- 監視 DB 初期化
  - init_monitoring_db を参照する形で、起動時に監視テーブルが存在することを保証（冪等に実行）。

- ロギング・プロセス制御ユーティリティ
  - setup_logging: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する共通ユーティリティを追加。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - set_process_priority / set_cpu_affinity: psutil を用いてクロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティを追加。Windows/Linux/Mac（POSIX）の差分を吸収し、権限不足など失敗した場合は警告を出して処理をスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: 候補選定（スコア降順・タイブレーク）、等額配分、スコア加重配分（全スコアが 0 の場合に等配分へフォールバック）を実装。
  - risk_adjustment: セクター集中上限を適用する apply_sector_cap、マーケットレジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear の既定値）を実装。未知レジームは警告を出して 1.0 にフォールバック。
  - position_sizing: 各銘柄の発注株数計算を実装（risk_based / equal / score の allocation_method に対応）、単位株（lot_size）丸め、per-position 上限・aggregate cap（利用可能現金に対するスケーリング）、cost_buffer（手数料・スリッページ見積り）考慮、残余現金を使ったロット単位での追加配分ロジックを実装。

- リサーチ機能（骨子）
  - research/factor_research: DuckDB を用いたファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity の設計とモメンタム計算関数の骨組み）。DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみを参照する設計。

- ツール
  - tools/paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）を計算してレポート出力。
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を用いた PASS/FAIL 判定を実装。
    - コマンドラインで期間指定（--from / --to）や DB パス指定（--db）をサポート。DB が存在しない場合は明示的にエラー表示。

### Changed
- 初回リリースのため該当なし（ベース実装として導入された項目を列挙）。

### Fixed
- 多くの入力/運用上の edge case をハンドリング:
  - .env のクォート内でのバックスラッシュエスケープ、インラインコメントの扱いを正しく処理することで、秘密値や複雑な値の読み込みを安定化。
  - MONITOR_POLL_INTERVAL の負値や非整数入力に対するフォールバックと警告を実装。
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時のフォールバック（コンソール出力のみ）を実装して起動失敗を回避。
  - プロセス優先度や CPU affinity の設定で権限不足や未対応 OS の場合に警告してスキップ。

### Security
- .env を生成する際に注意喚起を挿入（.env を Git にコミットしないよう明記）し、対話式ウィザードでシークレット項目はマスク表示するように実装。

### Notes / Implementation details
- run_execution は paper_trading モードで本番用 DB と完全分離するように設計（paper_sqlite_path を使用）。これによりテスト/検証と本番データの混在を防止。
- run_monitoring は監視データを本番 sqlite_path に記録する設計になっている（監視は環境に依存しない運用が想定されるため）。
- ExecutionEngine や SystemMonitor、各種ブローカー実装（MockBrokerClient 等）、監視 DB 初期化関数の詳細実装は別モジュールに分離されており、起動スクリプトはそれらを組み合わせるオーケストレーションを担う。
- DuckDB は分析・ファクター計算用に採用されている（duckdb_path が設定可能）。

---

以上。コードの実装内容に基づいて機能・修正点を整理しました。必要であれば、ファイル単位での変更履歴（より詳細な説明や想定される使用例、既知の制約）を追加します。