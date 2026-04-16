CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
形式は「Keep a Changelog」に準拠しています。

目次
----
- [Unreleased](#unreleased)
- [0.1.0 - 2026-04-16](#010---2026-04-16)
  - Added
  - Changed / Behavior
  - Fixed / Validation
  - Notes / Known issues

Unreleased
----------
（なし）

0.1.0 - 2026-04-16
-----------------

Added
- パッケージ初回リリース。
- 基本構成
  - パッケージメタ情報（kabusys.__version__ = "0.1.0"）。
  - Settings クラスによる環境変数ベースの設定管理モジュール（kabusys.config）。
    - .env / .env.local の自動読み込み（プロジェクトルート検出による、OS 環境変数保護）。
    - export プレフィックス・クォート・インラインコメント対応の .env パーサ実装。
    - 各種設定プロパティ（DB パス、KABUSYS_ENV、PAPER_FILL_MODE、しきい値等）。
- 実行エントリ
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番（SQLITE_PATH） DB を使用して初期化。
    - 停止フラグ (data/stop_requested.flag) による優雅な終了。
  - run_execution.py: ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite DB を使用（本番 DB と分離）。
    - 起動前に停止フラグチェック。PID ファイルを利用。
    - ExecutionEngine を別スレッドで実行し、停止フラグ検知で engine.stop() を呼ぶ仕組み。
- DB / analytics
  - DuckDB を分析用に組み込み（duckdb 接続を各種 research / ai モジュールへ注入）。
  - 監視用 DB の初期化ユーティリティ（monitoring_db.init_monitoring_db）を起動時に呼び出す冪等処理。
- Portfolio（銘柄選定・配分・単元丸め等）
  - portfolio_builder: 候補選定（select_candidates）、等重み・スコア加重配分（calc_equal_weights / calc_score_weights）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - position_sizing: position size 計算（calc_position_sizes）。
    - risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）丸め、aggregate cap（available_cash）に基づくスケールダウン・再配分ロジック実装。
- Research（因子計算・特性探索）
  - research.factor_research: モメンタム / ボラティリティ / バリュー系ファクター計算（DuckDB SQL ベース）。
    - mom_1m / mom_3m / mom_6m / ma200_dev、atr_20 / atr_pct / avg_turnover / volume_ratio、per / roe など。
  - research.feature_exploration: 将来リターン計算、Spearman ランク相関による IC 計算、ファクター統計サマリ、rank ユーティリティ。
  - research パッケージは kabusys.data.stats.zscore_normalize を再エクスポート。
- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成 CLI。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
    - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - CLI 引数 --from / --to / --db をサポート。
    - レポート向けのしきい値定義（稼働率 99%、成立率 90% 等）。
- AI / ニュース NLP
  - ai.news_nlp: raw_news から銘柄別にテキストを集約し OpenAI API（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づく記事抽出。
    - バッチ処理（最大 20 銘柄/呼び出し）、最大記事数・文字数トリム、スコア ±1.0 クリップ。
    - 429 / ネットワークエラー / タイムアウト / 5xx に対する指数バックオフリトライ。
    - JSON Mode を期待するシステムプロンプトとレスポンスバリデーション設計。
- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level): Windows と POSIX（Linux/Mac/FreeBSD）に差分吸収して実装。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアに固定するヘルパ。
    - 権限不足や未対応 OS の場合は警告ログを出して安全にスキップ。

Changed / Behavior
- .env 自動ロードの挙動:
  - デフォルトでプロジェクトルートの .env を自動読み込み（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - 読み込み順序: OS 環境 > .env.local > .env。OS 環境は上書き禁止（protected）。
- Execution / Monitoring 起動時のプロセス優先度を最初に "high" に設定（実行スクリプトの冒頭で set_process_priority("high") を呼ぶ）。
- run_monitoring は MONITOR_POLL_INTERVAL の値が不正な場合にデフォルト 60 秒へフォールバックして警告を出す。

Fixed / Validation
- Settings における入力検証強化:
  - KABUSYS_ENV, LOG_LEVEL の許容値チェックを追加し、無効値は ValueError を送出。
  - PAPER_FILL_MODE の値検証（instant|partial|never|reject）。無効値は ValueError。
- run_monitoring のポーリング間隔取得関数で 0 以下や非整数を安全に扱い、time.sleep に渡す前にフォールバックするようにした。
- DuckDB / SQLite の使用に関する運用上の注意（例: DuckDB executemany のパラメータが空の場合の注意喚起）はツール実装内で配慮。

Notes / Known issues
- apply_sector_cap 内に価格欠損時のフォールバックに関する TODO コメントあり:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされブロックが外れる可能性。将来的に前日終値等のフォールバックを検討する旨が記載されています。
- process_priority の権限不足や対応外 OS の場合は警告ログを出して設定をスキップします（動作保証外のプラットフォームがあることに注意）。
- ai.news_nlp: 大枠の設計（ウィンドウ計算、バッチ・トリム、リトライ、バリデーション、DB 書き換え戦略）が実装されていますが、提供コードスニペットの末尾で関数定義の一部が途切れているため（fetch_articles 等の補助実装がスニペット内に含まれていません）、実際の環境での完全動作は補完実装が必要です。実運用前に fetch / write ロジックの完全性を確認してください。
- paper_verification_report のレポートは DB スキーマ（system_status, trade_logs, risk_logs 等）に依存します。対象 DB に該当テーブルが存在しない場合は適切に N/A 表示されますが、DB の整合性は事前に確認してください。
- DuckDB を分析用途で使用する設計のため、production 向けのデータ保持ポリシー・VACUUM やバックアップ方針を運用側で定義することを推奨します。

付記
- ここに記載した変更点は提供されたソースコードの内容から推測してまとめたものであり、リポジトリ全体の別ファイル（テスト・ドキュメント等）に記載された意図や実装差分との整合は必ずしも保証しません。実際のリリースノートとして使用する場合は、差分確認と実運用テストを行った上で必要に応じて修正してください。