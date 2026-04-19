CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。

v0.1.0 - 2026-04-19
-------------------

Added
- 初期リリース: KabuSys ベース機能群を追加。
  - コア設定管理
    - kabusys.config.Settings: 環境変数 / .env ファイルからの設定読み込みを提供。
    - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml を基準）を検出して .env / .env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env のパースは export プレフィックス、シングル／ダブルクォート、バックスラッシュによるエスケープ、インラインコメント等に対応。
    - 環境変数必須チェック用の _require ユーティリティを提供。

  - 環境設定ウィザード
    - kabusys.config_setup: 対話式で .env を作成・更新する CLI ウィザードを追加。
    - シークレット項目はマスク表示、確認プロンプト付きで .env を安全に書き込み。

  - 設定検証ツール
    - kabusys.validate_config: .env と config/*.yaml の起動前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ確認、YAML パースチェック（PyYAML が存在する場合）、本番向けガードチェック（LINE 通知や Kill Switch 設定）などを実施。--strict モードで警告を fail 扱いにできる。

  - 起動スクリプト
    - run_execution: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離（MockBrokerClient の使用は設定に依存）。
      - 起動時にプロセス優先度を High に設定。
      - stop フラグ (data/stop_requested.flag) および実行 PID 管理をサポート。
      - 監視テーブルの初期化（init_monitoring_db）は冪等に実行。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値はデフォルトにフォールバックして警告出力。
      - 監視は環境にかかわらず production sqlite_path を使用する（監視 DB は一意）。
      - stop フラグ (data/stop_requested.flag) 検知でループを終了。

  - ロギング / プロセスユーティリティ
    - kabusys.utils.logging_setup.setup_logging:
      - ルートロガーの統一設定。コンソール出力（stdout）と日次ローテートされるファイル出力（TimedRotatingFileHandler）を設定。
      - 既存ハンドラをクリアして二重設定を防止。
      - LOG_DIR の作成失敗時はファイル出力を無効化してコンソールのみで動作するフェイルセーフを実装。
    - kabusys.utils.process_priority:
      - set_process_priority / set_cpu_affinity を提供。Windows と POSIX 系（Linux, macOS, FreeBSD）を吸収し、アクセス権限や未対応 API 時は警告を出してスキップする実装。

  - ポートフォリオ構築ライブラリ（純粋関数群）
    - kabusys.portfolio.portfolio_builder
      - select_candidates: スコア降順・タイブレークロジックで候補選定。
      - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分。全スコアが 0 の場合は等配分へフォールバックして警告。
    - kabusys.portfolio.risk_adjustment
      - apply_sector_cap: セクター集中上限チェック（max_sector_pct）を実装。未知セクター ("unknown") は上限適用外。
      - calc_regime_multiplier: market レジームに応じた資金乗数を返す（bull/neutral/bear マップ、未知レジームは 1.0 でフォールバック）。
    - kabusys.portfolio.position_sizing
      - calc_position_sizes: 複数の配分戦略（risk_based / equal / score）に基づいて発注株数を計算。lot_size（単元）丸め、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積り）を考慮した aggregate cap とスケーリング、残差の分配ロジックを実装。

  - 研究用ファクター計算（骨格）
    - kabusys.research.factor_research: DuckDB 接続を受け取り prices_daily / raw_financials を参照してモメンタム／バリュー等のファクターを計算する設計。モメンタム計算の定数と設計説明を含む（関数の実装は途中までの骨格あり）。

  - ツール
    - kabusys.tools.paper_verification_report:
      - Paper Trading 用の検証レポート生成スクリプトを追加。
      - 指標: システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）。
      - P95 計算、日付フィルタリング、デフォルト DB パス（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）、閾値による PASS/FAIL 判定を実装。

  - パッケージ情報
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。公開モジュール一覧を __all__ で指定。

Changed
- 環境変数読み込みポリシー:
  - OS 環境変数を保護する仕組みを導入（.env 上書き時に protected set を参照）。
  - .env のロード順: OS 環境変数 > .env.local > .env（既存環境変数は上書きされない）。.env.local は override=True（ただし OS 環境変数は保護）。
- ロギング設定:
  - 既存ハンドラを安全に flush/close してから削除し、二重ログを防止。
  - コンソールは stdout を使用（cron 等でのリダイレクト対策）。

Fixed
- 環境変数パースの堅牢化:
  - クォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメントの取り扱い等に対応し、.env ファイルの多様な書き方に耐性を持たせた。
- ポーリング間隔の安全な解決:
  - MONITOR_POLL_INTERVAL が不正（整数でない、0 以下）な場合は警告を出してデフォルト（60 秒）にフォールバック。time.sleep に不正値が渡らないように保護。
- データベース初期化:
  - 監視テーブルの初期化（init_monitoring_db）は run_execution/run_monitoring 起動時に呼び出され、冪等に存在を保証するようにした。
- プロセス優先度設定の失敗ハンドリング:
  - psutil による優先度設定や CPU affinity 設定で権限不足や未対応 API が発生した場合は警告ログを出して安全にスキップするように改善。

Notes / Known limitations
- research.factor_research の実装は骨格が中心で、完全なファクター計算ロジックは未完。DuckDB のテーブル構成（prices_daily / raw_financials）に依存するため、実運用前にテーブル整備が必要。
- apply_sector_cap は price_map に price 欠損（0.0）を含む場合にエクスポージャーを過少見積もる可能性がある旨を TODO コメントで残している（将来的に前日終値等でフォールバックする予定）。
- position_sizing の将来的拡張点として銘柄別の lot_size を持つ設計（stocks マスタの導入）を想定している。

Security
- 機密情報（J-Quants / kabu API パスワード等）は .env に記載することを想定。config_setup で .env を生成する際に「絶対に Git にコミットしないこと」を明記。
- .env の読み込み時に OS 環境変数を保護することで、シェル側で設定された機密値の上書きリスクを軽減。

---

今後の予定（想定）
- research.factor_research のフル実装（DuckDB クエリ + 正規化ユーティリティとの統合）。
- ExecutionEngine / BrokerClient 実装の拡張（実ブローカー接続・MockBroker の挙動詳細整備）。
- モニタリングアラート（LINE 通知）や監視閾値の設定ファイル化・チューニング。
- 単体テストと CI パイプラインの整備。

（この CHANGELOG はソースコードの内容から推測して作成しています。実際の変更履歴やリリースノートと差異がある場合は、実開発履歴に合わせて調整してください。）