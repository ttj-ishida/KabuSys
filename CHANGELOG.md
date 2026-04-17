# CHANGELOG

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の書式に準拠します。

最新の変更を先頭に記載しています。

## [Unreleased]

- WIP（進行中）
  - ai/news_nlp.py の OpenAI API 連携処理は大部分が実装されているものの、ファイル末尾で処理が途切れており（途中中断）、完全な実行経路・エラーハンドリングの最終整備や単体テストが残っています。
  - ドキュメント整備、追加のテストケース、Edge case のハンドリング（例: DuckDB executemany の空パラメータ回避など）を予定。

---

## [0.1.0] - 2026-04-17

初回公開リリース。自動売買システム KabuSys のコア機能群を実装。

### Added
- 全体
  - パッケージ初期版を追加。モジュール分割により運用/研究/ポートフォリオ構築/ツール群を提供。
  - バージョン情報: kabusys.__version__ = "0.1.0"

- 設定管理（src/kabusys/config.py）
  - .env 自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml）。
  - .env/.env.local の読み込み順序と「OS 環境変数を保護する protected」オプションを導入。
  - 複雑な .env 行のパース実装（export プレフィックス、クォート内エスケープ、インラインコメントの扱い）。
  - 各種環境設定プロパティを実装（DB パス、PID/kill フラグ、監視しきい値、PAPER_FILL_MODE のバリデーションなど）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能。

- 実行 / モニタリングスクリプト
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。Paper Trading モード用に専用 SQLite（data/paper_trading.db）を使用する分離を実装。停止フラグで安全に停止可能。
  - run_monitoring.py：SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
  - プロセス優先度を起動直後に "high" に設定（set_process_priority を利用）。

- 実行系コンポーネント（src/kabusys/execution/*）
  - BrokerFactory / ExecutionEngine / OrderManager / OrderRepository / Reconciler / RiskManager 等の実行系コンポーネントを統合（設定に応じて MockBroker を使うなどの分離を想定）。
  - RiskConfig によるリスク制限パラメータを定義（max_position_pct、max_utilization、rate_limit_per_sec 等）。

- 監視（src/kabusys/monitoring/*）
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）を呼び出すことで必要テーブルの存在を保証（冪等）。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - portfolio_builder: シグナル選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights、全スコア 0 の場合は等分配にフォールバックして警告）。
  - risk_adjustment: セクター集中抑制（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier、未知レジームは 1.0 にフォールバックして警告）。
  - position_sizing: 発注株数計算（calc_position_sizes）。risk_based / equal / score の各配分方式をサポート。単元株（lot_size）丸め、1 銘柄上限・総投下上限のスケールダウン、cost_buffer を考慮した保守的評価、残差に基づく追加配分ロジックを実装。

- 研究 / リサーチ（src/kabusys/research/*）
  - factor_research: モメンタム（calc_momentum）、ボラティリティ/流動性（calc_volatility）、バリュー（calc_value）ファクターを DuckDB クエリで一括計算する実装。ウィンドウサイズやデータ不足時の None 扱いなどを設計に反映。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、Spearman ベースの IC（calc_ic）、ファクター統計サマリ（factor_summary）、ランク付けユーティリティ（rank）を実装。
  - DuckDB 接続を受け取りローカルデータ（prices_daily, raw_financials）だけを参照する安全設計。

- AI（src/kabusys/ai/news_nlp.py）
  - ニュースを OpenAI（gpt-4o-mini）でスコアリングするモジュールを追加（銘柄ごとの集約、バッチ送信、429/ネットワーク/5xx に対する指数バックオフ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分更新による安全な DB 書き込み戦略などの設計を実装）。
  - バッチサイズ、リトライ回数、文字・記事数上限、ニュース収集ウィンドウ（JST → UTC 変換）などの定数を定義。
  - （注）ファイル末尾は途中で切れており、実行パスの最終調整が必要（Unreleased 参照）。

- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs などを集計して稼働率・成立率・送信率・P95 レイテンシ等を算出、閾値（稼働率 99% など）に基づく PASS/FAIL 判定を出力。
  - コマンドライン引数で期間指定（--from/--to）と DB パス（--db）をサポート。

- ユーティリティ（src/kabusys/utils/process_priority.py）
  - クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティを実装。Windows と POSIX の差分吸収、権限不足や未サポート環境での警告出力をサポート。

- パッケージ公開（src/kabusys/__init__.py）
  - 主要エクスポートの __all__ を整備（data, strategy, execution, monitoring 等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Design decisions
- モジュールは可能な限り副作用を抑え、DuckDB / SQLite 接続は呼び出し側で管理する設計（接続を受け取る関数を多用）。
- .env の読み込みはデフォルトで自動実行されるが、テスト等で無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
- Paper Trading と Live の DB を明確に分離（paper_trading 環境は paper_sqlite_path を使用）。
- レジームやセクター上限、リスクパラメータ等はコードにデフォルト値を持たせつつ、外部からの上書きを想定する設計。

---

未実装・要改善点（今後の課題）
- ai/news_nlp.py の処理完結と堅牢な例外処理・再試行ロジックの検証。
- utils/process_priority の一部プラットフォームでの権限不足時の動作確認とドキュメント化。
- DuckDB executemany 周りの挙動（空パラメータ回避）のユニットテスト追加。
- Portfolio / Execution のエンドツーエンド統合テストと、Paper Trading の検証スイート整備。

---

（注）追加の変更履歴を残す際は、本ファイルを更新してください。