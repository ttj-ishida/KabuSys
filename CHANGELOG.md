# Changelog

すべての重要な変更点をここに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

全般:
- セマンティックバージョニングに従います。
- リリース日はリポジトリ内の __version__ などを基にしています。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-17

初期リリース。主な追加点・仕様は以下の通りです。

### Added
- コアモジュールと CLI
  - Settings クラスによる環境変数ベースの設定管理を追加（src/kabusys/config.py）。
    - .env 自動ロード機能（プロジェクトルートを探索して .env / .env.local を読み込む）。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
    - 必須値チェックを行う _require ユーティリティ、各種設定プロパティ（DBパス、PIDファイルパス、しきい値など）を提供。
  - 対話式設定ウィザード: python -m kabusys.config_setup（src/kabusys/config_setup.py）
    - .env の初期作成・更新を対話的に実行、既存値の再利用やシークレットマスクをサポート。
  - 設定検証ツール: python -m kabusys.validate_config（src/kabusys/validate_config.py）
    - .env と config/*.yaml の存在・基本整合性チェック、--strict オプションで警告を FAIL 扱いにできる。
  - 実行スクリプト:
    - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db など）を使用し、本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成、ExecutionEngine の起動・停止ロジック（stop flag の検知、PID 管理）。
    - 監視ポーリングループ起動スクリプト: src/kabusys/run_monitoring.py
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値時にフォールバックして警告）。
      - 監視（monitoring）起動時は環境にかかわらず本番 sqlite_path を使用して監視 DB を初期化。
  - ツール:
    - Paper Trading 検証レポート生成: src/kabusys/tools/paper_verification_report.py
      - 稼働率、注文成功率、送信率、レイテンシ（P95 等）を集計して PASS/FAIL を判定。コマンドライン／環境変数で DB パス指定可能。
- ポートフォリオ関連（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights（スコア 0 の場合は等金額配分にフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（セクター別エクスポージャー計算と候補フィルタリング、"unknown" セクターは除外しない挙動）。
    - calc_regime_multiplier（bull/neutral/bear に対する乗数、未知レジーム時は 1.0 でフォールバック）。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes：risk_based / equal / score 方式に対応。lot_size 単位で丸め、aggregate cap によるスケールダウンと残余配分ロジックを実装。
- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - set_process_priority（Windows / POSIX を吸収、psutil を利用。権限不足時は警告してスキップ）。
    - set_cpu_affinity（最初の N コアにプロセスをピン固定。未対応環境や権限不足は警告してスキップ）。
- リサーチ / ファクター計算（一部）
  - Momentum / Volatility 等のファクター計算関数（src/kabusys/research/factor_research.py）
    - DuckDB 接続を受け取り prices_daily 等のテーブルからモメンタム（1M/3M/6M、MA200乖離）、ATR、出来高関連指標を計算する設計。
    - P95 やウィンドウ不足時の None 扱い等、堅牢な集計ロジックを採用。

### Changed
- （初期リリースのため無し）

### Fixed
- （初期リリースのため無し）

### Deprecated
- （初期リリースのため無し）

### Removed
- （初期リリースのため無し）

### Security
- （初期リリースのため無し）

補足メモ（実装上の重要ポイント）
- .env パースはクォート、エスケープ、export 形式、行末コメントなどを考慮した堅牢な実装を採用（src/kabusys/config.py）。
- Settings のプロパティは入力値検証を行い、不正値時は明確に例外を投げる（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。
- run_monitoring.py と run_execution.py は各種 stop/kill フラグ・PID ファイルを参照して安全に起動/停止するよう設計されている。
- Paper Trading の DB 分離や monitoring DB 初期化（init_monitoring_db）等、運用上の安全性を意識した実装。

---

注: ここに記載した内容は提供されたコードベースを解析して推測した「変更履歴（初期リリースの記録）」です。実際のコミット履歴やリリースノートが存在する場合はそれに従ってください。