CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。日付はこのコードスナップショットの作成日です。

Unreleased
----------

- なし

[0.1.0] - 2026-04-23
--------------------

Added
- 実行/監視ランナースクリプトを追加
  - run_execution.py: ExecutionEngine の起動スクリプト。KABUSYS_ENV に応じてペーパートレード用 DB を分離し、BrokerClientFactory 経由で Mock/実ブローカーを選択。PID ファイル管理、停止フラグ（data/stop_requested.flag）検出、デーモンスレッドでのエンジン実行制御を備える。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ検知で安全にループ終了。Monitoring は環境に依らず本番 sqlite_path を使用。

- 環境設定管理と自動ロード
  - config.py: .env / .env.local の自動読み込み機能（プロジェクトルート検出による）。export プレフィックス・クォートされた値のエスケープ処理・インラインコメント対応を含む堅牢な .env パーサ。Settings クラスにより環境変数をプロパティとして安全に取得（必須チェック付き）。
  - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START 等の設定プロパティを提供。KABUSYS_ENV / LOG_LEVEL の検証ロジックを実装。

- 設定用 CLI / ウィザード / 検証ツール
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する機能を追加。シークレット入力マスク、デフォルト値・選択肢の提示、保存確認機能を備える。
  - validate_config.py: 起動前に .env と config/*.yaml の整合性をチェックする CLI。必須環境変数チェック、パス存在チェック、PyYAML があれば YAML のパース検証、KABUSYS_ENV=live に対する追加ガード、--strict モード（警告を FAIL 扱い）をサポート。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite DB から稼働率、注文成功率、送信率、P95 レイテンシなどを集計してレポートを出力する CLI を追加。期間フィルタ、P95 計算、閾値に基づく PASS/FAIL 判定を含む。

- ポートフォリオ構築ユーティリティ（純粋関数群）
  - portfolio/portfolio_builder.py: シグナルのソート（スコア降順・タイブレーク）と候補選定、等金額・スコア加重の重み計算を追加。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を追加。未知レジームや unknown セクター時のフォールバックや警告ロジックを含む。
  - portfolio/position_sizing.py: 複数の配分方式（risk_based / equal / score）に対応した発注株数計算。単元株（lot_size）考慮、1銘柄上限・aggregate cap（可用現金に合わせたスケールダウン）、コストバッファを用いた保守的見積り、端数処理（lot 単位での再配分）を実装。

- ロギング・プロセス優先度ユーティリティ
  - utils/logging_setup.py: ルートロガーの初期化ユーティリティ。コンソール（stdout）と日次ローテートのファイルハンドラを設定。LOG_LEVEL / LOG_DIR の解決順を明確化。ログディレクトリ作成失敗時のフォールバック処理あり。
  - utils/process_priority.py: Windows/Linux/Mac の差を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを提供。psutil を用い、権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- データリサーチ基盤（骨格）
  - research/factor_research.py: モメンタム等ファクター計算のためのモジュール骨格を追加（DuckDB 経由で prices_daily / raw_financials を参照する設計）。P95 等の統計ユーティリティや計算レンジの定義あり。

- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

Changed
- なし（初期リリース相当）

Fixed
- .env パースの堅牢化
  - クォートされた文字列でのバックスラッシュエスケープ処理、export プレフィックス対応、インラインコメントの取り扱い、空行/コメント行のスキップ等を実装して .env のパースエラーを低減。

Security
- .env の生成テンプレート（config_setup の出力）に注意喚起を追加: .env を Git にコミットしない旨を明示。

Notes / Usage
- 実運用では KABUSYS_ENV を適切に設定（development/paper_trading/live）し、validate_config による事前検証を推奨。
- run_execution/run_monitoring をサービス化する際は stop flag（data/stop_requested.flag）や PID ファイルの扱いを運用手順に含めること。
- ログはデフォルト logs/ ディレクトリに日次ローテートで保存される（権限やディレクトリ作成失敗時はコンソール出力のみ）。

--- 

今後の改善案（実装候補）
- portfolio の lot_size を銘柄別に持てるよう stocks マスタとの連携
- position_sizing の価格欠損時（price=0）のフォールバックロジック強化
- research/factor_research の完全実装（Momentum/Value/Volatility/Liquidity の出力整備）
- monitor/engine の unit テストおよび起動時のナイス値/CPU affinity の OS 対応カバレッジ向上

※ 上記はソースコード内容から推測して作成した変更履歴です。実際のコミット履歴やリリースノートに応じて調整してください。