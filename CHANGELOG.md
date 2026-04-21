# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  
リリース日はソースコードから推測可能な範囲で記載しています。

全般的な注意:
- 環境変数は .env または OS 環境変数から読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- DuckDB / SQLite を組み合わせたローカル DB を使用する設計になっています。
- ペーパートレードは本番 DB と分離され、専用の SQLite を利用します。

## [Unreleased]
- 開発中 / 未リリースの変更はここに記載します。

## [0.1.0] - 2026-04-21
初回公開相当の機能セットを追加。

### Added
- 実行・監視ランナー
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用。
    - 起動時にプロセス優先度を "high" に設定する仕組みを導入。
    - 停止制御に project_root/data/stop_requested.flag を使用。停止時はエンジンを安全に停止。
    - 実行中 PID を data/execution.pid に書き込む想定の設定をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用（監視 DB は production path を参照）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
- 設定管理
  - config.py: 環境変数 / .env 自動読み込み機能を実装。
    - プロジェクトルートを .git または pyproject.toml で探索して自動ロード。
    - クォート / エスケープ / コメントを考慮した .env パーサを実装。
    - 必須環境変数取得用の _require と Settings クラスを提供。設定項目（DB パス、API トークン、監視閾値、環境種別など）をプロパティで取得可能。
  - config_setup.py: 対話式 wizard による .env 作成/更新ツールを追加。
    - J-Quants / kabu API / DuckDB / SQLite / LINE / ログレベル / Kill Switch 等を対話的に設定。
    - 既存 .env の読み込み、シークレット値のマスク表示、書き込みテンプレートを提供。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、DB パス・親ディレクトリチェック、YAML の存在確認と（PyYAML があれば）パース検証、live 環境向けの追加ガード。
    - --strict フラグで警告をエラー扱いにするオプションあり。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一されたログセットアップを追加。
    - StreamHandler を stdout、TimedRotatingFileHandler（日次・30日保持）をファイルへ設定。
    - LOG_DIR 作成失敗時はファイル出力をスキップして stdout のみで継続するフォールバックを実装。
    - ログレベル・ログディレクトリの解決順をサポート（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定を追加。
    - Windows/Linux/macOS を吸収して nice / priority を設定（失敗時は警告ログでスキップ）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（権限不足時は警告でスキップ）。
- Execution コンポーネント骨格（インジェクション可能な実装を想定）
  - execution 内のファクトリ・エンジン・オーダ管理・リスク管理・突合せなどのコンポーネントを組み立てる起動処理を実装（BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等を使用）。
  - RiskManager の既定設定をコード上に定義（max_position_pct=0.20, max_utilization=0.80 等）し、初期ポートフォリオ値に broker.get_available_cash() を使用。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点時は signal_rank）で上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア重み配分（スコア合計が 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター別エクスポージャ計算に基づき、新規候補からセクター上限超過のものを除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金マルチプライヤを提供（未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に応じた発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウンと端数配分）を実装。
    - cost_buffer（手数料・スリッページ見積り）を考慮した保守的な金額試算を実装。
- Paper Trading ツール
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計。
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し PASS/FAIL を判定。
    - --from / --to / --db CLI オプションをサポート。
- research/factor_research.py（ファクター計算の骨組み）
  - momentum 等のファクター計算の設計と定数を導入（期間定義、スキャンバッファ等）。DuckDB 接続を受ける設計。

### Changed
- なし（初回リリースのため該当なし）。

### Fixed
- なし（初回リリースのため該当なし）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- 環境変数の .env は自動生成される想定だが、.env を Git にコミットしないよう README/テンプレートに注意する（config_setup の注記あり）。

### Notes / Limitations / TODO（ソース内コメントより）
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャが過少見積りされる可能性があり、将来的に前日終値等でフォールバックすることを検討する旨の TODO がある。
- portfolio/position_sizing:
  - 将来的に銘柄別 lot_size をサポートする案（stocks マスタの導入）がコメントされている。
- utils/logging_setup:
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続するフォールバック実装あり。
- research/factor_research.py:
  - ファイルの一部（calc_momentum の実装途中）が未完の状態。研究モジュールは設計骨子が中心で、完全実装は今後。

---

(注) 本 CHANGELOG は提供されたソースコードからの推測に基づき作成しています。実際のリリースノートとして使用する場合は、実装・テスト状況やドキュメントと照合のうえ適宜修正してください。