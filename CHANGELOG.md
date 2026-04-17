# CHANGELOG

すべての変更は Keep a Changelog（https://keepachangelog.com/）の形式に従って記載しています。  
このファイルはコードベースから推測して作成した変更履歴です。

## [Unreleased]

- ドキュメント・内部注釈の整理（コード内 docstring の明確化、使用例追加等）
- 小さなログやデバッグメッセージの改善（詳細は各ファイル参照）

## [0.1.0] - 2026-04-17

初回リリース（コードベースの主要機能を追加）。

### 追加 (Added)
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。スレッドでエンジンを実行し、data/execution.pid に PID を書き込む仕組みおよび data/stop_requested.flag による停止ハンドルを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
- 環境・設定管理
  - config.py: Settings クラスを導入。環境変数 / .env の自動ロード（.env, .env.local の優先度）、必須値チェックや各種設定プロパティ（DB パス、KABUSYS_ENV、PAPER_FILL_MODE など）を提供。
  - config_setup.py: 対話式ウィザードにより .env を初期作成・更新する CLI を追加。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。--strict オプションで警告を FAIL 扱いにできる。
- Paper Trading / 分離
  - Execution の paper_trading モードに対応。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用（BrokerClientFactory を参照）、Paper 用 SQLite（デフォルト data/paper_trading.db）にデータを記録して本番 DB から完全分離。
  - 設定項目 PAPER_FILL_MODE を導入（instant/partial/never/reject）。
- 監視・モニタリング
  - monitoring_db の初期化呼び出しを run_monitoring/run_execution の起動フローに追加（冪等に監視テーブルを保証）。
  - run_monitoring は実行環境に関わらず本番 sqlite_path を使用する設計（監視は常に本番データに対して行う意図）。
- 分析・レポート
  - tools/paper_verification_report.py: Paper Trading の検証レポート出力ツールを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを計算し PASS/FAIL 判定を行う。閾値はソース内で定義（稼働率>=99%、fill>=90%、send>=95%、P95<=200ms）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
  - portfolio/position_sizing.py: position sizing ロジックを追加。risk_based / equal / score の割当方式、lot_size（単元株）丸め、aggregate cap によるスケールダウン、cost_buffer の考慮などを実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を追加。未知レジームやスコア全0 の場合のフォールバック挙動を定義。
  - portfolio/__init__.py: 上記 API をエクスポートするパッケージエントリポイントを追加。
- 研究・ファクター計算
  - research/factor_research.py: DuckDB を用いたファクター計算ユーティリティ（calc_momentum, calc_volatility など）を追加。prices_daily / raw_financials を参照してモメンタム、ATR、売買代金等を算出する設計。
- ユーティリティ
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を追加。Windows/Linux/Mac の差分を吸収しつつ例外時は警告でフォールバック。
- パッケージメタ
  - __init__.py: パッケージバージョン __version__="0.1.0" を設定。

### 変更 (Changed)
- .env 読み込みロジック
  - export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理などをサポートするようパーサを強化（config._parse_env_line）。
  - 自動ロード順序は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - 環境変数ロード時に OS 環境変数を保護する protected 引数を導入（.env.local の上書きでも OS 環境を維持）。
- 設定検証の強化
  - validate_config.py で必須環境変数チェック、KABUSYS_ENV の妥当性チェック、DB パスの親ディレクトリ存在の警告、config/*.yaml の存在/パース確認（PyYAML 未導入時はスキップ）を実装。
- 安全性・運用上の配慮
  - run_execution/run_monitoring 起動時にプロセス優先度を最初に high に設定するように変更（set_process_priority 呼び出し）。
  - run_execution は停止フラグ（data/stop_requested.flag）検知時に起動を回避、実行中に検知したら engine.stop() を呼び安全に停止するフローを整備。
- ログと例外処理
  - run_monitoring のポーリングループで monitor.check_once() の例外を捕捉してログ出力し、ループは継続するように安全化。
  - 環境変数の不正値や閾値設定ミスに対しては ValueError を発生させ明示的に検出できるように（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。

### 修正 (Fixed)
- 環境変数パースの不具合を修正（コメント/クォート/エスケープの扱い改善）。
- position sizing のスケールダウンロジックにおける端数分配ロジックを実装し、残余キャッシュ利用時に安定して lot 単位で配分するように改善。
- paper_verification_report: データ欠如時に sqlite の OperationalError を捕捉してレポート生成を継続するように修正（DB テーブルが存在しない場合でもエラーを出さず N/A として扱う）。

### 破壊的変更 (Breaking Changes)
- 監視モジュール（run_monitoring）は KABUSYS_ENV に関わらず「本番の sqlite_path」を使用する仕様になっています。運用環境によっては監視 DB を明示的に分離する必要があるため注意してください。
- Paper Trading 時は MockBrokerClient と別 DB（PAPER_TRADING_SQLITE_PATH）を使用するため、本番 DB と完全に分離されます。既存運用で同一 DB を期待している場合は設定を見直してください。

### ドキュメント・運用上の注意 (Notes)
- .env ファイルは絶対にバージョン管理にコミットしないこと（config_setup のヘッダにも注記あり）。
- validate_config の --strict モードは警告も失敗扱いにするため、本番チェック時に推奨。
- process_priority や CPU affinity の設定は OS や権限に依存し、権限不足等の場合は警告を出してスキップします。
- paper_verification_report の閾値はツール内部に定義されているため、要件に応じて調整してください。

---

この CHANGELOG はコード内の docstring、関数名、CLI 実装、環境変数やファイルパスの取り扱いなどから推測して作成しています。実際のコミット履歴や発表用リリースノートと差異がある場合があります。