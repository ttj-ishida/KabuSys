# Changelog

すべての注記は Keep a Changelog のガイドラインに準拠しています。  
この CHANGELOG はコードベースの実装内容から推測して作成しています（実際のコミット履歴ではありません）。

## [Unreleased]

### Added
- ニュースNLP スコアリング機能を追加（kabusys.ai.news_nlp）
  - raw_news / news_symbols から記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む。
  - バッチ処理（1回あたり最大 20 銘柄）、最大記事・文字数制限、スコアのクリップ、API リトライ（指数バックオフ）などを実装。
  - ニュース収集ウィンドウ計算（JST基準の前日15:00〜当日08:30 を UTC に変換）を提供。
- Paper Trading 検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）
  - 指定期間の system_status / trade_logs / risk_logs を集計し、稼働率・注文成功率・送信率・レイテンシ（P95）等を出力。
  - PASS/FAIL 判定、閾値は定数で定義（稼働率 99%、P95 レイテンシ 200 ms など）。
  - CLI 引数で期間と DB パスを指定可能。
- リサーチモジュールを拡充（kabusys.research）
  - factor_research: Momentum / Volatility / Value ファクター計算を DuckDB 経由で実装。
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、ランク関数等を実装。
  - research パッケージのエクスポート（zscore_normalize 等）を整理。
- ポートフォリオ構築モジュールを追加/拡張（kabusys.portfolio）
  - portfolio_builder: 候補選定（スコア順）、等重・スコア加重の重み計算を実装。スコアが全て 0 の場合のフォールバック警告あり。
  - risk_adjustment: セクター集中制限（apply_sector_cap）および市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジームは警告して 1.0 でフォールバック。
  - position_sizing: risk_based / equal / score の各配分方式に基づく株数計算、単元株丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した安全な配分ロジックを実装。
- 実行・監視用起動スクリプトを追加
  - run_execution: ExecutionEngine 起動フローを実装。KABUSYS_ENV=paper_trading 時は paper_sqlite_path（data/paper_trading.db デフォルト）を使用し本番 DB と分離。プロセス優先度設定・DuckDB 接続・各コンポーネント組み立て（Broker, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を実施。
  - run_monitoring: SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する旨を明記。
- 設定管理の改善（kabusys.config）
  - .env 自動読み込み時のファイル探索を __file__ ベースで実装（プロジェクトルート検出: .git または pyproject.toml）。
  - .env パーサの強化（export 書式対応、シングル/ダブルクォート内エスケープ処理、インラインコメントの扱い、override/protected オプション）。
  - 環境変数の検証ロジックを追加（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）。いくつかのプロパティにデフォルト値と検証処理を実装。
  - 自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
- プロセス優先度 / CPU affinity ユーティリティを追加（kabusys.utils.process_priority）
  - set_process_priority: Windows / POSIX（Linux, Darwin, FreeBSD）を吸収して nice/HIGH_PRIORITY_CLASS 等を設定。権限不足等は警告でスキップ。
  - set_cpu_affinity: 最初の N コアに固定する機能を実装。cpu_count=None で設定スキップ。権限不足等は警告でスキップ。

### Changed
- DuckDB / SQLite を併用する設計で、分析（DuckDB）と運用用の軽量監視（SQLite）を分離。
- ExecutionEngine の DB 選択ロジックを明確化（paper_trading 環境で paper DB を使用）。
- 設定の既存環境変数保護（protected set）により OS 環境変数を .env で上書きしないように変更。

### Fixed
- calc_score_weights: 全銘柄スコアが 0.0 の場合に等金額配分へフォールバックして警告を出すように修正。
- position_sizing: 単元丸め後の aggregate scale-down ロジックを実装し、端数再配分（lot 単位）を安全に行うように改良。
- risk_adjustment.apply_sector_cap: "unknown" セクターはセクター上限の対象外とする取り扱いを明確化。

---

## [0.1.0] - 2026-04-13

初回リリース（想定）: 基本設計に基づくコア機能群を実装。

### Added
- コアパッケージ構造とバージョン情報
  - パッケージバージョンを __version__ = "0.1.0" に設定（kabusys.__init__）。
- 実行系
  - ExecutionEngine 起動フロー（run_execution.py）。
  - BrokerClientFactory と MockBroker を含む想定のブローカ抽象化（実装参照: execution パッケージ）。
- 監視系
  - SystemMonitor ポーリング起動処理（run_monitoring.py）、監視用 DB 初期化呼び出し。
- データ/リサーチ
  - DuckDB を用いた factor_research（モメンタム・バリュー・ボラティリティ）を実装。
  - feature_exploration により将来リターン・IC・要約統計を提供。
- ポートフォリオ構築
  - 候補選定・重み計算、ポジションサイズ計算、セクター上限とレジーム乗数のロジックを実装。
- ユーティリティ
  - 設定管理（.env ロード、自動ロードの仕組み）、プロセス優先度・CPU 固定ユーティリティ。
- ツール
  - Paper Trading 検証レポート生成スクリプト（CLI）。
- AI 連携（初期実装）
  - ニュース記事を用いた銘柄別センチメントスコアリング機能（OpenAI 連携、バッチ処理、エラーハンドリング）。  

### Changed
- モジュールの公開 API を整理（kabusys.portfolio, kabusys.research の __all__ を整備）。
- 実行時ログレベル初期化（各起動スクリプトで logging.basicConfig(level=logging.INFO) を設定）。

### Security
- 環境変数の必須チェック関数 _require を追加し、トークン等の未設定時に明確なエラーを出すように。

---

注意:
- 本 CHANGELOG はコードの記述内容から推測して作成しています。実際のコミット単位や日付はリポジトリの履歴に依存します。必要であれば各機能を実装したコミットや PR を参照したより詳細な CHANGELOG を作成できます。