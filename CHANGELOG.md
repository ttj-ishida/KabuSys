# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。  
日付はリリース時点の推定日付を付与しています。

## [Unreleased]
- （現在のコードベースでは未リリースの作業なし）

## [0.1.0] - 2026-04-22
初回リリース。以下の主要機能とユーティリティを実装しました。

### Added
- 実行エントリスクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - スレッドベースで ExecutionEngine のセッションを実行し、外部停止フラグ（data/stop_requested.flag）を監視して安全に停止可能。
    - KABUSYS_ENV=paper_trading のときは paper_sqlite_path（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離する設計。
    - ブローカークライアントは BrokerClientFactory によって生成（paper_trading 時は MockBroker の使用が想定）。
    - デフォルトでプロセス優先度を "high" に設定。
    - PID ファイル管理（data/execution.pid）に対応。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値は警告のうえデフォルトへフォールバック。
    - 監視用 DB は環境にかかわらず production の sqlite_path を使用して監視データを一元化。
    - 停止フラグ（data/stop_requested.flag）検知、例外時のログ出力、KeyboardInterrupt ハンドリングを実装。

- 設定管理・ユーティリティ
  - config.py
    - Settings クラスによる環境変数経由の設定管理を追加。プロパティベースで各種設定を取得。
    - .env 自動読み込み機能を追加（プロジェクトルートの検出: .git / pyproject.toml を探索）。OS 環境変数を保護して .env/.env.local を読み込む仕組みを実装。
    - .env のパースはシングル/ダブルクォート、export KEY=val、インラインコメント、エスケープシーケンス等に対応。
    - 各種設定の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を行う。

  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。
    - セクション分けされたテンプレート出力（J-Quants, kabu API, LINE, DB, system 設定, kill switch）。
    - シークレット項目のマスク表示・既存値の再利用機能を提供。

  - validate_config.py
    - 起動前に .env と config/*.yaml の検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML があれば）を行う。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群・テストしやすい実装）
  - portfolio/portfolio_builder.py
    - 候補選定: signal をスコア降順、同スコア時は signal_rank 昇順でタイブレークして上位 N を選択。
    - 等金額配分、スコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）を実装。

  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装。既存保有のセクターエクスポージャを算出し、上限超過セクターの新規候補を除外。
    - unknown セクター（マップにない銘柄）はセクター上限の対象外。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームはフォールバック且つ警告）。

  - portfolio/position_sizing.py
    - 株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - risk_based: 許容リスク率・損切り率を用いた株数算出。
    - equal/score: 各銘柄の重みと portfolio_value から算出。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、総投下上限（max_utilization）対応。
    - cost_buffer を考慮した conservative なコスト見積りと、利用可能現金を超えた場合のスケールダウン（端数処理で残差順に再配分）を実装。

- モニタリング関連
  - monitoring_db 初期化を呼び出すユーティリティを各起動スクリプトで使用（冪等に監視テーブルを保証）。
  - utils/process_priority.py によるクロスプラットフォームの優先度設定（Windows / POSIX 対応）、CPU affinity 設定関数を実装。失敗時は警告ログでフォールバック。

- ロギング
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに統一的に設定するユーティリティを追加。
    - LOG_DIR 環境変数または引数でログ出力先を指定。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

- ツール類
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計して人間向けレポートを出力。
    - デフォルト閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し PASS/FAIL を判定。
    - 日付フィルタ（--from / --to）、DB 指定（--db / 環境変数）に対応。

- 研究（未完のファイルあり）
  - research/factor_research.py
    - DuckDB からの価格・財務データ参照を想定したモメンタム/Value/Volatility/Liquidity ファクター計算モジュールの骨組みを追加（calc_momentum 等の実装開始）。
    - 設計方針として DuckDB 接続受け取り・テーブル参照のみで副作用を起こさない純関数にすることを明記。

### Changed
- 初回リリースのため変更履歴なし（初期実装）。

### Fixed
- 初回リリースのため既知のバグ修正履歴なし。

### Deprecated
- なし

### Removed
- なし

### Security
- .env ファイルは絶対に Git にコミットしない旨を config_setup のテンプレートに明記（運用上の注意）。

---

Notes / 備考
- 設定読み込みは自動で .env（および .env.local）をプロジェクトルートから読み込みますが、テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- run_monitoring は監視用 DB として settings.sqlite_path を常に使用する点、run_execution は paper_trading モードで専用 DB を使う点に注意してください（本番 DB とログの分離を意図）。
- 将来的な改善候補（TODO）:
  - position_sizing の価格欠損時フォールバック（前日終値や取得原価など）を導入。
  - factor_research の各ファクター実装の完了とテストカバレッジ拡充。
  - ExecutionEngine / SystemMonitor の詳細実装・エラーハンドリング強化（現状は起動/ループの骨組みが中心）。

もしリリース日やバージョン番号を変更したい場合、またはより細かいログ（コミット単位）を含めたい場合は指示してください。