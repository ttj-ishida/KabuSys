# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 初回公開リリース。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動用エントリポイント。
    - KABUSYS_ENV=paper_trading 時はペーパートレード専用の SQLite（data/paper_trading.db、環境変数で上書き可）を使用し、本番 DB と分離。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 起動時にプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）を監視して安全に停止可能。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境に関わらず本番 sqlite_path を使用する仕様。
    - 停止フラグファイル検出でループを終了、KeyboardInterrupt にも対応。
- 設定管理・検証・セットアップ
  - config.py
    - .env の自動ロード（.env → .env.local、OS 環境変数を保護して上書き処理）。
    - .env パースの頑健化（export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメント処理など）。
    - Settings クラスを通じた環境変数アクセス（型変換・値検証を含む）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新。
    - シークレット項目は入力時にマスク表示、保存前に確認プロンプトあり。
  - validate_config.py
    - 起動前チェック CLI。必須環境変数、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス、config/*.yaml の存在・パース（PyYAML が利用可能な場合）を検証。
    - --strict オプションで警告をエラー扱いにできる。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - select_candidates（score 降順、同点は signal_rank でタイブレーク）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重、全スコア 0 の場合は等配分にフォールバック）
  - portfolio/risk_adjustment.py
    - apply_sector_cap（セクター集中上限を超える場合の候補除外、売却予定銘柄は除外して計算）
    - calc_regime_multiplier（market regime に応じた投下資金乗数。マッピング: bull=1.0, neutral=0.7, bear=0.3。未知レジームは警告して 1.0 にフォールバック）
  - portfolio/position_sizing.py
    - calc_position_sizes（risk_based / equal / score の配分方式をサポート、lot_size（単元）丸め、max_position_pct/max_utilization に基づく上限、aggregate cap のスケールダウンと残差配分ロジックを実装）
- ユーティリティ
  - utils/logging_setup.py
    - 統一ロギング設定関数 setup_logging を提供。コンソール（stdout）と日次ローテートファイルハンドラ（TimedRotatingFileHandler、30 日保持）を設定。
    - LOG_DIR が作成できない場合はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - set_process_priority と set_cpu_affinity を提供し、Windows/Linux/macOS の差分を吸収。権限エラー等は警告してスキップ。
- 監視・分析関連
  - monitoring_db の初期化を呼び出す処理を run_execution/run_monitoring に追加（監視テーブルの冪等な保証）。
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成ツール。
    - system_status / trade_logs / risk_logs から稼働率（uptime）、注文成功率（fill_rate）、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を表示。閾値（稼働率 99.0%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）をデフォルトで定義。
- 研究用スクリプト雛形
  - research/factor_research.py
    - DuckDB を使ったファクター計算（モメンタム / MA200 / ATR / 流動性等）の実装を想定した骨組みを追加（prices_daily / raw_financials に依存）。注：一部実装はファイル末尾で未完（スナップショットのため）。

### 変更 (Changed)
- ログ出力方針
  - StreamHandler を stdout に向ける（stderr ではなく、外部のリダイレクトを想定）。
- .env 自動読み込みの優先度
  - OS 環境変数 > .env.local（上書き）> .env（未設定時のみ設定）という明確なルールを採用。
  - OS 環境変数は protected として .env/.env.local の上書きを防止。

### 修正 (Fixed)
- .env 解析の改善
  - クォート付き値内のバックスラッシュエスケープ処理や、コメント検出の挙動を改善して .env の実用性を向上。

### ドキュメント (Documentation)
- 各モジュールにドクストリングと使用例を追加し、挙動や設計方針を明示。
- config_setup による .env テンプレート生成ロジック（_write_env）を追加し、各設定項目の説明とデフォルト値を明記。

### セキュリティ (Security)
- .env ファイルは絶対に Git にコミットしない旨の注記を config_setup の出力テンプレートに明記。
- 起動時の必須環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）は validate_config でチェックして未設定を検出可能。

### 既知の制限・注意点 (Known issues / Notes)
- research/factor_research.py は部分的に未完の実装が含まれる（スナップショット時点）。実際のファクター計算ロジックは追加実装が必要。
- position_sizing や apply_sector_cap は price の欠損（0 や None）に対するフォールバックが限定的であり、将来的に前日終値やマスタからのフォールバック価格導入を検討する旨の TODO が存在。
- process_priority / cpu_affinity は権限やプラットフォームの制約で失敗する可能性があり、その場合は警告を出して処理を続行する設計。

---

将来的なリリースでは以下を想定しています:
- research/factor_research の完成版実装と単体テスト追加
- ExecutionEngine / SystemMonitor の統合テストおよびブローカーモックの拡充
- 設定検証・ウィザードの出力をより詳細に（例: 検出された警告の改善手順提示）