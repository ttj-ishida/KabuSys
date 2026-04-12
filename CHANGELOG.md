# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの内容から推測して作成した変更履歴です（実際のコミット履歴ではありません）。

なお、バージョン番号はパッケージの __version__（0.1.0）に合わせています。

## [Unreleased]

### Added
- MONITOR_POLL_INTERVAL 環境変数による監視ポーリング間隔の上書き（不正値はデフォルト 60 秒にフォールバックし警告ログ出力）。
- 監視プロセス起動スクリプト（run_monitoring.py）を追加。SystemMonitor を用いたポーリングループ、SQLite / DuckDB 接続、プロセス優先度設定を行う。
- 実行エンジン起動スクリプト（run_execution.py）を追加。ExecutionEngine の起動フロー、ブローカークライアントファクトリの利用、paper_trading 環境での専用 DB 分離対応を実装。
- 設定管理モジュール（kabusys.config）を追加：
  - .env / .env.local の自動読み込み（プロジェクトルート検出、OS 環境変数の保護、オーバーライド制御）。
  - .env 行パーサの実装（クォート、エスケープ、インラインコメント対応）。
  - 各種環境変数プロパティ（DB パス、PID/kill フラグ、閾値、PAPER_FILL_MODE バリデーション等）。
- Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）を追加。CSV ではなく標準出力レポートを生成、期間フィルタ・DB パス指定オプションをサポート。
- ポートフォリオ構築モジュール（kabusys.portfolio）を追加：
  - 候補選定（select_candidates）、等金額／スコア加重のウェイト計算（calc_equal_weights / calc_score_weights）。
  - セクター上限適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
  - 発注株数決定（calc_position_sizes）：リスクベース・等配分・スコア配分、単元株丸め、aggregate cap によるスケーリング、cost_buffer の考慮など。
- 研究モジュール（kabusys.research）を追加：
  - ファクター計算（calc_momentum, calc_volatility, calc_value）。
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）。
  - DuckDB を用いた効率的な SQL ベース計算。
- AI ニュース NLP モジュール（kabusys.ai.news_nlp）を追加：
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング。
  - タイムウィンドウ算出、記事集約、銘柄ごとチャンク処理（最大バッチサイズ制御）、レスポンス検証、スコアクリッピング、部分更新（対象コードのみ置換）などの堅牢なフローを実装。
  - 429/タイムアウト/5xx 等に対する指数バックオフリトライ実装（上限回数制御）。
- ユーティリティ（kabusys.utils.process_priority）を追加：
  - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収したプロセス優先度設定。
  - CPU affinity 設定ユーティリティ（最初の N コアへ固定）。
  - 権限不足や未対応 OS の場合は警告ログで安全にスキップ。

### Changed
- 監視・実行スクリプトで起動時にプロセス優先度を "high" に設定するように変更（set_process_priority 呼び出しを最初に実行）。
- ExecutionEngine 起動時のリスク管理初期設定を明示（Rate limit, Circuit breaker, Drawdown 等のパラメータを RiskConfig に集約）。
- 設定値読み込みの優先度を OS 環境 > .env.local > .env に決定し、OS 環境変数は保護（上書き不可）。
- Paper Trading（paper_trading）環境では SQLite DB を本番 DB と分離（デフォルト data/paper_trading.db）する振る舞いを採用。
- DuckDB の利用を全体で標準化（research / ai 等の分析処理は DuckDB 接続を受け取って SQL を実行）。

### Fixed
- .env パースでのクォート・エスケープやインラインコメントの取り扱いを堅牢化（export キーワード対応を含む）。
- 空のデータや NULL 値が混在する場面での計算（パーセンタイル、平均、P95、ATR 等）に対する安全処理を追加（None / 空リストハンドリング）。
- calc_score_weights で全スコアが 0 の場合に等金額配分へフォールバックして警告を出すように修正。
- ポジションサイズ計算における aggregate スケーリングで小数端数処理（lot_size 単位での再配分）を改善。
- news_nlp の API キー未設定時に明確な例外を送出するように変更。

---

## [0.1.0] - 2026-04-12

最初の公開リリース。本リポジトリに含まれる主要機能をまとめてリリース。

### Added
- 基本パッケージ情報（kabusys.__init__ に version=0.1.0 を設定）。
- 監視サブシステム:
  - SystemMonitor のポーリングループ起動スクリプト（run_monitoring.py）。
  - 監視用 DB 初期化ユーティリティ（init_monitoring_db を呼び出す部分を用意）。
- 実行（Execution）サブシステム:
  - ExecutionEngine 起動スクリプト（run_execution.py）。
  - ブローカークライアントファクトリ（BrokerClientFactory）を利用した broker 抽象化。
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせた実行フロー。
- 設定管理（kabusys.config）:
  - .env 自動ロード、必須環境変数チェック、各種設定プロパティ。
- ポートフォリオ構築（kabusys.portfolio）:
  - 候補選定・重み算出・セクター制限・レジーム乗数・ポジションサイズ算出（lot 単位丸め・リスク制限）。
- 研究・分析（kabusys.research）:
  - モメンタム・ボラティリティ・バリュー等のファクター計算。
  - 将来リターン・IC・ファクター統計サマリー。
- AI ニューススコアリング（kabusys.ai.news_nlp）:
  - OpenAI 連携によるニュースセンチメント集計と ai_scores への書き込み。
- ユーティリティ（kabusys.utils）:
  - プロセス優先度・CPU affinity 操作。
- ツール:
  - Paper Trading 検証レポート生成 CLI（kabusys.tools.paper_verification_report）。

### Changed
- 各モジュールで外部リソース（DB / OpenAI / ブローカー等）へ直接アクセスしないよう設計（DuckDB 接続や broker は呼び出し側で注入する設計）。
- 研究モジュールは DuckDB の SQL を活用する設計によりパフォーマンスと可読性を両立。
- 設定ロードの挙動（プロジェクトルート検出）により、パッケージ配布後も設定ファイルの自動検出が可能な実装。

### Fixed
- ファイル・DB が存在しない場合やテーブルがない場合に graceful に動作するように多数の保護処理を追加（OperationalError の捕捉等）。

---

作成・更新に関する注意:
- この CHANGELOG はコードから推測して作成したため、実際のコミット単位の履歴とは異なります。具体的な変更差分をコミットレベルで記録する場合は、git の履歴やタグ付けを参照/整備してください。