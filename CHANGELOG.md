# CHANGELOG

すべての注目すべき変更点を記録します。
このファイルは "Keep a Changelog" の形式に準拠します。

フォーマット:
- 変更はセマンティックバージョニングに従います。
- 日付はリリース日を示します。

## [0.1.0] - 2026-04-24

### Added
- 初期リリースを追加。KabuSys の基本的な実行・監視・設定・ポートフォリオ構築・検証ツール群を含む。
- 実行スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合に paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用する仕組みを実装。ペーパートレード時は本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成。MockBrokerClient を組み込める設計。
    - Engine の起動・停止をデーモンスレッドで行い、data/stop_requested.flag による外部停止フラグ検知をサポート。
    - 起動時に pid ファイルを書き込む仕組み（data/execution.pid を使用）。
    - RiskManager / Reconciler / OrderManager / OrderRepository を組み立てるワークフローを備える。RiskConfig のデフォルトパラメータを定義。
- 監視スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の sqlite_path を使う（監視データは共通で記録）。
    - data/stop_requested.flag による停止検知を実装。
- 設定管理
  - src/kabusys/config.py
    - 環境変数を扱う Settings クラスを追加。J-Quants / kabu API / DB /監視閾値 などをプロパティ化。
    - プロジェクトルート自動検出（.git / pyproject.toml）に基づく .env 自動読み込み機能を実装（.env → .env.local の順、OS 環境変数を保護）。
    - .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - PAPER_FILL_MODE の妥当性チェック、PAPER_TRADING_SQLITE_PATH など paper_trading 関連設定をサポート。
- 設定ウィザード / 検証ツール
  - src/kabusys/config_setup.py
    - 対話式 .env 作成/更新ウィザードを追加。主要な環境変数（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を対話的に設定して .env を生成。
  - src/kabusys/validate_config.py
    - 起動前検証 CLI を追加。必須環境変数や DB パス、config/*.yaml の存在・パースチェック（PyYAML がある場合）を行う。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）および TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティを追加。
    - LOG_LEVEL / LOG_DIR の解決順を実装し、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ行うフォールバックを備える。
    - stdout を採用（stderr ではなく）し、cron 等でのリダイレクト運用を考慮。
  - src/kabusys/utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定 (high/normal/low) と CPU affinity 設定ユーティリティを追加。Windows/Linux/macOS を吸収する実装。
    - アクセス権がない環境・未サポート環境では警告を出して安全にスキップする。
- ポートフォリオ構築ライブラリ
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナルのソート（スコア降順 + signal_rank によるタイブレーク）と候補選定 (select_candidates) を実装。
    - 等配分 (calc_equal_weights) およびスコア加重 (calc_score_weights) を実装。スコア全てが 0 の場合は警告を出して等配分へフォールバック。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap) を実装。既存ポジションのセクター比率に基づき当日新規候補の除外を行う。
    - 市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装（bull/neutral/bear のマッピング、未知レジームは警告のうえ 1.0 フォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に応じた発注株数計算を実装。
    - 単元株（lot_size）での丸め、per-stock 上限、aggregate cap（利用可能現金を超えた場合のスケーリング）を実装。cost_buffer を用いた保守的見積りにも対応。
- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite から集計し、稼働率・注文成功率・送信率・レイテンシ（P95）等を算出して PASS/FAIL 判定を行う。
    - P95 計算、日付フィルタ、欠損テーブル時の耐障害性を備える。
- リサーチ（ファクター計算）基盤
  - src/kabusys/research/factor_research.py（モジュール追加）
    - Momentum / Value / Volatility / Liquidity 等の定量ファクター計算方針を実装するためのベースを追加（DuckDB 接続を受け、prices_daily / raw_financials に基づく算出を想定）。
    - モメンタム計算関数 calc_momentum の実装開始（ファイル末尾で未完部分あり）。

### Changed
- ロギング構成の設計:
  - コンソール出力は stdout を使用するよう統一（cron/Task Scheduler での運用を考慮）。
  - 既存ハンドラがある場合は一旦 flush/close してから再設定することで二重出力を防止。
- .env 読み込みの振る舞い:
  - OS 環境変数を保護する protected 機構を導入し、.env.local の override を安全に行う実装に変更。

### Fixed / Robustness
- .env パーサ:
  - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの取り扱いを考慮したより堅牢なパースを実装。
- DB 初期化:
  - 監視用 DB の初期化関数 init_monitoring_db を呼び出し、監視テーブルが必ず存在するように（冪等に）保証。
- 起動/停止ハンドリング:
  - run_execution/run_monitoring で外部停止フラグ存在時に安全に起動を回避または停止する処理を追加。
  - KeyboardInterrupt を捕捉してクリーンに終了するハンドリングを追加。
- ログファイル出力失敗時のフォールバック:
  - ログディレクトリ作成やファイルハンドラ生成に失敗した場合でも、コンソール出力だけで継続できるようにした。

### Notes
- 現在のリリースは初期実装であり、いくつかの箇所は将来的な拡張を想定した TODO や注記が残されています（例: position_sizing の銘柄別 lot_size 対応、risk_adjustment の価格フォールバック、research モジュールの未完部分など）。
- config/*.yaml の内容検証は PyYAML がインストールされている場合のみ行われます。開発環境で YAML 検証を有効にする場合は PyYAML をインストールしてください。
- Monitoring は設計上「環境にかかわらず本番 sqlite_path を使用する」点に注意してください。必要に応じて環境変数で sqlite_path を切り替えて運用してください。
- セキュリティ: .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意書きあり）。

---

今後の予定（例）
- research/factor_research の完全実装（ファクター計算の SQL 最適化、Zスコア正規化）
- ExecutionEngine / Broker クライアントの詳細な統合テスト
- 単体テスト・CI の整備、設定例（.env.example）・運用ドキュメントの拡充

（この CHANGELOG はコードベースの内容を基に推測して作成しています。実際の変更履歴やリリース日等はプロジェクト運用に合わせて適宜修正してください。）