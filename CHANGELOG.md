# CHANGELOG

すべての重要な変更を記載します。本ファイルは「Keep a Changelog」形式に準拠します。

現在のバージョン: 0.1.0 — 2026-04-23

## [0.1.0] - 2026-04-23

初回リリース。本リポジトリは日本株自動売買システム「KabuSys」の基盤機能群を提供します。主な追加点は以下のとおりです。

### 追加 (Added)
- コアパッケージ構成
  - kabusys パッケージの初期化とバージョニング（`__version__ = "0.1.0"`）。
- 実行関連スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度を上げ、SQLite / DuckDB に接続してエンジンをデーモン的に起動。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、PID ファイル / 停止フラグ（data/execution.pid, data/stop_requested.flag）に対応。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用する設計。
    - 停止フラグ検知・例外ハンドリング・リソースクローズを備える。
- 設定・環境管理
  - config.py
    - 環境変数ラッパー Settings を追加。各種環境変数（J-Quants, kabu-api, DB パス, モードフラグ等）をプロパティ経由で取得。
    - .env 自動読み込み機構を追加（プロジェクトルート検出 .git / pyproject.toml 基準）。.env, .env.local の読み込みと OS 環境変数の保護対応。
    - .env パースはクォート・エスケープ・インラインコメントに対応する堅牢な実装。
    - 各種バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
  - config_setup.py
    - .env 初期作成・更新のための対話式ウィザードを追加。既存 .env の読み込み・マスク表示・確認後書き込みを行う。
  - validate_config.py
    - 起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV、DB パス、config/*.yaml の存在と YAML パース（PyYAML があれば）などをチェック。--strict オプションで警告をエラー扱いにできる。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 共通のログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加。Windows / POSIX を吸収して set_process_priority(level) を提供。CPU affinity 固定用 set_cpu_affinity も実装。権限や未対応環境では警告ログでスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等重み (calc_equal_weights)、スコア加重 (calc_score_weights) を追加。スコアが全て 0 の場合は警告を出して等重みへフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限適用関数 (apply_sector_cap) と市場レジームに応じた乗数計算 (calc_regime_multiplier) を追加。未知レジームは 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - 株数算出関数 (calc_position_sizes) を追加。allocation_method により "risk_based" / "equal" / "score" をサポート。単元株丸め、ポジション上限、aggregate cap（スケーリング）および cost_buffer による保守的見積りを実装。
  - portfolio/__init__.py で上記機能を公開。
- モニタリング関連
  - monitoring_db 初期化呼び出しを実行スクリプトから行う（init_monitoring_db を起動時に確保）。
  - SystemMonitor との統合により定期的な状態チェックが可能。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証用レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH を参照し、期間指定（--from/--to）でシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計。既定の合格基準（稼働率 >= 99%、成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）に基づく PASS/FAIL 判定を出力。
- リサーチ
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの骨組みを追加。モメンタム、移動平均乖離、ATR、流動性等の計算設計が記載され、calc_momentum の実装開始（未完）。

### 変更 (Changed)
- なし（初回リリースのため変更履歴はありません）

### 修正 (Fixed)
- 例外や環境不備に対する堅牢性を強化
  - .env 読み込み失敗時に警告を出してスキップするように設計。
  - MONITOR_POLL_INTERVAL の不正値は警告してデフォルトにフォールバック。
  - ログディレクトリ作成やファイルハンドラ生成に失敗した際にコンソールログにフォールバック。
  - process_priority の権限不足や未サポート OS では処理をスキップし、警告ログのみ出す。

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- なし

---

注記:
- 各モジュールは外部リソース（DuckDB, SQLite, kabu API, J-Quants 等）に依存します。運用環境では .env の設定と config/*.yaml の整備を必ず行ってください。
- research/factor_research.py や一部関数には TODO コメントや未実装部分があり、今後の実装・改善が予定されています。