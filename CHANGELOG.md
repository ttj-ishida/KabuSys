# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現時点では未リリースの作業なし）

---

## [0.1.0] - 2026-04-19

初回公開リリース。日本株自動売買システム「KabuSys」の基本機能を構成する以下のモジュールと CLI / ユーティリティ群を実装しました。

### Added
- 基本パッケージ構造とバージョン情報
  - src/kabusys/__init__.py にてバージョンを "0.1.0" として定義。

- 環境設定管理
  - src/kabusys/config.py
    - プロジェクトルート検出（.git または pyproject.toml を基準）に基づく .env 自動ロード。
    - .env / .env.local の読み込みロジック（OS 環境変数の保護、上書きルール）。
    - .env の行パーサーを実装（export プレフィックス、クォート、エスケープ、インラインコメント対応）。
    - Settings クラスでアプリケーション設定の取得とバリデーションを提供（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。
    - デフォルトファイルパス（DuckDB / SQLite / paper_trading DB 等）を提供。

- 設定ウィザード / 検証 CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - 秘匿項目のマスク表示、選択肢・デフォルトの取扱いをサポート。
  - src/kabusys/validate_config.py
    - 起動前検証 CLI。必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在・パース確認、live 環境向けの追加ガード等を実行。
    - --strict オプションで警告を失敗扱いにできる。

- 起動スクリプト（実行系 / 監視系）
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動用スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を経由したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 等の組み立て、デーモンスレッドでの実行と停止フラグ監視実装。
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境に関わらず本番 sqlite_path を使用する挙動を明示。

- 監視 DB 初期化・監視ロジック基盤（参照）
  - monitoring モジュール向けの DB 初期化フックが呼ばれるように統合（init_monitoring_db を利用）。

- ロギング・プロセス制御ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - ルートロガーの統一設定関数を提供。StreamHandler は stdout、TimedRotatingFileHandler による日次ローテーション（30日保持）を実装。ログディレクトリ作成失敗時はファイル出力を抑止してコンソール出力のみで継続するフェールセーフ付き。
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX の差分を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティ。権限不足や未対応プラットフォーム時にはワーニングを出して安全にスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額・スコア重み計算（calc_equal_weights, calc_score_weights）。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - src/kabusys/portfolio/position_sizing.py
    - 各銘柄の発注株数決定ロジック（risk_based, equal, score の allocation_method をサポート）、単元株丸め、aggregate cap によるスケーリング、コストバッファによる保守的見積もり。
  - src/kabusys/portfolio/__init__.py
    - 上記機能を公開するパッケージ初期化。

- リサーチ（ファクター計算）基盤
  - src/kabusys/research/factor_research.py
    - DuckDB を利用したファクター計算の設計と一部実装（モメンタム等の計算方針、定数定義）。（モジュールは DuckDB の prices_daily / raw_financials に依存）

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレードの SQLite ログを集計してレポート出力（稼働率、注文成功率、送信率、レイテンシ指標 P95 等）。
    - 閾値に基づく PASS/FAIL 判定、DB ファイルが存在しない場合のエラーメッセージ、日付フィルタ対応（--from / --to / --db）。

### Changed
- ログ出力周りの運用方針を統一
  - stdout を標準出力に使うことで cron / タスクスケジューラ等でのログリダイレクト運用を想定。

- 環境変数の自動ロード順序と保護ポリシー
  - OS 環境変数 > .env.local > .env の優先順で読み込み、OS 環境変数は保護され上書きされないように実装。

### Fixed / Hardening
- .env パーサーの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いを明示的に実装。誤った .env 行の無視や警告発生を防止。

- 起動スクリプトの耐障害性向上
  - run_monitoring.run() での check_once() の例外をキャッチしてログ出力後にポーリング継続する設計。
  - MONITOR_POLL_INTERVAL の不正値に対する警告とデフォルトフォールバックの実装。
  - run_execution で停止フラグを検知した場合に起動を抑止／安全停止するフローを追加。

- DB 初期化の冪等性確保
  - Execution 起動時に監視テーブルの存在を保証するため init_monitoring_db を呼び出す（paper_trading DB と本番 DB の分離を維持）。

- 設定検証の柔軟性
  - validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告を出す。config/*.yaml の欠如は警告として通知。

- Paper Trading レポートの統計処理改善
  - P95 の計算、latency_ms が NULL の扱い、データ欠損時の安全なデフォルトの導入。

### Security
- .env ファイルに関する注意喚起を config_setup に明記（.env を Git に絶対にコミットしない旨）。

---

今後の予定（例）
- ExecutionEngine / SystemMonitor 等の詳細実装の追加テスト・ドキュメント化
- factor_research の完全実装（ファクター群の SQL 実装と正規化ユーティリティ統合）
- 単体テスト、CI/CD 設定、デプロイ手順の整備

---

注: 本 CHANGELOG は、提供されたソースコードの内容から実装された機能・改善点を推測して作成しています。実際のコミット履歴やリリース履歴に基づくものではありません。