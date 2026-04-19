# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠します。  
このファイルはリポジトリ内のコードから実装内容を推測して作成した初回リリース向けの変更履歴です。

なお、バージョン番号はパッケージ定義（kabusys.__version__ = "0.1.0"）に合わせています。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 基本アプリケーション構成
  - パッケージ初期化（kabusys）とバージョン情報を追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するためのエントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用し、MockBrokerClient を用いたペーパートレードをサポート。
    - 実行中の PID を data/execution.pid に記録する仕組み、停止フラグ（data/stop_requested.flag）による安全停止処理を実装。
    - 実行スレッドをデーモンスレッドで起動し、停止フラグ検知時に Engine.stop() を呼び出してシャットダウンする。
  - run_monitoring.py: SystemMonitor ポーリングループの起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視 DB は環境に依らず本番 sqlite_path を使用（監視テーブル初期化を行う）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了する。
- 設定管理
  - config.py: 環境変数および .env 自動読み込み機能を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により、CWD に依存しない .env の読み込み。
    - .env, .env.local の読み込み順と OS 環境変数の保護機能（上書き制御）。
    - Settings クラスでアプリケーションが利用する環境設定（DBパス、API トークン、監視閾値、環境種別など）をプロパティとして提供。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
- 設定ユーティリティ / CLI
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - 各種設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL、Kill Switch 等）のプロンプト・デフォルト・マスク表示に対応。
    - .env への書き出しテンプレートを提供。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数や KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML 利用可の場合）などを検証し、errors/warnings/infos を出力。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング & プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーへ設定。
    - LOG_DIR 環境変数や引数でログ出力先を制御。既存ハンドラの二重設定を防止する実装。
  - utils/process_priority.py: プロセス優先度（および CPU affinity）設定ユーティリティを追加。
    - Windows / POSIX の差分を吸収しつつ、"high"/"normal"/"low" の優先度設定を提供。
    - CPU affinity を最初の N コアに固定する関数を提供。
- Execution コンポーネントの骨子（実装を想定）
  - execution パッケージで BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の組み立て・起動フローを実装（run_execution.py から利用）。
  - RiskManager のデフォルト設定を実装（レート制限、サーキットブレーカー、最大ドローダウン等）。
- 監視（Monitoring）
  - monitoring.monitoring_db.init_monitoring_db を用いた監視テーブル初期化処理の呼び出しを導入（冪等）。
  - SystemMonitor の check_once() を定期実行し、例外耐性を持たせる構成。
- ポートフォリオ構築ライブラリ（portfolio）
  - portfolio/portfolio_builder.py:
    - 信号の候補選定（select_candidates: score 降順、タイブレークに signal_rank）を追加。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights、スコア合計が 0 の場合は等金額にフォールバック）を追加。
  - portfolio/risk_adjustment.py:
    - セクター集中制限 apply_sector_cap を追加（既存保有時価を基に上限チェック、"unknown" セクターは適用除外）。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear、未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - 複数方式の株数決定ロジックを実装（risk_based / equal / score）。
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に収めるためのスケーリングと端数配分）を実装。
    - 手数料・スリッページ見積り用の cost_buffer パラメータをサポート。
- ツール（tools）
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite から集計を行い、稼働率、注文成功率、送信率、レイテンシ（平均、最大、P95）等の指標を算出してレポート出力するスクリプトを追加。
    - 各種しきい値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を行う。
    - --from / --to / --db オプションで期間・DB パスを指定可能。
- リサーチ（research）
  - research/factor_research.py: ファクター計算モジュールの骨子を追加（Momentum / Value / Volatility / Liquidity の計算方針、DuckDB 接続を受ける設計）。モメンタム計算の実装開始（関数シグネチャ等）。

### 変更 (Changed)
- 環境変数読み込みポリシー
  - OS 環境変数を保護しつつ .env/.env.local を自動ロードする設計により、ローカル開発時の利便性を向上。
- ログ出力の標準化
  - 全ての起動スクリプトから setup_logging を呼ぶことでログ形式・ローテーション・出力先が統一されるように改善。
- DB 周り
  - monitoring 用の SQLite と分析用の DuckDB を用途に応じて使い分ける構成に整理（Execution は paper_trading 時に専用 SQLite を使用）。

### 修正 (Fixed)
- 環境変数パースの堅牢化
  - .env の解析ロジックでクォート／エスケープ／インラインコメント処理をサポートし、不正な行を無視する実装に改良。
- ポジションサイズ計算の端数処理
  - aggregate cap スケール後の端数処理で、lot_size 単位での再配分を行い利用可能現金を有効活用するロジックを導入。

### ドキュメント (Documentation)
- 各モジュール内に docstring と使い方コメントを追加。CLI の help メッセージや config_setup の対話ヘルプを整備。
- Portfolio / Strategy に関する設計注記（PortfolioConstruction.md / StrategyModel.md を参照）への言及をコード内コメントで保持。

### 既知の制限 (Known issues)
- research/factor_research.py はモメンタム等の関数定義が始まっているが、ファイル末尾（calc_momentum の続き）が途中で終わっている箇所があり、完全な実装は未完の可能性がある。
- apply_sector_cap の価格欠損（price が 0.0 の場合）によりエクスポージャーが過少見積もられる可能性があり、将来的にフォールバック価格導入を検討する旨の TODO が残っている。
- process_priority/set_cpu_affinity は権限不足やプラットフォーム差分により失敗するケースを警告してスキップするが、運用環境では注意が必要。

---

今後のリリースでは以下を想定しています（実装方針のメモ）:
- research/factor_research の完全実装と単体テスト追加
- ExecutionEngine 周りの詳細なログ・メトリクス強化
- 単体テスト・CI ワークフローの追加
- config/*.yaml を用いた各種パラメータの外部化とバリデーション強化

--- 

（この CHANGELOG はコードの現状から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。）