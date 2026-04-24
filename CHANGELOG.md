# Changelog

すべての注目すべき変更をこのファイルに記録します。フォーマットは「Keep a Changelog」準拠です。  
リリースの重要な点（追加・変更・修正・既知の制約など）を日本語で記載しています。

全般
- バージョンポリシー: セマンティックバージョニングを想定（この履歴は初期リリースを記録）。
- 日付は本 CHANGELOG 作成日: 2026-04-24。

## [0.1.0] - 2026-04-24

初期リリース。自動売買システム「KabuSys」のコアユーティリティ群、実行/監視スクリプト、設定ツール、ポートフォリオ構築ロジック、検証ツール等を追加。

### Added
- 基本設定と自動読み込み
  - .env ファイルの自動読み込み機能を追加（プロジェクトルートの検出: .git または pyproject.toml が基準）。
  - .env のパースはシングル/ダブルクォート、エスケープ、インラインコメント、`export KEY=val` 形式に対応。
  - 環境変数のロード順: OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化可能。

- Settings クラス
  - 環境変数をラップする Settings クラスを実装。J-Quants / kabuステーション / LINE / DB パス / 監視閾値 等のプロパティを提供。
  - KABUSYS_ENV/LOG_LEVEL 等の値検証と便利なプロパティ（is_live / is_paper / is_dev）を実装。
  - Paper Trading 関連設定: PAPER_FILL_MODE（"instant" / "partial" / "never" / "reject"）および PAPER_TRADING_SQLITE_PATH をサポート。

- 設定ユーティリティ
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を追加。PyYAML 非インストール時は YAML 検証をスキップする（警告）。`--strict` オプションで警告をエラー扱いに可能。

- 実行 / 監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db 既定）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ (data/stop_requested.flag) を監視して安全停止。
    - PID ファイル (data/execution.pid) を扱う仕組みをサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告出力。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視テーブルは常に本番用に初期化）。
    - 停止フラグ (data/stop_requested.flag) によるループ終了、KeyboardInterrupt ハンドリング、check_once() の例外捕捉で堅牢化。

- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定する共通ユーティリティを追加。
    - LOG_LEVEL / LOG_DIR の解決順とファイルハンドラ作成失敗時のフォールバックを実装。
  - utils/process_priority.py:
    - プロセス優先度設定 (high/normal/low) をクロスプラットフォームで実装（psutil ベース）。Windows / POSIX(macOS/Linux/FreeBSD) に対応。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity() を追加。
    - 権限不足や未対応環境では警告を出してスキップする安全設計。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - シグナル選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights) を実装。
    - スコア全てが 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py:
    - セクター集中上限を適用する apply_sector_cap を実装（売却予定銘柄の除外や "unknown" セクターの扱いを明記）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull"=1.0、"neutral"=0.7、"bear"=0.3、未知は 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - allocation_method（"risk_based" / "equal" / "score"）に対応した株数計算 calc_position_sizes を実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金に合わせてスケールダウン）、cost_buffer（手数料・スリッページ考慮）のロジックを実装。
    - 残余キャッシュを利用してラウンド処理で lot_size 単位の追加配分を行うアルゴリズムを実装。

- 解析・研究ユーティリティ
  - research/factor_research.py:
    - Momentum / Value / Volatility / Liquidity 等のファクター計算枠組みを追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - 各種定数（窓幅・スキャン範囲）を定義。P95 等の補助関数あり。
    - （注）ファイル末尾に示される calc_momentum の実装は途中までの状態（ファイル切れのため未完の可能性あり）。

- 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。期間指定や DB パス指定オプションを提供。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数などを集計して PASS/FAIL を判定する閾値を定義。
    - DB が存在しない場合のエラーメッセージ等を実装。

- パッケージ初期化
  - kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。
  - portfolio モジュールの __all__ エクスポートを整理。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- 環境変数ファイル（.env）に関する注意書き:
  - config_setup が生成する .env は「絶対に Git にコミットしない」旨のヘッダコメントを出力。
  - シークレット項目はウィザードでマスク表示するよう配慮。

### Notes / Known limitations / TODOs
- research/factor_research.py の calc_momentum 実装がファイル中で途中で終わっている（"start_da" の破損と思われる）。ファクター計算の完全実装は今後の作業が必要。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過小評価される旨の注記あり。前日終値等でのフォールバックは将来的な拡張予定。
- position_sizing.calc_position_sizes:
  - 現状は全銘柄共通の lot_size を想定。将来的に銘柄別 lot_size を受け取る拡張を検討中（TODO 記載あり）。
- run_monitoring では Monitoring が「環境にかかわらず本番 sqlite_path を使用」する点に注意。監視データを別 DB に分けたい場合は設定またはコード修正が必要。
- ログディレクトリ作成やプロセス優先度設定は権限依存で失敗する可能性があるため、失敗時は警告を出してフォールバックする設計。

---

将来的な追加案（例）
- research モジュールの完全実装（ファクター算出ロジックの完成、ユニットテスト）
- 個別銘柄の lot_size サポート、手数料・スリッページのより現実的なモデル化
- モニタリング用 DB を環境別に分離するオプション
- ExecutionEngine / Broker クライアントのエンドツーエンド統合テスト、モックの充実

（以上）