# Changelog

すべての変更は "Keep a Changelog" の形式に準拠して記載しています。  
このファイルはコードベースから推測して作成した初回リリース向けの変更履歴です。

全体方針:
- バージョンはパッケージ定義（src/kabusys/__init__.py の __version__）に合わせて 0.1.0 としています。
- 主要な追加機能・CLI・ユーティリティ・設計上の注意点を日本語でまとめています。

## [0.1.0] - 2026-04-20

### Added
- 基本アプリケーション構成と CLI を実装
  - Settings クラス (src/kabusys/config.py)
    - 環境変数から各種設定を取得するラッパーを提供
    - 自動 .env 読み込み機能を実装（プロジェクトルート(.git または pyproject.toml)検出に基づく）
    - .env/.env.local の読み込み時に OS 環境変数を保護する仕組みを導入
    - 必須/オプション設定や環境（development/paper_trading/live）・ログレベル等を扱うプロパティを提供
    - PAPER_FILL_MODE の検証や paper_trading 用 DB パスの分離用プロパティを実装

  - 環境設定ウィザード CLI (src/kabusys/config_setup.py)
    - 対話式で .env を生成・更新するウィザードを実装
    - シークレット入力のマスク表示、既存 .env の読み込み、保存前の確認などを提供
    - .env のテンプレート書き出し機能を実装（.env を決して Git にコミットしない旨の注意を付記）

  - 設定検証 CLI (src/kabusys/validate_config.py)
    - .env と config/*.yaml の前準備チェックを実行する CLI を追加
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パス親ディレクトリチェック、YAML パースチェック（PyYAML があれば）を実装
    - --strict オプションで警告を失敗扱いにするモードを提供

  - 起動スクリプト
    - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
      - KABUSYS_ENV=paper_trading 時は paper DB を利用し、本番 DB と分離（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能）
      - BrokerClientFactory を使ったブローカー抽象化、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立てとデーモンスレッド実行
      - 停止フラグファイル (data/stop_requested.flag) と実行 PID ファイル (data/execution.pid) を扱う制御
    - 監視ポーリング起動スクリプト: src/kabusys/run_monitoring.py
      - SystemMonitor の初期化とポーリングループを実装
      - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）
      - 監視モジュールは環境にかかわらず本番用 sqlite_path を使用する旨の設計

  - ユーティリティ群
    - ロギング設定ユーティリティ (src/kabusys/utils/logging_setup.py)
      - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定
      - LOG_LEVEL / LOG_DIR の解決ルールを実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続
    - プロセス優先度設定ユーティリティ (src/kabusys/utils/process_priority.py)
      - Windows / POSIX の差分を吸収してプロセス優先度 (high/normal/low) を設定
      - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（権限不足時には安全にスキップ）
      - 権限や未対応 OS の場合に警告を出してフォールバック

  - ポートフォリオ構築ライブラリ (src/kabusys/portfolio/)
    - portfolio_builder.py
      - select_candidates: スコア降順の銘柄選定（signal_rank によるタイブレーク）
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコア 0 の場合は等配分にフォールバック）
    - risk_adjustment.py
      - apply_sector_cap: セクター集中制限（既存保有比率が上限を超える場合、新規候補を除外）
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear とフォールバック）
    - position_sizing.py
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算、単元株丸め（lot_size）、aggregate cap によるスケールダウンと残差処理を実装

  - 研究用ファクター計算（骨格） (src/kabusys/research/factor_research.py)
    - モメンタム・移動平均・ATR・出来高等のファクター計算方針と定数を定義（DuckDB を使って prices_daily 等のテーブルを参照）
    - （実装の続きがある設計。DuckDB 接続を受け取るインターフェースを想定）

  - ペーパートレード検証レポートツール (src/kabusys/tools/paper_verification_report.py)
    - SQLite（PAPER_TRADING_SQLITE_PATH）からデータを読み取り、稼働率・注文成功率・送信率・APIレイテンシ（平均・最大・P95）等を集計してレポート出力
    - PASS/FAIL 判定閾値を定義（稼働率 99%、成功率 90% など）
    - --from / --to / --db オプションをサポート

### Changed
- （初回リリースのため「変更」は影響のある内部設計・デフォルト値の明文化）
  - ロギング: コンソール出力は stdout を使用（cron/Task Scheduler 等で stdout/stderr をまとめて扱う運用を考慮）
  - .env 自動読み込みの優先順位: OS 環境変数 > .env.local > .env、OS 環境は保護（上書き禁止）される仕様を採用

### Fixed
- 例外や環境不備時のフォールバックと安全弁を複数実装
  - MONITOR_POLL_INTERVAL が不正（0/負値/文字列）の場合は警告ログを出してデフォルト 60 秒にフォールバック
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時に処理が停止しないようにフォールバック
  - psutil による優先度設定や cpu_affinity 設定で権限不足や未実装の属性が発生してもワーニングを出してスキップ
  - validate_config: PyYAML 未インストール時は YAML パース検証をスキップして警告（fail にはしない）

### Security
- .env 管理上の注意を明記（config_setup にも .env を絶対に Git にコミットしない旨を記載）
- Settings._require() で必須環境変数が未設定の場合に明確なエラーを投げることで起動時の安全性を確保

### Notes / Known limitations
- research/factor_research.py はファクター計算の方針と一部の実装（定数・関数骨格）を含むが、ファイル末尾で実装が途中の箇所がある（ソース断片のため継続実装が必要）。
- apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合はエクスポージャーが過少見積もられる可能性があり、将来的にフォールバック価格（前日終値など）を導入することを想定。
- position_sizing:
  - lot_size は現状全銘柄共通で 100 を想定。将来的には銘柄別 lot_map を受け取る拡張を検討。
- run_monitoring は監視 DB に常に本番 sqlite_path を使う設計（モニタリング DB とトレード用 DB を分離しない構成では運用上の注意が必要）。

---

貢献・利用方法のヒント:
- 環境セットアップ:
  - まず python -m kabusys.config_setup を実行して .env を生成してください。
  - 生成後は python -m kabusys.validate_config で設定を検証してください。
- 実行:
  - 監視ループ: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時はコミットログ・実装差分を基に調整してください。）