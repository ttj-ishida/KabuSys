# Changelog

すべての変更は「Keep a Changelog」形式に準拠して記載しています。  
当リポジトリの初回リリースとして推定される機能追加や挙動を、ソースコードから推測してまとめました。

## [0.1.0] - 2026-04-23

### 追加
- 基本バージョン番号を設定
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 実行用エントリスクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続、ブローカークライアント生成、OrderManager/RiskManager/Reconciler の組み立て、スレッドでのエンジン実行、停止フラグ（data/stop_requested.flag）検知を実装。paper_trading 環境では paper 専用 DB（data/paper_trading.db）を使用。
    - ファイル: src/kabusys/run_execution.py

  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）、停止フラグ検知、例外ハンドリング、sqlite/duckdb 接続、監視 DB の初期化を実施。
    - ファイル: src/kabusys/run_monitoring.py

- 環境設定管理
  - Settings クラス: .env 自動読み込み（プロジェクトルート探索）、各種環境変数のラッパーを提供。paper_trading 用 DB パス、PAPER_FILL_MODE バリデーション、監視しきい値（CPU/MEM/DISK）や PID / kill flag パスなどを含む。
    - ファイル: src/kabusys/config.py

  - .env ウィザード CLI: 対話形式で .env を生成・更新するツールを追加。既存値の読み込み、シークレットマスク、保存確認等を実装。
    - ファイル: src/kabusys/config_setup.py

  - 設定検証 CLI: 必須環境変数・KABUSYS_ENV 値・LOG_LEVEL・DB パス・config/*.yaml の存在とパース（PyYAML がある場合）・本番用ガード等の検証を行うツールを追加。--strict オプションで警告を失敗扱いにできる。
    - ファイル: src/kabusys/validate_config.py

  - .env パーサー: export 形式やクォート内のエスケープ、行内コメントの扱いなどを考慮した堅牢な .env 読み込みロジックを実装。
    - ファイル: src/kabusys/config.py（内部関数）

- ロギング・プロセスユーティリティ
  - 統一ログ設定ユーティリティ setup_logging を追加。コンソール (stdout) と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定、ログディレクトリ自動作成・フォールバックを提供。
    - ファイル: src/kabusys/utils/logging_setup.py

  - プロセス優先度 / CPU affinity 設定ユーティリティを追加。Windows/Linux/macOS に対応（psutil 利用）、例外時は警告ログでスキップする設計。
    - ファイル: src/kabusys/utils/process_priority.py

- ポートフォリオ構築関連（純粋関数群）
  - 候補選定と重み計算: select_candidates / calc_equal_weights / calc_score_weights を追加。スコアが全て 0 の場合のフォールバック挙動を実装。
    - ファイル: src/kabusys/portfolio/portfolio_builder.py

  - セクター集中度制御・レジーム乗数: apply_sector_cap（売却予定銘柄の除外、unknown セクター除外ルール）と calc_regime_multiplier（bull/neutral/bear の乗数）を追加。未知レジーム時はフォールバック。
    - ファイル: src/kabusys/portfolio/risk_adjustment.py

  - ポジションサイジング: calc_position_sizes を追加。allocation_method による risk_based / equal / score の対応、損切りベースのリスク算出、単元株（lot_size）での丸め、aggregate cap によるスケールダウンと端数処理（残差優先度に基づく追加配分）、cost_buffer による保守的コスト見積りを実装。
    - ファイル: src/kabusys/portfolio/position_sizing.py

  - ポートフォリオモジュールのエクスポートを整理。
    - ファイル: src/kabusys/portfolio/__init__.py

- Paper Trading 検証ツール
  - paper_verification_report: ペーパートレード用 SQLite DB を読み、稼働率（uptime）、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計し PASS/FAIL 判定するレポート生成スクリプトを追加。P95 計算、期間フィルタ、閾値定義を含む。
    - ファイル: src/kabusys/tools/paper_verification_report.py

- 研究用ファクターモジュール（骨格）
  - factor_research: モメンタム等のファクター計算に関する骨格と定数を追加（DuckDB 接続を想定）。（実装途中の箇所あり）
    - ファイル: src/kabusys/research/factor_research.py

- データベース初期化ヘルパー呼び出し
  - 監視 DB の初期化 (init_monitoring_db) を起動スクリプト群で呼び出し、テーブル存在を保証（冪等）。DuckDB との併用を想定。

### 変更（設計上の決定）
- 本番 / ペーパー DB 分離ポリシー
  - 監視系（run_monitoring）は実行環境にかかわらず本番 sqlite_path を使用する設計を採用。一方、実行系（run_execution）は KABUSYS_ENV=paper_trading の場合に専用の paper_sqlite_path を使用することで本番 DB と完全分離を行う。

- ログ出力先と挙動
  - StreamHandler は stdout を使用（cron/Task Scheduler からのリダイレクトを考慮）。ログファイルは logs/<app_name>.log に日次ローテーションで出力（30 日保持）。

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を自動ロード。OS 環境変数を保護するための上書きポリシーを実装（.env.local は override=true だが OS 環境変数は上書きされない）。

### 修正（既知の安全策 / フォールバック実装）
- 環境変数パースの堅牢化
  - クォート内のバックスラッシュエスケープや inline コメント処理などを実装し、一般的な .env の落とし穴に対処。
  - 無効値や不足時は明示的エラー／警告を出す（validate_config で検出可能）。

- process_priority / cpu_affinity の安全な実行
  - 権限不足や未対応プラットフォームでの呼び出しは警告ログで安全にスキップするよう変更。

- ポジションサイジングの保守的計算
  - 価格欠損（0 や None）や lot 単位での丸めにより過剰な発注を避ける設計。aggregate cap を超えた場合に再スケーリング・残余配分を行う。

### 既知の制限 / TODO
- factor_research モジュール内で未完の実装が存在（ファイル末尾で途中）。
- price 欠損時のフォールバック（前日終値やマスタ）に関する改善案がコメントで残っている（risk_adjustment）。
- 将来的な拡張として銘柄ごとの lot_size を受け取る設計への変更を想定（position_sizing の TODO）。

---

今後のリリースでは、factor の完全実装、ExecutionEngine や SystemMonitor のユニットテスト・統合テスト、Paper Trading の検証パイプライン強化、設定検証の拡張（より厳密な YAML スキーマ検証など）を予定すると良いでしょう。