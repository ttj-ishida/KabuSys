CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
コードベースから推測できる機能追加・変更・修正点を日本語で記載しています。

Unreleased
----------

- なし

0.1.0 - 2026-04-21
------------------

Added
- プロジェクト初版リリース（バージョン 0.1.0）。
- 実行用エントリスクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成をサポート（モック／実ブローカーの切替）。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag による外部停止制御と execution.pid 管理を行う。
    - RiskManager / OrderManager / Reconciler 等の組み立てを行う。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番 sqlite_path を使用する（監視テーブル初期化を含む）。
    - stop_requested.flag の検知で安全にループを終了。
- 環境設定・検証関連 CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する機能。
    - J-Quants / kabu API / DB パス / LINE など主要な環境変数を対話的に設定可能。
    - シークレット項目は表示マスク、保存前に確認を行う。
  - validate_config.py
    - .env と config/*.yaml の起動前検証ツール。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパースチェック（PyYAML 未インストール時は警告）等。
    - --strict オプションで警告を失敗扱いにできる。
- 設定管理
  - config.py
    - .env の自動ロード機構（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env → .env.local の優先読み込み、OS 環境変数の保護（上書き抑止）。
    - .env パーサは
      - export KEY=val 形式のサポート、
      - シングル/ダブルクォート内のバックスラッシュエスケープの解釈、
      - クォートなし値でのインラインコメント扱い（直前が空白の場合のみ）
      といった実運用上の細かい仕様に対応。
    - 設定アクセスをラップする Settings クラスを提供（env, log_level, duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能（テスト用途）。
- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのソート／上位選定（スコア降順、同点は signal_rank で破棄）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア合計 0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限ロジック（既存保有をベースにセクター超過時は当該セクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金倍率（bull/neutral/bear のマップ。未知値は 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数算出。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）によるスケールダウン、残差の lot 単位での再配分ロジックを実装。
    - cost_buffer による手数料/スリッページの保守的見積りを考慮。
- ユーティリティ
  - utils.logging_setup
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30世代保持）を設定する共通セットアップ。
    - LOG_DIR を自動作成。作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
    - ログレベルは引数 > 環境変数 > デフォルト の優先順位。
  - utils.process_priority
    - プラットフォーム差を吸収したプロセス優先度設定（Windows の priority class / POSIX の nice 値を内部で切替）。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応環境では警告ログを出してスキップする安全な実装。
- 監視 DB 初期化
  - monitoring.monitoring_db（起動時に init_monitoring_db を呼出し、監視用テーブルの冪等初期化を保証）。
- 実行時の安全機構
  - 停止フラグ（data/stop_requested.flag）や PID ファイル、KILL フラグ関連（KILL_FLAG_CLEAR_ON_START 設定）により外部からの停止・保護を実装。
- Paper Trading 検証ツール
  - tools.paper_verification_report
    - ペーパートレード用 SQLite からシステム稼働率、注文成功率、送信率、API レイテンシ（avg/max/P95）などを集計してレポート出力。
    - PASS/FAIL 判定閾値を定義（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200 ms など）。
    - --from / --to / --db オプションをサポートし、DB ファイルの不存在や SQLite のテーブル欠損時の耐障害性を確保。
- パッケージメタ情報
  - __init__.py によるバージョン設定: __version__ = "0.1.0"

Changed
- （初版リリースにつき該当なし）

Fixed
- （初版リリースにつき該当なし）

Security
- （該当なし）

Notes / 既知事項・利用上の注意
- run_monitoring は監視用に常に本番 sqlite_path を使用するため、監視とテスト用 DB を分離したい場合は運用設計に注意が必要（monitoring は環境にかかわらず production path を参照する実装）。
- .env の自動ロードはプロジェクトルート検出に依存する（.git または pyproject.toml）。配布パッケージ環境では自動ロードがスキップされる場合があるため、必要に応じて環境変数を直接設定すること。
- research.factor_research のファイルはファクター計算設計を含むが、現在の配布中のコードは途中で切れている（実装が未完の箇所あり）。ファクター計算を利用する前に実装完了・テストが必要。
- process_priority/set_cpu_affinity は権限や OS に依存するため、実際に優先度やアフィニティが反映されないケースがある（ログで警告が出力される）。
- ログ出力は標準で stdout に出力するため、プロセス監視運用とログローテーション戦略を合わせて運用すること。

今後の予定（推測）
- research パッケージのファクター計算の完成・テスト実装。
- SystemMonitor / ExecutionEngine の詳細なテスト・モニタリングアラート機能（LINE 連携等）の拡張。
- 銘柄別 lot_size 対応や手数料モデルのより詳細な反映など、position_sizing の拡張。

---

この CHANGELOG はコードの現状から推測して作成しています。実際のコミット履歴やリリースノートと照合して必要に応じて調整してください。