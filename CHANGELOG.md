# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
日付は 2026-04-21。

## [0.1.0] - 2026-04-21

初回リリース。自動売買システム「KabuSys」のコアユーティリティ・起動スクリプト・ポートフォリオ構築・検証ツールを含みます。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離する挙動を実装。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成（paper/live/開発に対応する想定）。
    - ExecutionEngine をスレッドで実行し、プロジェクトルートの stop フラグ（data/stop_requested.flag）で安全に停止可能。
    - 実行時にプロセス優先度を "high" に設定し、pid ファイル（data/execution.pid）を利用。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0以下や非数値）はデフォルトにフォールバックして警告を出力。
    - 監視用 DB は実行環境にかかわらず本番 sqlite_path を使用する仕様。

- 設定管理・支援ツール
  - config.py
    - .env 自動ロード機構を実装（プロジェクトルート探索: .git または pyproject.toml を基準）。
    - .env のパースを強化:
      - export KEY=val 形式に対応
      - シングル/ダブルクォート内のバックスラッシュエスケープに対応
      - クォートなし行のインラインコメント扱いルールを改善
    - Settings クラスを実装し、各種設定値（DB パス、KABUSYS_ENV、ログレベル、paper_trading 用設定等）をプロパティで提供。PAPER_FILL_MODE の検証や env 値の妥当性チェックを含む。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。シークレット項目はマスク表示、既存 .env の読み込みに対応。
  - validate_config.py
    - 起動前に .env と config/*.yaml の検証を行う CLI。
    - 必須環境変数の有無、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パースチェック、KABUSYS_ENV=live 時の追加警告などを実行。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通利用するログ設定ユーティリティ。
    - stdout への StreamHandler（stdout を使用）と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30 日保持）をルートロガーに設定。
    - 既存ハンドラを一旦クリアしてから再設定することで二重設定を防止。
    - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - Windows / POSIX（Linux, macOS, FreeBSD）でのプロセス優先度設定を抽象化。
    - set_process_priority(level) で "high"/"normal"/"low" を指定可能。アクセス権限不足等は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) でプロセスを最初の N コアに固定する機能を提供（利用不可時は警告を出してスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank）でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分を提供。全スコアが 0 の場合は警告して等分配にフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用。既存保有のセクター別エクスポージャーを計算し、閾値超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: weight/candidates/リスクパラメータに基づいて発注株数（単元株丸め）を算出。
    - risk_based / equal/score 両方式に対応。lot_size（デフォルト 100）で切り捨てを行い、aggregate cap（available_cash 超過時）ではスケールダウンと remainder による追加配分アルゴリズムを実装。
    - cost_buffer（スリッページ・手数料見積り）を考慮した保守的なコスト推定を実装。

- リサーチ / ファクター計算（初期実装）
  - research/factor_research.py（骨組み）
    - DuckDB 接続を受けて各種ファクター（Momentum / Value / Volatility / Liquidity）を計算する設計方針と定数を定義。
    - モメンタム計算 calc_momentum の実装開始（ファイル末尾で途中）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプト。
    - 稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシ等を集計し、閾値比較（PASS/FAIL）で判定。
    - DB が存在しない場合にわかりやすくエラーメッセージを出力。
    - P95 算出、日付フィルタリング（ISO8601 UTC 変換）に対応。

- パッケージ情報
  - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。

### Changed
- なし（初回リリースのため既存挙動からの変更はありません）。

### Fixed
- なし（初リリース）。

### Notes / Behavior details
- .env 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をセットすると無効化可能。プロジェクトルートが見つからない場合は自動ロードをスキップする設計になっています（配布後の安全性確保）。
- run_monitoring は監視データ保存に本番 sqlite_path を常に使用します（環境に依存しない監視 DB の一貫性を確保するため）。
- run_execution は paper_trading モード時に MockBrokerClient 等での完全分離を想定しており、紙上トレードの結果は PAPER_TRADING_SQLITE_PATH で管理します。
- logging_setup は stdout を使用するため、cron 等からの起動で stdout/stderr をリダイレクトしている環境でもログの扱いが安定します。
- position_sizing と apply_sector_cap は現状 DB 参照を行わない純粋関数として実装されており、テストしやすい設計です。

---

今後の予定（例）
- research/factor_research の各ファクター実装完了
- ExecutionEngine / SystemMonitor の詳細挙動のドキュメント化・テスト追加
- strategy モジュール（シグナル生成）およびデータ取得パイプラインの統合テスト

README やドキュメントに載せるべき運用ガイド（.env 設定例、DB 初期化、起動コマンド等）は別途整備予定です。