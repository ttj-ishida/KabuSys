CHANGELOG
=========

すべての重要な変更点はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。  

※ 本 CHANGELOG は提示されたコードベースの内容から推測して作成しています。

[Unreleased]
------------

- （現時点のコードは initial release 相当の状態のため、未リリースの変更はありません）

[0.1.0] - 2026-04-24
-------------------

初回リリース — KabuSys: 日本株自動売買システム（プロトタイプ）

Added
- パッケージ全体
  - kabusys パッケージを追加。バージョン: 0.1.0。
  - モジュール構成を整備（execution, monitoring, portfolio, research, tools, utils, config, etc.）。

- 実行・監視ランチャ
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV による動作分岐（paper_trading 時は専用の paper DB と MockBrokerClient を利用）。
    - execution.pid による PID 管理、data/stop_requested.flag による外部停止制御を実装。
    - 実行はバックグラウンドスレッドで行い、停止フラグ検知で安全に停止する。
    - DB 接続（SQLite / DuckDB）および監視テーブル初期化を行う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 本番用 sqlite_path を環境にかかわらず監視で使用（監視データは本番 DB に書き込む想定）。
    - data/stop_requested.flag による停止制御、KeyboardInterrupt による終了処理を実装。

- 設定管理
  - config.py:
    - .env 自動読み込み機能を導入（プロジェクトルートの検出: .git や pyproject.toml を基準）。
    - .env / .env.local の読み込み順序と OS 環境変数保護（保護されたキーは上書きされない）を実装。
    - 複雑な .env パース実装（export プレフィックス、クォート内のエスケープ、インラインコメントの扱い）を提供。
    - Settings クラスで各種設定をプロパティ化。バリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE 等、ペーパートレード向け設定を追加。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。

  - config_setup.py:
    - 対話式ウィザードで .env を初期作成/更新する CLI を実装。
    - 各項目の説明・選択肢・シークレット入力対応を備え、.env ファイルを書き出す機能を提供。

  - validate_config.py:
    - 起動前に .env と config/*.yaml の設定整合性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パス（親ディレクトリ存在確認）、YAML の存在／パース検証（PyYAML 未インストール時は警告）などを実装。
    - --strict オプションで警告を FAIL 扱いにする機能を提供。

- ログ・プロセス運用ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティを追加。
    - ログディレクトリ自動作成、ファイルハンドラ作成失敗時のフォールバックを実装。
    - ログ保持日数は 30 日（backupCount=30）。
  - utils/process_priority.py:
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加（Windows / POSIX 対応）。
    - CPU affinity 設定ユーティリティを提供。
    - psutil の権限エラー等を安全に無視して処理を継続する設計。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルからスコア降順で候補選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分およびスコア加重配分を実装。スコア合計が 0 の場合は等配分にフォールバック（警告出力）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限により候補を除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームはフォールバック 1.0。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数決定ロジックを実装。
    - 単元株（lot_size）単位で丸め、per-stock 上限・aggregate cap（available_cash）に基づくスケーリングと残差処理を実装。
    - cost_buffer による保守的コスト見積りを考慮。

- Execution コンポーネント（概念的）
  - execution/*.py（参照のみ: BrokerClientFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager, OrderRepository）
    - BrokerClientFactory 経由で環境に応じたブローカークライアント（Mock含む）を生成。
    - RiskConfig のデフォルト値を設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
    - ExecutionEngine は pid_file を受け取り run_session/stop の制御を行う想定。

- 監視・検証ツール
  - monitoring/monitoring_db 初期化機能（init_monitoring_db）を使用して監視テーブルを冪等に作成。
  - tools/paper_verification_report.py:
    - ペーパートレード用の検証レポート生成 CLI を追加。
    - システム稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出し PASS/FAIL を判定する自動判定基準を実装。
    - デフォルト DB パスは data/paper_trading.db。PAPER_TRADING_SQLITE_PATH と --db オプションで上書き可能。
    - P95 計算、日付フィルタ、NULL/データ欠損に対する耐性を実装。
    - デフォルト閾値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms

- 研究用
  - research/factor_research.py:
    - DuckDB 接続を利用したファクター計算インターフェース（モメンタム、MA200 乖離、ATR、流動性等）を実装する設計。関数 calc_momentum などを追加（実装途中の箇所あり）。

Changed
- なし（初回リリース）

Fixed
- なし

Removed
- なし

Security
- なし（既知のセキュリティ修正は含まれていません）

Notes / Known limitations
- factor_research.py の実装はファイル末尾で途中（start_da で切れている）であり、完全実装が必要。
- position_sizing.calc_position_sizes 内で価格が欠損（0.0）の場合、エクスポージャーが過少見積りされる旨の TODO コメントがある。将来的に前日終値や取得原価等のフォールバックが必要。
- ログディレクトリ作成やプロセス優先度設定は環境（権限）によって失敗することが想定され、失敗時はフォールバックして動作する設計だが運用時に注意が必要。
- validate_config の YAML 検証は PyYAML 非インストール時にはスキップされる（警告のみ）。

今後の予定（提案）
- factor_research の完成と単体テストの追加。
- ExecutionEngine 周りの e2e テスト（MockBroker を用いたペーパートレード検証）。
- 銘柄別 lot_size のサポート（stocks マスタの導入）。
- 監視関連の通知（LINE 連携）実装の強化とアラートルールの策定。
- DuckDB を用いた分析ジョブの標準化（スケジューリング・ジョブ管理）。

---

以上。追加でリリースノート内容を拡張したい箇所（個別ファイルごとの詳細、日付の変更など）があれば指示してください。