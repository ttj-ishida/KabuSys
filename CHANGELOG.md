Keep a Changelog
=================

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

該当バージョン: __version__ = 0.1.0

Unreleased
----------
- 今後のリリースに向けた小さな改善・ドキュメント追加を予定しています。

[0.1.0] - 2026-04-18
-------------------
初回リリース。KabuSys のコア機能を実装しました。主な追加・変更点は以下の通りです。

Added
- 基本 CLI/ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading DB を使用し MockBrokerClient を利用可能。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイル / stop フラグに対応。
    - ExecutionEngine をデーモンスレッドで起動し、stop フラグで安全に停止可能。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番用 sqlite_path を使用して監視 DB を初期化。
    - stop フラグ検出・KeyboardInterrupt による終了処理を実装。
- 設定管理 / 検証 / ウィザード
  - config.py: 環境変数 / .env 自動読み込み機能を実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動ロード。
    - .env の読み取りロジック（引用符・エスケープ・コメントの扱い等）を実装。
    - Settings クラスで各種設定値を型変換・検証して提供（env, log_level, DB パス, paper モードなど）。
  - config_setup.py: .env の対話式ウィザードを追加（シークレット項目のマスク表示、既存値の再利用、保存機能）。
  - validate_config.py: 起動前設定検証 CLI を追加（必須環境変数・KABUSYS_ENV・DB パス・config/*.yaml の存在とパースチェック）。
    - --strict オプションで警告を FAIL 扱いにできる。
    - PyYAML 未インストール時は YAML 検証をスキップして警告を出す。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコアソート／上位 N 抽出。
    - calc_equal_weights / calc_score_weights: 重み付けロジック（スコアが全て 0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限を適用（既存保有の時価を計算して上限超過セクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear をサポート、未知の値はフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method("risk_based", "equal", "score") に基づく発注株数計算。
      - 単元株丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、残差を用いた追加配分ロジックを実装。
- ユーティリティ
  - utils.logging_setup:
    - 統一的なログ設定ユーティリティを追加。コンソール（stdout）と日次ローテーションファイル（logs/<app>.log）を設定。
    - LOG_DIR / LOG_LEVEL の解決順やハンドラの再設定（多重登録防止）を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority:
    - プラットフォーム差分を吸収するプロセス優先度設定を実装（Windows と POSIX を考慮、set_cpu_affinity も提供）。
    - 権限不足などで設定できない場合は警告でフォールバック。
- 分析 / レポート
  - tools.paper_verification_report.py:
    - Paper Trading 用の検証レポート生成ツールを追加。uptime・注文成功率・送信率・遅延（P95）等を算出して PASS/FAIL を判定。
    - --from/--to/--db オプションで期間・DB を指定可能。
- 研究用モジュール
  - research.factor_research.py（骨格実装）:
    - DuckDB 接続を受けてモメンタム・ボラティリティ等のファクターを計算するための関数設計・定数を追加（prices_daily / raw_financials を参照）。

Changed
- ロギングの標準出力先を stderr ではなく stdout に設定（Task Scheduler などのリダイレクト互換性向上）。
- .env 自動読み込みの優先順位: OS 環境変数 > .env.local > .env（既存 OS 環境変数は保護）。
- run_monitoring / run_execution 起動時に最初にプロセス優先度を設定するよう統一。
- Execution の Paper Trading と Live の DB 分離を明確化（paper_trading は PAPER_TRADING_SQLITE_PATH を使用）。

Fixed
- .env パーサーの堅牢化:
  - export KEY=val 形式への対応、シングル/ダブルクォートとバックスラッシュエスケープの正しい処理、インラインコメント扱いの改善。
- validate_config が PyYAML 未導入環境でも graceful に動作するようにし、YAML パース不可時は警告を出す設計に変更。
- logging_setup: ログディレクトリ作成失敗時に例外で落ちず、コンソールのみで動作を継続するよう改良。
- process_priority / set_cpu_affinity: 権限不足や未対応 OS で例外を出さず警告するように改善。
- position_sizing / calc_position_sizes:
  - 価格欠損（0.0 または None）のハンドリングを改善し、不正な価格での計算をスキップするようにした。
  - aggregate cap 適用時の端数処理と残余配分アルゴリズムを実装し、再現性のためソートの安定化を行った。

Security
- シークレット項目（API トークン等）は config_setup ウィザードでマスク表示。 .env は Git コミットしないことをドキュメントに明記。

Notes
- バージョンは src/kabusys/__init__.py の __version__ に従います: 0.1.0
- 初期実装のため、将来的に以下を検討／追加予定:
  - factor_research の完全実装（SQL 実装・ユニットテスト）
  - 単体テスト・統合テストの充実
  - broker 周りの抽象化とモック実装の拡張
  - 詳細なドキュメント（API リファレンス、設計ドキュメントの公開）

-----  
この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時には、コミットログやリリース差分（PR/issue）を確認して更新してください。