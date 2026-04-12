CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
（コードベースから推測して生成した変更履歴です。実際のコミット履歴と異なる場合があります。）

Unreleased
----------

### Added
- 起動スクリプトを追加
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。プロセス優先度を高に設定し、Broker クライアントを生成して注文実行セッションを開始します。paper_trading 環境では MockBrokerClient を利用し、専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用します。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する点に注意。

- 設定管理（Settings）を整備
  - 環境変数の自動読み込み機能を追加（プロジェクトルートに .env / .env.local がある場合）。OS 環境変数は保護され、.env.local により上書きできる設計。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーを実装し、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いをサポート。
  - Settings クラスに多数のプロパティを追加（J-Quants / kabuAPI / LINE / DB パス / 監視設定 / システム設定 等）。PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の検証ロジックを導入。

- ポートフォリオ構築モジュールを追加/強化
  - portfolio_builder: シグナル選定関数 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を実装。スコア合計が 0 の場合のフォールバック挙動を明記。
  - risk_adjustment: セクター集中制限 apply_sector_cap と市場レジームに応じた乗数 calc_regime_multiplier を実装。unknown セクターの扱い、レジームマップのデフォルト（bull/neutral/bear）を定義。
  - position_sizing: 発注株数計算 calc_position_sizes を実装。risk_based / equal / score の allocation_method、lot_size（単元）での丸め、aggregate cap によるスケールダウン、cost_buffer を使った保守的コスト見積り、残差処理による追加配分ロジックを実装。

- 研究（research）機能の実装
  - factor_research: DuckDB を使ったファクター計算関数を追加（calc_momentum, calc_volatility, calc_value）。MA200、ATR20、各種モメンタム（1m/3m/6m）等を計算し、欠損条件は None を返す設計。
  - feature_exploration: 将来リターン計算 calc_forward_returns、スピアマンランク相関 IC 計算 calc_ic、ランク付けユーティリティ rank、ファクター統計 summary を実装。外部ライブラリに依存せず標準ライブラリで完結。

- ニュース NLP（AI）モジュールを追加
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）に送信して銘柄ごとのセンチメントスコアを生成し、ai_scores に書き込む処理を実装。バッチ処理（最大 20 銘柄/コール）、リトライ（429/ネットワーク/5xx の指数バックオフ）、レスポンス検証、スコアの ±1.0 クリッピング、部分成功時の DB 部分置換戦略などを採用。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）ユーティリティ calc_news_window を提供。
  - API キー未設定時は ValueError を送出する明示的チェックを導入。

- ユーティリティを追加/改善
  - utils/process_priority.py: プロセス優先度（Windows の priority class / POSIX の nice 値）をプラットフォーム差分を吸収して設定する set_process_priority を実装。set_cpu_affinity による CPU ピンニング機能も追加。権限不足や未対応環境では警告を出してスキップする安全策を導入。

- 運用ツールを追加
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどの指標を計算し、PASS/FAIL 判定を出力。コマンドライン引数 --from/--to/--db をサポートし、主要な閾値を定義（例: uptime >= 99% 等）。

- パッケージメタ情報
  - __init__.py に __version__ = "0.1.0" を設定（初期バージョン）。

### Changed
- DB の扱いに関する明確化
  - 監視コンポーネントは環境にかかわらず本番 sqlite_path を使用する仕様に変更（run_monitoring）。一方、ExecutionEngine は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離。
- ログレベルや設定値の検証強化
  - Settings.env / log_level / PAPER_FILL_MODE 等で不正値検出時に ValueError を返すようにし、起動時に早期に設定ミスを検出できるようにした。
- .env 読み込みの優先度仕様を明確化
  - 読み込み順: OS 環境 > .env.local > .env。OS 環境変数は保護され上書きされない。

### Fixed
- ポーリング間隔の妥当性チェック
  - MONITOR_POLL_INTERVAL の値が不正（0 以下や非数）の場合にデフォルト 60 秒へフォールバックするロジックを追加（run_monitoring の _get_poll_interval）。time.sleep での ValueError を回避。
- DuckDB / SQLite 接続のクローズ処理を保証
  - run_execution.py / run_monitoring.py で finally ブロックにより接続を確実に close するようにした。

### Security
- OpenAI API キーの取り扱いにおける明示的チェックを追加（未設定時はエラー）。
- .env 自動読み込み時に OS の既存環境変数を上書きしない保護機構を導入（.env.local からの上書きを許可するが OS 環境変数は保護）。

0.1.0 - 2026-04-12
------------------
（初期公開想定）
- 初回パッケージ化。基本的なモジュール群を実装:
  - コンフィグ管理（Settings）、.env パーサー
  - 実行・監視起動スクリプト（run_execution, run_monitoring）
  - ExecutionEngine 周辺（OrderManager / OrderRepository / RiskManager / Reconciler）への接続ポイント（実装は別モジュール）
  - ポートフォリオ構築（portfolio パッケージ）
  - 研究用ファクター計算（research パッケージ）
  - ニュース NLP（ai/news_nlp.py）
  - 運用ツール（tools/paper_verification_report.py）
  - ユーティリティ（process_priority 等）

注記
----
- 本 CHANGELOG はコードベースからの推測に基づいて作成しています。実際のコミット単位や公開日付はソース管理ログをご確認ください。
- 重大な設計上の挙動（例: 監視が常に本番 sqlite を参照する等）はコード内コメントに明記されています。運用時には環境変数やパス設定を再確認してください。