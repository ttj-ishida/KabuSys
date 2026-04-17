# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。  

リンクやコミットハッシュは含めていません（コードベースから推測して作成）。

## [0.1.0] - 2026-04-17

初回リリース。システム全体のコア機能（実行エンジン、監視、設定管理、ポートフォリオ構築、ユーティリティ、レポートツールなど）を導入しました。

### 追加 (Added)
- 実行エンジン起動スクリプト
  - run_execution.py を追加。ExecutionEngine をスレッドで起動し、停止フラグ（data/stop_requested.flag）で安全停止を行う。
  - KABUSYS_ENV=paper_trading の場合に MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を利用して本番 DB と分離する動作を実装。
  - 起動時にプロセス優先度を "high" に設定する機能（utils.process_priority.set_process_priority を使用）。
  - execution.pid を出力するための pid_file サポート。
  - OrderRepository, OrderManager, Reconciler, RiskManager（RiskConfig を含む）を組み立てて ExecutionEngine を起動。

- 監視ポーリング起動スクリプト
  - run_monitoring.py を追加。SystemMonitor をポーリングするループを提供。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
  - 監視は環境に関わらず本番の sqlite_path を使用する設計（コメント表記あり）。
  - 停止フラグ検知でループ終了、例外発生時はログ出力して次回ポーリングへ継続。

- 設定・環境変数管理
  - config.py: Settings クラスを導入し、環境変数から各種設定値を取得する共通インターフェースを提供。
  - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動ロード機能を実装（.env → .env.local の順で読み込み、OS 環境変数は保護）。
  - .env パースの強化: export プレフィックス、クォート（シングル/ダブル）、エスケープ、インラインコメントの扱いに対応。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値チェックを実装し、不正値で例外を送出する（安全性向上）。

- 設定ウィザード CLI
  - config_setup.py を追加。対話式ウィザードで .env の初期作成／更新を支援。機密値はマスク表示、確認後に .env を書き出す。

- 設定検証 CLI
  - validate_config.py を追加。.env および config/*.yaml の不足や不整合を起動前に検出するツールを提供。--strict モードで警告も失敗（exit 1）扱いにできる。
  - PyYAML が無ければ YAML 検証をスキップし警告する仕組み。ライブ環境向けの追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START）を実装。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等配分 calc_equal_weights、スコア加重 calc_score_weights を実装。スコア全0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、マーケットレジームに基づく乗数 calc_regime_multiplier を実装（既知レジームのマップ、未知時は 1.0 でフォールバック）。
  - portfolio/position_sizing.py: allocation_method = "risk_based" / "equal" / "score" に対応した発注株数計算。単元株（lot_size）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap のスケーリングおよび端数処理を実装。

- 研究／ファクター計算
  - research/factor_research.py: DuckDB 接続を用いるモメンタム（1M/3M/6M、MA200乖離）およびボラティリティ系ファクターの計算関数を提供。prices_daily テーブルを前提とした設計。

- レポートツール
  - tools/paper_verification_report.py を追加。紙トレード DB（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計し、閾値に基づく PASS/FAIL レポートを出力する。P95 の計算、日付フィルタ、データ欠損時の N/A 表示などに対応。

- ユーティリティ
  - utils/process_priority.py: set_process_priority（Windows / POSIX 対応、失敗時は警告）と set_cpu_affinity（最初の N コアに固定、無効時は警告）を実装。プラットフォーム差分を吸収。

- パッケージ情報
  - __init__.py にて __version__="0.1.0" を設定。

### 変更 (Changed)
- .env 自動読み込みの優先順位を明確化: OS 環境変数 > .env.local > .env。OS 環境変数は protected として .env/.env.local による上書きを防止。
- .env 読み込み失敗時は warnings.warn で通知してプロセスを継続するようにして起動の堅牢性を向上。
- run_monitoring にて異常発生時もループを継続させるために例外をキャッチしてログに残す設計。

### 修正 (Fixed)
- MONITOR_POLL_INTERVAL の不正値（0 や負数、非数）での time.sleep 呼び出しによる例外を防ぐため、不正値時にデフォルトへフォールバックして警告を出す実装を追加。
- position_sizing のスケーリングで端数処理・単元株丸めに関する挙動を明確化し、残余キャッシュを使って安定的に lot_size 単位で配分するロジックを導入。
- process_priority / set_cpu_affinity が権限不足や未サポート環境でクラッシュしないよう例外を捕捉し警告でスキップするように変更。

### セキュリティ (Security)
- config_setup で生成される .env ファイルに関して、「.env は絶対に Git にコミットしないこと」を明示。機密値は対話時にマスク表示。
- Settings._require() により必須環境変数未設定時は早期に ValueError を投げ、誤設定で実行を続けないようにした。

### 注意事項 / 既知の制約 (Notes / Known issues)
- run_monitoring のドキュメントにある通り、監視は環境設定（KABUSYS_ENV）に関わらず sqlite_path を本番設定として使用する設計になっています。運用時は sqlite_path の値に注意してください。
- portfolio/risk_adjustment.apply_sector_cap は price_map に欠損（0.0）がある場合にエクスポージャーが過小評価される可能性があり、将来的にフォールバック価格を導入することを想定した TODO コメントがあります。
- research/factor_research のボラティリティ部分はファイル内で処理が続いていますが、外部データ・テーブルの前提（prices_daily, raw_financials）が必要です。
- 一部モジュール（ExecutionEngine、SystemMonitor、BrokerClientFactory 等）は本 CHANGELOG 作成時点で他ファイルに依存しており、実際の挙動はそれらの実装に依存します（ここでは存在を前提に説明しています）。

---

今後のリリースでは、テストカバレッジ、ドキュメント整備、個別コンポーネント（エンジン・ブローカー・モニタ）の詳細改善、エラーハンドリングの強化などを予定しています。必要であれば各モジュールごとの詳細な変更点や設計意図の追記版 CHANGELOG を作成します。