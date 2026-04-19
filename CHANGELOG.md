# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。
バージョン番号はパッケージの __version__ に基づきます。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-19
初回公開リリース。日本株自動売買システム KabuSys の基盤的なスクリプト・ユーティリティ群を追加しました。

### Added
- 全体
  - パッケージ初期バージョンを定義しました（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - 環境変数/設定読み込みのための Settings クラスを追加（src/kabusys/config.py）。
    - .env 自動読み込み（プロジェクトルート検出、.env / .env.local の読み込み順をサポート）。
    - 必須値取得ヘルパー、各種パス・閾値・環境判定プロパティを提供。
    - PAPER_FILL_MODE の検証ロジックを実装（instant/partial/never/reject）。
- 起動スクリプト
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止は data/stop_requested.flag によるフラグ検知で行う。
    - 監視は環境に関わらず本番 sqlite_path を使用する挙動を明示。
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用の専用 SQLite を使用（data/paper_trading.db がデフォルト）。
    - BrokerClientFactory を経由してブローカークライアントを生成し、ExecutionEngine をスレッドで実行。停止フラグで安全終了。
    - PID ファイルパス、停止フラグの扱いを実装。
- 設定ユーティリティ / CLI
  - 対話式 .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - 複数の設定項目（環境、トークン、DB パス、ログレベル、Kill Switch 設定等）を対話的に生成・保存。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在とパース（PyYAML があれば）等を検査。
    - --strict オプションで警告を FAIL 扱いにする機能を提供。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights を実装。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（セクター上限の候補除外）、calc_regime_multiplier（bull/neutral/bear の乗数）を実装。
  - 株数決定・投下資金ロジック（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金とのスケーリング）、cost_buffer を考慮したスケールダウンロジックを実装。
  - portfolio パッケージエクスポートを追加（src/kabusys/portfolio/__init__.py）。
- ユーティリティ
  - ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - コンソール（stdout）出力と日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL 環境変数、引数による上書きに対応。既存ハンドラを上書きして二重登録を防止。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX を吸収し psutil を使って nice / priority を設定。失敗時は警告を出してスキップ。
    - set_cpu_affinity によるコア固定機能を提供。
- モニタリング DB 初期化フック（参照）
  - run_monitoring と run_execution で監視用テーブルの初期化（init_monitoring_db）を呼び出すように調整（冪等的に存在を保証）。
- ペーパートレード検証ツール
  - Paper Trading 向けの検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）、リスク却下数などを集計して PASS/FAIL 判定を行う。
    - 閾値はスクリプト内定義（稼働率 >=99%、成功率 >=90% など）。--from / --to / --db オプションをサポート。
- 研究用ファクター計算基盤（初期）
  - research/factor_research.py を追加（モメンタム等のファクター計算の基盤を定義）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する設計。モメンタム関連の定数が定義済み。

### Changed
- 起動スクリプトにおいてプロセス優先度を起動直後に「high」に設定するフローを統一（run_execution.py, run_monitoring.py）。
- run_execution は paper_trading 環境時に DB を分離する挙動を実装（settings.is_paper に依存）。

### Fixed
- .env パースの堅牢化（src/kabusys/config.py）:
  - export KEY=val 形式、引用符で囲まれた値内のバックスラッシュエスケープ、インラインコメント処理、クォートなし値のコメント扱い等に対応し、現実の .env の様々なフォーマットに耐えるように改善。
- logging_setup の挙動:
  - 既存ハンドラを明示的に閉じてから削除することで、複数回の初期化による二重ログ出力を防止。
  - ログディレクトリ作成失敗時にファイル出力をスキップしてコンソールのみで継続する安全処理を追加。
- process_priority と set_cpu_affinity は psutil が環境で制限されていても例外を吸収し、警告ログでフォールバックするように改善。

### Documentation / Messages
- 各スクリプト・モジュールに詳細なドキュメンテーション文字列（docstring）を追加。使用例、想定挙動、環境変数の説明等を含む。
- config_setup のウィザードで .env 保存前に確認画面を表示するインタラクティブフローを実装。

### Notes / TODO
- portfolio.position_sizing: price が欠損（0.0）の場合のフォールバック（前日終値や取得原価）について TODO コメントあり。将来的に銘柄別単元情報（lot_size）を拡張する余地あり。
- research.factor_research.py はファクター計算の基盤を用意しているが、一部実装（calc_momentum の続きなど）は追加実装が必要。
- 本リリースでは監視テーブル初期化の関数呼び出し箇所があるものの、監視テーブルのスキーマ定義・マイグレーション詳細は monitoring パッケージ内の実装に依存します。

---

配布物に含まれる主要ファイル一覧（概略）
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/config_setup.py
- src/kabusys/validate_config.py
- src/kabusys/run_monitoring.py
- src/kabusys/run_execution.py
- src/kabusys/portfolio/*
- src/kabusys/utils/*
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/research/factor_research.py

今後の予定:
- factor_research の完全実装（各ファクター計算ロジックの完成）。
- execution/monitoring の統合テスト、config YAML のテンプレート整備と生成スクリプト強化。
- 更なるエラーハンドリング強化とログ・メトリクスの充実。