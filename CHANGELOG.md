# CHANGELOG

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

- リリース管理方針: ここではパッケージ内の初期機能群をまとめて v0.1.0 として記載しています。  
- 参考: 実装中の詳細はソースコードの docstring とモジュールコメントを参照してください。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 基本パッケージ初期実装: KabuSys 自動売買システムのコアモジュール群を追加。
  - パッケージメタ情報: src/kabusys/__init__.py にてバージョンを 0.1.0 に設定。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書きに対応（デフォルト 60 秒）。
    - 停止判定はプロジェクト直下 data/stop_requested.flag ファイルで行う。
    - Monitoring は KABUSYS_ENV に関わらず production 用 sqlite_path を使用する旨を明示。
    - 起動時にプロセス優先度を "high" に設定するフローを導入。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite (default: data/paper_trading.db) に記録して本番 DB から分離。
    - エンジンは別スレッドで実行し、停止フラグ (data/stop_requested.flag) により安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定するフローを導入。

- 設定管理
  - config.py
    - 環境変数／.env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env/.env.local のロード順 (OS env > .env.local > .env) を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env の行パーサを実装し、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理をサポート。
    - Settings クラスを導入し、各種設定値（DB パス、API トークン、監視閾値、環境種別判定等）をプロパティ経由で取得できるように。
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path、kill/ pid ファイルパスなどのプロパティを含む。

  - config_setup.py
    - 対話式環境設定ウィザードを追加（.env を対話的に作成・更新）。
    - デフォルトや選択肢、シークレット入力の扱い、既存 .env の読み込み、保存前の確認をサポート。
    - .env のテンプレート書き込みロジックを提供。

  - validate_config.py
    - 起動前検証 CLI を追加（必須環境変数の存在、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ有無、config/*.yaml の存在とパース確認（PyYAML があればパース検証）など）。
    - --strict オプションにより警告を失敗として扱うモードを追加。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。
    - stdout に出力する StreamHandler と、日次ローテーション（TimedRotatingFileHandler）を root ロガーに設定。既存ハンドラのクリアやログレベル解決（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

  - utils/process_priority.py
    - プロセス優先度設定と CPU affinity 設定用ユーティリティを追加。
    - Windows / POSIX（Linux, macOS, FreeBSD）での差分吸収（psutil を利用）を実装し、権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
    - スコア全体が 0 の場合は等配分へフォールバックし警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を追加。既存保有を考慮して新規候補をフィルタリング。"unknown" セクターは制限対象外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear のマップ、未知レジームはフォールバック 1.0）。

  - portfolio/position_sizing.py
    - 銘柄ごとの発注株数計算ロジックを追加（allocation_method: "risk_based", "equal", "score" をサポート）。
    - 損切り、リスクパーセンテージ、max position、max utilization、lot_size、cost_buffer（手数料/スリッページ見積り）を考慮した計算。
    - aggregate cap に応じたスケールダウンと lot 単位での再配分ロジックを実装。

- 研究・ファクター計算
  - research/factor_research.py
    - DuckDB 接続を受け取り価格データからファクター（Momentum, Value, Volatility, Liquidity）を計算するための基盤を追加（詳細な関数はモジュール内に実装予定／一部実装開始）。

- Paper Trading 向け判定ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - DB からシステム稼働率、注文成功率、送信率、API レイテンシ（平均/最大/P95）を集計し、閾値に基づいて PASS/FAIL を判定（閾値はソース内に定義）。
    - コマンドライン引数で期間指定 (--from / --to) と DB パス指定 (--db) に対応。

- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を run スクリプトから呼び出して監視用テーブルの存在を保証（冪等的に初期化）。

### 変更 (Changed)
- ログ出力先の統一化
  - setup_logging により全起動スクリプトが同一のフォーマット・ローテーション設定を共有するように変更（コード設計フェーズで統一された挙動に整理）。

- .env パーシングの堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを明確化して .env 自動ロードを頑健化。

### 修正 (Fixed)
- （初期リリースのため重大なバグ修正履歴はなし。実行時のエラーは logger.exception / warning にて安全に処理する設計を採用。）

### セキュリティ (Security)
- 秘匿情報の扱い
  - config_setup.py のウィザードで J-Quants トークン・kabu API パスワードはシークレットとして扱うよう設計（表示をマスク）。.env を Git にコミットしないよう README/テンプレートで注意喚起する旨のコメントを含む。

---

今後の予定（例）
- research/factor_research の完全実装（ファクター計算関数群の実装完了）。
- ExecutionEngine / BrokerClient の実装強化と単体テスト整備。
- CI による .env 自動読み込みの安全性検証および各種ユニットテスト追加。

もし特定のモジュールや変更点についてより詳細な説明が必要であれば、どのファイル・機能について知りたいかを教えてください。