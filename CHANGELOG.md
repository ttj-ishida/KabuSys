Keep a Changelog準拠の CHANGELOG.md（日本語）
※コードベースから挙動を推測して記載しています。

All notable changes
===================

0.1.0 - 2026-04-20
------------------

Added
- 初回リリース。
- 起動スクリプト / 実行環境
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時にはペーパートレード用 DB を分離して使用（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成を導入（テスト用 MockBroker の利用を想定）。
    - ExecutionEngine をデーモンスレッドで起動し、data/stop_requested.flag による安全停止と data/execution.pid による PID 管理。
    - エンジン停止時は thread.join を利用して最大待機を行う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（不正値はデフォルト 60 秒にフォールバック）。
    - 監視は環境に関係なく本番向け sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定、停止フラグ検出でループを終了。
- 設定・環境管理
  - config.py: Settings クラスによる環境変数ラッパーを追加。
    - .env 自動読み込み機能を導入（プロジェクトルートを .git または pyproject.toml で探索）。
    - 読み込み順序: OS 環境 > .env > .env.local（.env.local は .env を上書き、ただし OS 環境は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - 各種プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - KABUSYS_ENV 値検証（development/paper_trading/live）とログレベル検証。
  - config_setup.py: 対話式 .env ウィザードを追加（.env の初期作成・更新を支援）。
    - シークレット入力マスク、デフォルト値、選択肢サポート、保存前の確認を含む。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 確認、DB パスや config/*.yaml の存在・パース検証（PyYAML 未インストール時は警告）。
    - --strict オプションで警告を失敗扱いにできる。
- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - 統一的なログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と 日次ローテート（TimedRotatingFileHandler）によるファイル出力を設定。
    - LOG_DIR / app_name に基づくログファイル（<log_dir>/<app_name>.log）、30 日分保持。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみ動作するフォールバック。
  - utils/process_priority.py:
    - プラットフォーム差異を吸収するプロセス優先度設定ユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）対応。アクセス権限がない場合は警告を出してスキップ。
    - CPU affinity 設定関数 set_cpu_affinity を追加（コア数指定で最初の N コアに固定）。
- ポートフォリオ構築・リスク調整・ポジション算出
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順（同点は signal_rank でタイブレーク）で候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分。スコア合計が 0 の場合は等金額にフォールバックし WARNING を出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）を実装。既存保有のセクター別時価を計算し上限超過セクターの新規候補を除外。unknown セクターはチェック対象外。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数を実装（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして警告。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算を実装。
      - risk_based: risk_pct と stop_loss_pct から個別目標株数を算出、単元株（lot_size）で丸め。
      - equal/score: 重みと max_utilization を用いた per-position 上限、aggregate cap によるスケーリング。
      - cost_buffer を用いた保守的なコスト見積もり、利用可能現金を超える場合はスケールダウンと残差に基づく追加配分を行う。
      - 価格欠損（<=0）や lot_size 単位の丸めに関するログ出力。
- 研究・ファクター計算（骨格）
  - research/factor_research.py:
    - モメンタム、ボラティリティ、流動性、バリュー系ファクターの計算方針と定数を定義。
    - DuckDB を利用して prices_daily / raw_financials から計算する設計（関数 calc_momentum の冒頭まで実装済み）。
- ツール
  - tools/paper_verification_report.py:
    - ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）から検証レポートを生成するスクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）を算出。
    - パス/フェイル基準を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms）し、判定結果を表示。
- パッケージメタ
  - __init__.py: バージョンを "0.1.0" に設定し、主要パッケージを __all__ に列挙。

Notes / 実装上の注意点
- .env パーサーは export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理をサポート。無効行は無視する実装。
- .env の自動読み込みでは OS 環境変数を保護（上書き禁止）するため protected set を使用。
- run_monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する点に注意（監視データを本番 DB に統一して収集する設計）。
- run_execution はペーパートレード時に DB を分離する点により、本番とペーパートレードのデータが混ざらないよう配慮。
- process_priority / cpu_affinity は権限不足や未サポート環境で安全にフォールバックする（警告ログ）。
- ロギングは stdout を基本とし、ファイル出力に失敗した場合でもプロセスが継続できる設計。

今後の課題（想定）
- research/factor_research.py のファクター計算関数の続き実装（calc_momentum の未完部）。
- 銘柄ごとの lot_size をサポートするための拡張（stocks マスタ参照）。
- 価格欠損（price=0）時のフォールバックロジック（前日終値など）実装。
- 単体テスト、統合テストの追加（特にポジション算出・スケーリングロジック、ファクター計算）。
- ドキュメント（PortfolioConstruction.md 等）との整合性チェックと詳細化。

--- 

この CHANGELOG はコードから推測して作成しています。実際の変更履歴やリリースノートを作成する際は、コミットログやリリース管理情報に基づいて調整してください。