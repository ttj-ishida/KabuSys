# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-04-23

### 追加 (Added)
- プロジェクト初版リリース。
- 実行用スクリプトを追加:
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は専用の MockBrokerClient を使用し、paper_trading 用 SQLite（環境変数 / デフォルト: data/paper_trading.db）に記録することで本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) と実行 PID ファイル (data/execution.pid) の取り扱いを実装。
    - ExecutionEngine をバックグラウンドスレッドで実行し、停止フラグ検知時に安全に停止する仕組みを提供。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（不正値はデフォルトにフォールバックし警告を出力）。
    - Monitoring は環境にかかわらず本番の sqlite_path を使用する（注: 意図的に本番 DB を参照）。
    - 停止フラグ検知でループを終了し、例外発生時はロギングして次ポーリングへ復帰。
- 設定管理:
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env/.env.local のマージロード（OS 環境変数の保護あり）。
    - 複雑な .env パース実装（export 対応、シングル/ダブルクォート、エスケープ、インラインコメント処理）。
    - Settings クラスを実装し、各種設定値（DB パス、API トークン、PAPER_FILL_MODE の検証など）をプロパティ経由で取得可能。
- 設定関連 CLI:
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - 入力時に既存値の再利用、マスク表示（シークレット項目）などを実装。
  - validate_config.py
    - .env と config/*.yaml の事前検証ツール。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、PyYAML があれば YAML のパース検証、KABUSYS_ENV=live 向けの追加ガードを実装。
    - --strict モードで警告を FAIL 扱いにできる。
- ツール:
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプト。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を集計・判定（閾値付きの PASS/FAIL 判定）。
    - 日付レンジ指定 (--from / --to) に対応、データが存在しない場合の耐性を実装。
- ポートフォリオ構築関連（純粋関数群、DB 非依存）:
  - portfolio/portfolio_builder.py
    - 銘柄選定（スコア降順、タイブレークの signal_rank）と等重 / スコア加重の重み計算を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
    - 未知レジーム時のフォールバックと警告出力を実装。
  - portfolio/position_sizing.py
    - risk_based / equal / score の割当方式に対応した株数決定ロジックを実装。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料/スリッページ見積）の考慮、aggregate cap によるスケーリング（割合に基づくスケールダウンと端数処理）を実装。
    - 現在値・価格欠損時のログ出力とスキップ処理を実装。
- ユーティリティ:
  - utils/logging_setup.py
    - ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（daily ローテーション, 30 日保持）を設定する共通関数を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定を実装（psutil ベース）。
    - 権限不足等で設定できない場合は警告を出して安全にフォールバック。
- リサーチ:
  - research/factor_research.py
    - モメンタム / ボラティリティ / Value / Liquidity 等のファクター設計を開始。DuckDB 接続を受け取って prices_daily / raw_financials を参照する設計方針を定義。
    - モメンタム計算（calc_momentum）の骨組みを実装（注意: ファイル末尾で実装が途中で切れている箇所あり、詳細は既知の問題参照）。

### 変更 (Changed)
- 初版のため該当なし。

### 修正 (Fixed)
- 初版のため該当なし。

### 破壊的変更 (Removed)
- 初版のため該当なし。

### セキュリティ (Security)
- 初版のため該当なし。

---

## 既知の問題 / TODO
- research/factor_research.py の calc_momentum 実装がファイル末尾で途中 (ソースが切れている) ため、モメンタム計算の完全な実装は未完。今後のリリースで完了予定。
- portfolio/position_sizing.py:
  - lot_size を銘柄毎に扱う拡張（銘柄マスタ経由）は TODO。現状は全銘柄共通の lot_size を想定。
- portfolio/risk_adjustment.py:
  - apply_sector_cap 内の価格欠損（price == 0.0）時にエクスポージャーが過少見積りされる可能性あり。将来的に前日終値などのフォールバック価格導入を検討。
- .env 自動読み込みはプロジェクトルート検出に依存するため、配布後や特殊な配置では自動ロードをスキップする場合がある（KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して制御可能）。
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用する」設計のため、development 等で実行すると本番 DB を参照・更新する可能性があります。実行時は環境変数設定に注意してください。
- PAPER_FILL_MODE やその他の環境変数は厳密な値チェックを行うため、設定ミス時は起動時に例外を投げます。validate_config を事前実行することを推奨します。

---

今後の予定:
- research モジュールのファクター実装完了と単体テスト追加。
- ExecutionEngine / Monitoring 周りの統合テストと運用監視向けの改善（ログ、メトリクス、アラート連携）。
- 銘柄別単元情報や手数料モデルを取り入れた position sizing の精緻化。