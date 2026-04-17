# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはリポジトリ内の現在のコードベースから推測して作成した初期リリース用の変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-17
### Added
- 基本パッケージメタ情報を追加
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
    - 複雑な .env 行パースの実装（export、クォート、バックスラッシュエスケープ、インラインコメントの対応）。
    - Settings クラスを導入し、各種環境変数（J-Quants、kabuステーション、LINE、DBパス、監視閾値、システムフラグ等）をプロパティ経由で取得・検証できるようにした。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値チェックとエラーメッセージを実装。
  - global settings インスタンスを提供（settings）。

- 設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env ファイルを初期作成 / 更新するツールを追加。
    - デフォルト値・選択肢・シークレット入力表示・保存確認の実装。
    - .env の読み書きロジックを提供（既存値読み込み、テンプレート書き込み）。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml の不備を検出する検証ツールを追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DBパスの親ディレクトリ存在確認、config YAML の存在および（PyYAML があれば）パース検証を実装。
    - KABUSYS_ENV=live の場合の追加警告（LINE通知設定や KILL_FLAG_CLEAR_ON_START の危険性）。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行エンジン起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するエントリポイントを実装。
    - 設定に応じて paper_trading 用の専用 SQLite DB を使用（settings.is_paper による分離）。
    - BrokerClientFactory を使ったブローカークライアント生成（paper_trading 時は MockBrokerClient を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで起動する制御ロジックを実装。
    - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を提供。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止処理、PID ファイル管理を実装。
    - DuckDB 接続を受け取るコンポーネント構成。

- 監視ループ起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor をポーリングで定期実行する起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視 DB は共有想定）。
    - 停止フラグ検知でループを安全に抜ける処理、check_once() の例外を捕捉して継続する耐障害性の実装。
    - プロセス優先度を起動時に設定する処理を追加。

- 監視 DB 初期化ユーティリティ利用
  - run_monitoring.py / run_execution.py で監視テーブルが存在することを保証する init_monitoring_db 呼び出しを追加（冪等）。

- Paper Trading 検証レポート
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の SQLite DB から稼働率・注文成功率・送信率・レイテンシなどを集計してレポート/判定を出力する CLI を追加。
    - --from / --to / --db オプション対応、P95 計算、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）による PASS/FAIL 判定。
    - DB 存在チェックとエラーハンドリング。

- ポートフォリオ構築ロジック（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等配分 / スコア加重配分（calc_equal_weights / calc_score_weights）を実装。
    - スコアが全て 0 の場合は等配分にフォールバックする警告実装。
  - src/kabusys/portfolio/position_sizing.py
    - allocation_method("risk_based" / "equal" / "score") に基づく株数決定ロジックを実装。
    - リスクベースの position sizing、単元株丸め(lot_size)、max position cap、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積りを実装。
    - 現在保有との差分を計算して買い増し量を返す。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック（既存保有のセクター比率が上限を超えた場合、新規候補をフィルタ）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装（未知のレジームは警告して 1.0 フォールバック）。
  - src/kabusys/portfolio/__init__.py
    - 上記機能をパッケージ API としてまとめてエクスポート。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - DuckDB を使ったモメンタム / ボラティリティ等のファクター計算を実装（prices_daily / raw_financials テーブル参照）。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率の計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比の計算（ウィンドウ不足時は None を返す）。
    - 大規模データを効率的に扱うために SQL ウィンドウ関数を活用。
    - 結果は (date, code) をキーとする dict のリストで返却。

- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - プロセス優先度・CPU affinity 設定ユーティリティを追加（psutil を利用）。
    - Windows / POSIX の差を吸収し、set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未サポート環境での警告処理を実装。

### Changed
- （初回リリースのためなし）

### Fixed
- （初回リリースのためなし）

### Deprecated
- （初回リリースのためなし）

### Removed
- （初回リリースのためなし）

### Security
- 環境変数ファイル（.env）は絶対に Git にコミットしない旨を config_setup の出力に明示。

---

備考:
- 多くのコンポーネントは「純粋関数」設計（DB 参照なし）でテスト可能な形になっていることを意図しています（portfolio モジュールなど）。
- 実行時の挙動（データベースパス、環境、ログレベル 等）は環境変数で細かく制御できます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring/run_execution は停止フラグファイル（data/stop_requested.flag）と PID ファイルを用いた運用向けの仕組みを備えています。
- 本 CHANGELOG はコードベースから推測して作成した初期リリース記録です。実際のリリースノート作成時はコミット履歴やリリース作業内容に合わせて調整してください。