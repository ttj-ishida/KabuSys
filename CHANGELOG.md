CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。形式は「Keep a Changelog」に準拠しています。  

[Unreleased]
------------

- 特になし。

[0.1.0] - 2026-04-19
--------------------

初回リリース。自動売買システム KabuSys のコアユーティリティ、実行・監視用スクリプト、設定ツール、ポートフォリオ構築ロジック、検証ツール等を含む。

### 追加 (Added)

- アプリケーション設定・環境変数管理
  - 自動 .env ロード機能を実装（プロジェクトルートの検出: .git / pyproject.toml ベース）
  - .env / .env.local の読み込み、保護（OS環境変数の上書き防止）、自動無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）
  - Settings クラスを導入し、各種設定値（J-Quants トークン、kabuAPI、DB パス、Paper Trading 設定、監視閾値、環境種別、ログレベル等）をプロパティ経由で取得可能に
  - 環境変数の検証（値の妥当性チェック、必須項目の要求機能）

- 起動 / 管理用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離
    - BrokerClientFactory によるブローカークライアント生成（モック/実ブラウザ切替）
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み上げ、ExecutionEngine をデーモンスレッドで実行
    - 停止フラグ（data/stop_requested.flag）検出で安全に停止
    - 実行 PID ファイル管理（data/execution.pid）
    - RiskManager のデフォルト RiskConfig を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は KABUSYS_ENV にかかわらず production 相当の sqlite_path を使用（監視テーブルを一元管理）
    - 停止フラグでループ終了、例外時のログ出力とリトライ継続

- 設定検証・セットアップ CLI
  - validate_config.py
    - .env と config/*.yaml の事前検証ツールを追加（必須 env チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パス確認、YAML パースチェック、live 環境向けガード）
    - --strict オプションで警告をエラー扱いにできる
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新するツールを追加
    - デフォルト値、選択肢、シークレットマスク表示、保存確認を実装

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定
    - LOG_DIR / LOG_LEVEL / app_name による柔軟な設定、ログディレクトリ作成失敗時のフォールバック
  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定（Windows の priority class、POSIX の nice 値）
    - CPU affinity 設定ユーティリティ（最初の N コアに固定）
    - 権限不足や未対応 OS の際は警告ログを出してスキップ

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)
    - 等金額配分 (calc_equal_weights)
    - スコア重み配分 (calc_score_weights) — 全スコアが 0 の場合は等配分にフォールバック
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用 (apply_sector_cap) — 既存保有を基にセクター上限を判定し候補を除外
    - レジームに応じた資金乗数 (calc_regime_multiplier) — bull/neutral/bear のマッピングと未知レジームのフォールバック
  - portfolio/position_sizing.py
    - 株数決定ロジック (calc_position_sizes)
      - allocation_method による分岐: "risk_based" / "equal" / "score"
      - 単元株丸め（lot_size）、per-position 上限、aggregate cap（利用可能現金でスケールダウン）
      - cost_buffer による保守的な費用見積り、端数処理（lot 単位で残差配分）
      - 現在保有株数を考慮して追加発注量を算出

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - SQLite（Paper Trading DB）から集計して検証レポートを標準出力に生成
    - 指標: システム稼働率 (uptime%), 注文成功率 (fill_rate), 送信率 (send_rate), P95 レイテンシ等
    - 基準値（閾値）を定義し PASS/FAIL 判定を出力
    - --from / --to / --db オプションに対応

- 研究用モジュール（下流で DuckDB 使用）
  - research/factor_research.py（ファクター計算の枠組みを実装開始）
    - Momentum / Value / Volatility / Liquidity に関する計算方針といくつかの定数を定義
    - calc_momentum() 等の実装を開始（未完の箇所あり）

- パッケージ情報
  - パッケージ初期バージョン __version__ = "0.1.0"

### 変更 (Changed)

- （初回リリースのため該当無し）

### 修正 (Fixed)

- （初回リリースのため該当無し）

### 廃止 (Deprecated)

- （初回リリースのため該当無し）

### 削除 (Removed)

- （初回リリースのため該当無し）

### セキュリティ (Security)

- セキュリティ関連の設定は環境変数で外部化（シークレットは .env で管理、config_setup では .env を Git 管理しないよう注意書きを出力）

注意事項 / 備考
- run_monitoring.py は監視用 DB（sqlite_path）を環境に依らず使用するため、開発環境と本番環境で監視データの取り扱いに注意が必要です（コード内で明示的にその挙動が書かれています）。
- config._parse_env_line() はクォート、エスケープ、インラインコメントの取り扱いに対応する比較的堅牢な .env パーサを実装していますが、極端なケースで差異が出る可能性があります。
- research/factor_research.py は実装途中（ファイル末尾で calc_momentum の途中で切れている）ため、完全なファクター計算を行うには追加実装が必要です。
- BrokerClient の具象実装（モック/実ブローカー）や ExecutionEngine の内部実装はこのログには含まれていません（別モジュール）。Paper Trading と Live の DB 分離や fill_mode 等の設定により副作用の分離を図っています。

今後の予定（例）
- factor_research の完実装とユニットテスト追加
- ExecutionEngine / SystemMonitor の統合テストおよび稼働監視の強化
- 銘柄毎の lot_size マスタ対応、取引コストモデルの改善
- ドキュメント（API・運用手順）の整備

--- 

この CHANGELOG はコードベースから推測して作成しています。運用上の重要な変更・リリース日・バージョン管理は実際のリリース手順に合わせて適宜更新してください。