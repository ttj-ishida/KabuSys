# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
フォーマット: https://keepachangelog.com/ja/ を参照。

注: 以下は与えられたコードベースの内容から推測して作成した変更履歴です。

## [Unreleased]
- 進行中 / 要確認
  - research/factor_research.calc_momentum 関数の実装が途中で切れているため、ファクター計算モジュールは作業中です（WIP）。
  - risk_adjustment.apply_sector_cap の価格欠損時のフォールバックロジックは TODO として注記あり（将来的な改善予定）。
  - 今後の改善候補:
    - 銘柄ごとの単元情報（lot_size）を stocks マスタに持たせる設計への拡張。
    - .env パーサー/ウィザードの追加バリデーションやマスキング強化。

---

## [0.1.0] - 2026-04-19
初回公開リリース。以下の主要機能・ユーティリティを追加。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。

- 起動スクリプト
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル data/stop_requested.flag の検出でループ終了。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して DB 接続を行う。
  - run_execution.py:
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用し Mock ブローカーを利用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定し、停止フラグでエンジンを停止。実行中の PID 管理ファイル（data/execution.pid）指定対応。

- 設定／環境管理
  - config.py:
    - プロジェクトルート自動検出関数（.git / pyproject.toml 基準）を実装し、.env 自動読み込み機能を追加（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env / .env.local の読み込み順（OS 環境 > .env.local > .env）を実装（.env.local は上書き）。
    - .env パーサーは export プレフィックス、クォート／エスケープ、インラインコメントを考慮した堅牢な実装。
    - Settings クラスを提供し、J-Quants トークン、kabu API 設定、DB パス（duckdb/sqlite）、Paper Trading 設定、監視しきい値などをプロパティで取得可能にした。
    - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）や KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装。

  - config_setup.py:
    - 対話式ウィザードで .env を作成/更新する CLI を実装（python -m kabusys.config_setup）。
    - 項目群（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE トークン等）を対話的に入力可能。シークレット項目は表示をマスク。
    - 生成される .env のテンプレートと保存方法を実装（.env を誤ってコミットしないことを注意喚起）。

  - validate_config.py:
    - 起動前に環境変数や config/*.yaml を検証する CLI を実装（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリ存在チェック、config YAML の有無・パース検証（PyYAML があればパース）を実施。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - 統一的ログ設定関数 setup_logging(app_name, log_dir, level) を追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。既存ハンドラはクリアして再設定。
    - stdout を利用する設計（cron 等のリダイレクトを考慮）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしコンソールのみで継続。
  - utils/process_priority.py:
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加（set_process_priority）。
    - Windows の PRIORITY_CLASS・POSIX の nice 値を利用。権限不足等の例外は警告でフォールバック。
    - CPU affinity 設定用 set_cpu_affinity を実装。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py:
    - 候補選定 select_candidates（スコア降順、signal_rank でタイブレーク）、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を追加。スコア合計が 0 の場合は等金額配分にフォールバック（警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、max_sector_pct を超えるセクターの新規候補を除外するロジックを実装（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームで警告し 1.0 にフォールバック。
    - 価格欠損時のフォールバックは将来的な改善として TODO を記載。
  - portfolio/position_sizing.py:
    - 各種 allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
    - 単元（lot_size）丸め、1 銘柄上限・aggregate cap スケーリング、cost_buffer（手数料・スリッページ見積り）対応、可用現金に応じたスケールダウンロジックを実装。
    - risk_based 方式では risk_pct / stop_loss_pct に基づくポジションサイズ計算を実施。

- Execution コンポーネント骨組み（呼び出し／組み立て）
  - run_execution から BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立てて起動する処理を追加（実体は別モジュールに実装されている想定）。
  - RiskConfig のデフォルトパラメータ（max_position_pct=0.20 等）を設定。初期ポートフォリオ値を broker.get_available_cash() から取得。

- 監視（Monitoring）
  - run_monitoring で SystemMonitor を初期化・起動。DB 初期化（init_monitoring_db）を実行し、duckdb も接続。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から集計レポートを生成する CLI を追加。
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）。
    - PASS/FAIL 基準を定義（稼働率 >= 99.0%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200ms）。
    - 日付フィルタ (--from / --to) をサポートし、レポートを標準出力へ整形して出力。

### Changed
- ロギング設計上の既定値:
  - ログディレクトリ: logs/
  - デフォルトログレベル: INFO
  - 日次ローテーション・30日保持を採用。

- 環境変数読み込みの挙動:
  - OS 環境変数は保護され .env の上書きを防止（protected set を使用）。
  - .env のパースは export プレフィックス、クォート、エスケープ、インラインコメントに対応するよう改善。

### Fixed
- プラットフォーム差異への適応:
  - process_priority で Windows / POSIX の違いに対応し、該当しない OS では警告を出してスキップするように安定化。

### Deprecated
- なし

### Security
- なし

---

開発者向け注記
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。config_setup.py でもその旨を注意喚起しています。
- validate_config は本番（KABUSYS_ENV=live）向けの追加チェックを行い、LINE 通知設定や Kill Switch クリア設定の危険性を警告します。
- 一部モジュール（例: factor_research）は実装が未完の箇所があるため、使用前に実装完了・テストを行ってください。

もし特定ファイルごとにさらに詳細な変更点（関数単位の追加・変更・挙動の差分）が必要であれば、対象ファイル名を指定してください。