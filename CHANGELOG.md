# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの内容から推測して作成した要約です（実装コメント・定数等を基に記載）。日付は 2026-04-12。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Added
- 各種起動スクリプトを追加 / 整備
  - run_execution: 実取引・ペーパートレード両対応の ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離する。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境に関わらず本番 sqlite_path を使用する挙動。

- 設定・環境変数管理
  - Settings クラスを提供。各種設定（J-Quants / kabuAPI / LINE / DB パス /監視閾値 / 環境判定など）をプロパティ経由で取得する。
  - 環境ファイル自動読み込み機能を実装（.env, .env.local、OS 環境変数を保護して上書き制御）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーを強化（export 形式、シングル/ダブルクォート、エスケープ、行内コメントの扱いを考慮）。

- 実行環境制御ユーティリティ
  - process_priority: プロセス優先度（high / normal / low）をクロスプラットフォームで設定するユーティリティを追加。Linux/macOS/FreeBSD の nice 値対応、Windows の HIGH_PRIORITY_CLASS 等に対応。
  - CPU affinity 設定ユーティリティ（set_cpu_affinity）を追加（使用可能なら最初の N コアに固定）。

- Execution コンポーネント
  - BrokerClientFactory、OrderManager、OrderRepository、Reconciler、RiskManager、ExecutionEngine（および EngineConfig / RiskConfig）といった実行系コンポーネントの組み立てを run_execution で実演。
  - RiskManager に対するデフォルト設定を明示（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）。
  - ExecutionEngine は duckdb 接続を受け取り、pid_file を扱う設計。

- 監視・モニタリング
  - init_monitoring_db による監視テーブル初期化を run_* スクリプトで保証（冪等性）。
  - SystemMonitor の単発チェックをポーリングループで定期実行し、例外はキャッチしてログ出力しつつ次回ポーリングに継続。

- Paper Trading 検証ツール
  - tools/paper_verification_report: ペーパートレード用 SQLite から稼働率、注文成功率、送信率、API レイテンシ等を集計してレポート出力する CLI ツールを追加。各種閾値による Pass/Fail 判定を実装。
  - 日付フィルタ、P95 計算、欠損データに対するフェイルセーフ処理を実装。

- ポートフォリオ構成ライブラリ
  - portfolio_builder: シグナルの候補選定（スコア降順、タイブレーク）、等分配 / スコア加重配分の実装（スコアが全て 0 の場合は等重配分にフォールバック）。
  - risk_adjustment: セクター集中上限チェック（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジーム時のフォールバックログも出力。
  - position_sizing: allocation_method（risk_based / equal / score）に基づく発注株数計算、lot_size（単元株）での丸め、max_position_pct / max_utilization 等の制約、aggregate cap によるスケールダウンと端数配分ロジック（remainders）を実装。手数料・スリッページを想定した cost_buffer を考慮。

- リサーチ機能
  - research.factor_research: Momentum / Volatility / Value の各ファクター計算関数を追加（DuckDB を用いた SQL 実装）。MA200 乖離、ATR、20日平均出来高、PER/ROE などを算出。データ不足時は None を返す安全設計。
  - research.feature_exploration: 将来リターン計算（複数ホライズン対応）、スピアマンによる IC（calc_ic）、ファクターの統計サマリー（median 等）を実装。外部依存を避けた純粋実装（標準ライブラリのみ）。
  - research パッケージから zscore_normalize を公開。

- AI ニュース NLP
  - ai/news_nlp: raw_news と news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄別センチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む処理を実装。主な特徴:
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して比較）
    - 記事数・文字数上限（1 銘柄あたり最大記事数・最大文字数）を設けてトークン肥大化を回避
    - 最大バッチサイズ、リトライ（429, 5xx, ネットワーク等）と指数バックオフ
    - レスポンスバリデーション（厳密な JSON 期待）、スコアを ±1.0 にクリップ
    - 部分失敗時でも既存スコアを保護するため code 範囲を限定した置換（DELETE + INSERT）を想定
    - API キーは引数または環境変数 OPENAI_API_KEY から解決（未設定時は ValueError）

### Changed
- コード内デフォルト値を明示
  - MONITOR_POLL_INTERVAL のデフォルトを 60 秒に設定し、0 以下はデフォルトへフォールバックして time.sleep の ValueError を回避。
  - 各種パスのデフォルト（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH）を Settings で定義し expanduser を適用。

- 安全性 / フェイルセーフの強化
  - DB 操作や API 呼び出しで発生しうる例外は大半でキャッチしてログに記録し、処理継続を優先する設計（監視ループや AI スコアリング等）。
  - psutil による優先度/affinity 設定は権限不足や未実装 API の場合に警告ログを出すようにしてプロセス停止を防止。

### Fixed
- .env パースの不具合対策
  - クォート内のエスケープとインラインコメント処理を正しく扱うよう改善。
  - export KEY=val 形式の対応を追加。

### Removed
- なし（初期リリース相当のため該当なし）

---

## [0.1.0] - 2026-04-12

初回リリース（推定）。上の Unreleased の内容を v0.1.0 としてまとめた想定リリース。

### Added
- 基本パッケージ情報:
  - パッケージ初期化で __version__ = "0.1.0" を設定。
- 実行 / 監視:
  - run_execution.py, run_monitoring.py を実装。
- 設定管理:
  - config.Settings と .env 自動読み込み / パース周りの実装。
- 実行ユーティリティ:
  - utils.process_priority（プロセス優先度設定 / CPU affinity）。
- Execution 系:
  - BrokerClientFactory を利用したブローカークライアント抽象化、OrderRepository / OrderManager / Reconciler / RiskManager / ExecutionEngine の組み立て。
- 監視 DB 初期化:
  - init_monitoring_db（監視テーブルの冪等初期化）を導入。
- Paper Trading 検証ツール:
  - tools/paper_verification_report を追加（レポート生成・閾値判定）。
- ポートフォリオ構築:
  - portfolio モジュール（選定・重み付け・セクター制限・レジーム乗数・株数決定ロジック）。
- リサーチ:
  - research パッケージに factor_research / feature_exploration を実装（DuckDB SQL ベースのファクター・将来リターン・IC・要約統計）。
- AI ニュース処理:
  - ai.news_nlp による OpenAI 統合のセンチメントスコアリング（バッチ・リトライ・書き込み戦略）。
- テスト / デバッグに資するログ出力の整備。

### Changed
- なし（初回リリースのためチェンジ履歴なし）

### Fixed
- なし（初回リリース）

### Removed
- なし

---

破壊的変更 (BREAKING CHANGES)
- なし（初回リリース想定のため）

注記
- 本 CHANGELOG はコードベースのコメント・実装内容から推測して作成した要約です。実際のリリース履歴やマイルストーンはリポジトリのコミット履歴に基づいて整理することを推奨します。