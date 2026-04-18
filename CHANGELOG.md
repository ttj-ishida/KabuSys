# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
SemVer を採用しています。なお以下の内容はコードベースの実装から推測してまとめたもので、実際のコミット履歴ではありません。

## [Unreleased]
- 追加・改善
  - なし（現状は 0.1.0 を初期リリースとして記載）

## [0.1.0] - 2026-04-18
初期リリース。日本株自動売買システム「KabuSys」の基本機能を実装。

- Added
  - 起動スクリプト
    - run_execution.py
      - ExecutionEngine を起動するエントリポイント。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db、環境変数で上書き可）を使用する分離設計。
      - ブローカークライアント生成（BrokerClientFactory）および OrderManager / RiskManager / Reconciler の組み立て。
      - スレッドでエンジンを実行し、data/stop_requested.flag による安全な停止処理を実装。
      - 実行中の PID を data/execution.pid に保存する仕組みを想定。
    - run_monitoring.py
      - SystemMonitor のポーリングループを起動するエントリポイント。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - stop flag（data/stop_requested.flag）検知でループを終了。
      - 監視用 DB は環境に関わらず本番 sqlite_path を使用する（監視の独立性を確保）。
  - 設定管理
    - config.py
      - .env 自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
      - .env/.env.local の読み込み順と上書きルール（OS 環境変数保護）。
      - export KEY=val 形式やクォート・エスケープ、インラインコメントを考慮した堅牢な .env パーサを実装。
      - Settings クラスで各種設定値をプロパティとして提供（DB パス、Paper Trading 関連、監視しきい値、ログレベル等）。
      - PAPER_FILL_MODE の検証や KABUSYS_ENV の許容値チェックを実装。
  - 設定ユーティリティ / CLI
    - config_setup.py
      - .env の対話式ウィザードで初期作成・更新を支援。
      - シークレット項目のマスク表示、選択肢サポート、既存値の再利用機能などを提供。
    - validate_config.py
      - .env および config/*.yaml の起動前検証ツール。
      - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスと YAML ファイルの存在チェック。
      - --strict オプションで警告を失敗扱いにするモードを提供。
      - PyYAML の有無に応じて YAML 検証をスキップする柔軟性を持たせている。
  - ロギング / プロセス管理ユーティリティ
    - utils/logging_setup.py
      - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を追加して統一的なログ管理を実現。
      - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソール出力のみで継続するフォールバック処理を実装。
      - LOG_LEVEL / LOG_DIR の解決ルールを実装。
    - utils/process_priority.py
      - Windows / POSIX の差分を吸収したプロセス優先度設定（"high"/"normal"/"low"）と CPU affinity 設定ユーティリティを実装。
      - 権限不足や未対応 OS に対する警告・フォールバックを実装。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定（スコア降順、タイブレークルール）select_candidates。
      - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（スコアが全て 0 の場合は等分へフォールバック）。
    - portfolio/risk_adjustment.py
      - セクター集中制限 apply_sector_cap（既存保有・売却予定を考慮して新規候補を除外）。
      - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマップと未知レジームのフォールバック）。
    - portfolio/position_sizing.py
      - allocation_method（"risk_based"/"equal"/"score"）に基づく株数算出 calc_position_sizes。
      - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金）に基づくスケールダウン、残余での優先配分ロジックを実装。
      - 手数料・スリッページ見積りのための cost_buffer を考慮。
  - 監視・検証ツール
    - monitoring.monitoring_db:init_monitoring_db を介した監視テーブル初期化（冪等性を考慮）。
    - tools/paper_verification_report.py
      - Paper Trading の検証レポート生成ツール。
      - 稼働率（uptime）、注文成功率（fill_rate）、送信率、リスク却下数、API レイテンシ（平均/最大/P95）などを算出し、PASS/FAIL を判定する閾値を定義。
      - 日付フィルタ（from/to）や --db オプションでの DB 指定に対応。
  - 研究用モジュール（骨子）
    - research/factor_research.py（モメンタム等のファクター計算の骨子を実装）
      - DuckDB 接続を前提に prices_daily / raw_financials を参照して各種ファクター（Momentum / Value / Volatility / Liquidity）を計算する設計方針を記載。
      - 計算用の定数や P95 ユーティリティなどを実装済み（一部関数は継続実装を想定）。
  - パッケージ情報
    - __init__.py にてパッケージバージョン __version__ = "0.1.0" を設定。

- Changed
  - なし（初回公開）

- Fixed / Hardened
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）のケースでデフォルト値にフォールバックして time.sleep に渡す際の例外を回避。
  - ログディレクトリ作成やファイルハンドラ生成失敗に対するフォールバック処理を追加（起動失敗に至らないように堅牢化）。
  - process_priority の設定時に権限不足や未対応 API による例外を捕捉して警告に落とすことで起動安定性を向上。

- Security
  - .env ファイルを生成する際に「絶対に Git にコミットしないこと」を README 的に注意喚起（config_setup.py のヘッダに記載）。

---

注意:
- 上記はソースコードの実装内容を元にした変更履歴の推測です。実際のコミット単位での履歴や日付・作者情報は含まれていません。
- 将来的なリリースでは、各機能（特に research/factor_research の詳細実装や ExecutionEngine 内の挙動）について、より細かい変更履歴を追加してください。