# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の書式に従います。
安定版リリースが行われるまでは Unreleased に進行中の変更・注意点を記載します。

## [Unreleased]

- 研究モジュール（kabusys.research.factor_research）が途中で終端している箇所を確認。
  - ファイルの末尾で実装が途切れているため、factor 計算の一部が未完成。次版で完成予定。
- 既知の注意点:
  - 一部 TODO コメントあり（価格フォールバックや銘柄ごとの lot_size 拡張など）。
  - 実行時挙動は環境変数やファイルパスに依存するため、初回導入時は `python -m kabusys.config_setup` → `python -m kabusys.validate_config` による確認を推奨。

---

## [0.1.0] - 2026-04-25

初回公開リリース。自動売買システムのコア機能、ユーティリティ群、運用用スクリプト、およびポートフォリオ構築ロジックを含む。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。
  - パッケージ公開用のエクスポート (`__all__`) を定義。

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合、専用の Paper Trading 用 SQLite（既定: data/paper_trading.db）を使用。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立てと ExecutionEngine の起動を実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きをサポート（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。

- 設定・環境管理
  - config.py:
    - .env 自動読み込み（プロジェクトルートの検出: .git または pyproject.toml 基準）。
    - 柔軟な .env パーサ実装（export 形式・クォート・インラインコメント等に対応）。
    - Settings クラスで各種設定値（DB パス、API トークン、環境フラグ、しきい値等）を取得するユーティリティを提供。
    - PAPER_FILL_MODE の検証、paper_sqlite_path 等のプロパティを追加。
  - config_setup.py:
    - 対話式ウィザードで .env ファイルを初期作成・更新する CLI を追加。
    - 既存 .env の読み込み、シークレットマスク表示、確認プロンプト、.env 書き込みをサポート。
  - validate_config.py:
    - 起動前チェック用 CLI を追加（必須環境変数の確認、KABUSYS_ENV／LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml の有無とパース検証）。
    - `--strict` オプションで警告も失敗扱いにできる。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合のフォールバックログを追加。
  - portfolio/risk_adjustment.py:
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
    - 未知レジーム時のフォールバック（1.0）と警告ログ。
  - portfolio/position_sizing.py:
    - 各銘柄の発注株数を計算する calc_position_sizes を実装（allocation_method="risk_based"/"equal"/"score" をサポート）。
    - 単元株（lot_size）丸め、per-stock 上限・aggregate cap スケールダウン、残余配分アルゴリズムを実装。
    - cost_buffer による保守的なコスト見積りを導入。

- 運用ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出し PASS/FAIL 判定を行う。
    - デフォルト閾値を設定（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - DB の存在チェックや SQL の OperationalError を考慮した堅牢な実装。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - StreamHandler（stdout）と TimedRotatingFileHandler（ログ日次ローテーション、30日保持）をルートロガーに設定する共通関数 setup_logging を追加。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続するフォールバックを実装。
  - utils/process_priority.py:
    - Windows・POSIX でのプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。
    - アクセス拒否や未対応環境では警告を出して安全にスキップ。

- DB / 分析統合
  - duckdb 接続を Execution/Monitoring 両方で使用するように統合（Settings.duckdb_path）。

### 変更 (Changed)
- start-up の振る舞い
  - 起動スクリプトでプロセス優先度を起動直後に "high" に設定するように変更（set_process_priority("high") を追加）。
- .env 読み込みポリシー
  - 自動ロード順序: OS 環境 > .env.local > .env。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で抑制可能。
- ログ出力先の統一
  - StreamHandler は stdout を使用して、タスクスケジューラ等からのリダイレクトで扱いやすくした。

### 修正 (Fixed)
- 環境変数パースの堅牢化
  - export 形式、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いを改善して .env の柔軟な記述を許容。
- 停止制御の安全化
  - run_execution / run_monitoring で停止フラグ（data/stop_requested.flag）を監視し、正しくシャットダウン・停止処理を行うようにした。
- DB 初期化の冪等性
  - init_monitoring_db 呼び出しを追加して監視用テーブルが存在することを保証（存在しても安全に呼べるように設計）。

### 既知の問題 (Known Issues)
- research/factor_research.py が途中で実装途切れ（ファイル末尾の不完全な行あり）。factor 計算の一部が未実装のため、研究目的で使用する際は注意。
- 一部の機能は外部依存（psutil、duckdb、PyYAML など）により挙動が異なる:
  - PyYAML 未インストール時は config YAML の中身検証をスキップして警告を出力する。
  - psutil による優先度設定や CPU affinity は権限不足や未対応 OS でスキップされる。

---

開発者向けの補足:
- 初回導入手順の推奨:
  1. .env を作成: python -m kabusys.config_setup
  2. 設定検証: python -m kabusys.validate_config
  3. 必要な DB ディレクトリを作成（通常は scripts で自動作成されるが、手動で準備しても良い）
  4. 実行: python -m kabusys.run_monitoring / python -m kabusys.run_execution

もし CHANGELOG に追記してほしい点（例: リリース日を別にしたい、より詳細な変更箇所や責任者の記載など）があれば指示ください。