# Changelog

すべての重要な変更をここに記録します。フォーマットは Keep a Changelog に準拠しています。  
現在のバージョン: 0.1.0

## [Unreleased]

## [0.1.0] - 2026-04-17

### 追加
- 初回リリース（0.1.0）。
- 基本構成・起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - 停止用フラグファイル (data/stop_requested.flag) を検知して安全にループを抜ける処理を実装。
    - 監視用 DB は環境にかかわらず production の sqlite_path を使用する挙動を明示。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを実行。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカクライアント生成を組み込み（paper_trading 時に Mock クライアントを利用する想定）。
    - Engine を別スレッドで起動し、停止フラグファイルを検知して安全停止する処理を実装。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを実行。
- 設定管理
  - config.py
    - .env 自動読み込み実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env / .env.local の読み込みルール（OS 環境変数優先、.env.local は上書き用）を実装。
    - .env 行パーサは export プレフィックス、クォート（シングル/ダブル）およびバックスラッシュエスケープ、インラインコメント処理に対応。
    - Settings クラスを導入し、環境変数の型変換・バリデーションを提供（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の妥当性検証など）。
    - 各種パス（DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH 等）と閾値（CPU/MEM/DISK）を環境変数で取得可能。
- 設定ユーティリティ
  - config_setup.py
    - 対話式ウィザードで .env を新規作成/更新する CLI を追加。
    - 秘密値マスク、選択肢提示、既存 .env の読み込み・再利用、保存前確認などの UX を実装。
  - validate_config.py
    - 起動前チェック用 CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ確認、config/*.yaml の存在とパース（PyYAML があれば）を検証。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の危険設定など）を実装。
    - --strict による警告を FAIL 扱いにするモードをサポート。
- ポートフォリオ構築ライブラリ（純粋関数群、メモリ内処理）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全銘柄スコアが 0 の場合は等配分にフォールバックして警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限をチェックし、上限超過セクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear 等）に対する投下資金乗数を提供（未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じて発注株数を算出。単元株（lot_size）丸め、個別上限（max_position_pct）、集合上限（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的な見積り、端数の再配分ロジックを実装。
- 分析・レポート・研究
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成 CLI を追加。指定期間（--from / --to）で稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計して PASS/FAIL を判定する。デフォルト DB は data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH から上書き可能。
    - P95 計算、NULL/データ欠損時の N/A ハンドリング、閾値定義（稼働率99% 等）を実装。
  - research/factor_research.py
    - DuckDB 接続を利用したファクター計算（モメンタム、ボラティリティ等）を実装。calc_momentum/calc_volatility など、prices_daily テーブル参照で計算する純粋関数群を提供。
- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム非依存でプロセス優先度と CPU affinity を設定するユーティリティを追加。
    - Windows/Linux/macOS の差分を吸収し、psutil を用いて nice / priority_class / cpu_affinity をセット。権限不足や未サポート環境では警告を出して安全にスキップする実装。

### 変更
- パッケージメタ情報
  - __init__.py にバージョン情報を追加: __version__ = "0.1.0"

### 修正
- 初期リリースのため該当なし（今後のパッチリリースで細かなバグ修正や改善を追加予定）。

### 既知の注意点 / 制限
- position_sizing.calc_position_sizes:
  - 価格情報が欠損（0.0 等）の場合、エクスポージャーが過少に見積もられる可能性があり、将来的に前日終値や取得原価を用いるフォールバックが望まれる旨を TODO コメントで明示。
- .env 自動読み込みはプロジェクトルートの検出に依存するため、配布後や特殊配置では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化できる。
- 一部の config/*.yaml の検証は PyYAML に依存。未インストール時は YAML パースの検証がスキップされ、警告が出る。
- run_monitoring の監視 DB は環境にかかわらず sqlite_path を参照するため、paper_trading と production の完全分離が必要なケースでは設定に注意。

### セキュリティ
- 秘密情報（API トークン・パスワード）は .env に保存する設計だが、config_setup は .env を生成する際に「.env を絶対に Git にコミットしないこと」旨を明示している。公開リポジトリに秘密情報を含めないよう注意してください。

---

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートはプロジェクトの変更意図やリリース方針に応じて適宜修正してください。