CHANGELOG
=========

すべての注目すべき変更履歴をここに記載します。フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

（現在未リリースの作業はありません）

[0.1.0] - 2026-04-16
-------------------

初回公開リリース。コードベースから推測される主要な機能・修正点、運用上の注意点をまとめます。

Added
- 基本アプリケーションと起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV が paper_trading の場合は paper_trading 専用 SQLite DB を使用して本番 DB と分離（data/paper_trading.db をデフォルト）。停止フラグ（data/stop_requested.flag）や PID ファイル管理をサポート。
  - run_monitoring.py: SystemMonitor ポーリングスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する点に注意。
- 設定管理
  - kabusys.config.Settings: 環境変数・.env 自動ロード機構を提供（プロジェクトルートの検出、.env / .env.local の読み込み順）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - .env パーサーは export プレフィックス、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメント処理に対応。既存 OS 環境変数は保護される（.env.local でも上書きは protected を回避しない）。
  - 環境値検証を実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE などの有効値チェック）。
- ポートフォリオ構築モジュール
  - portfolio_builder: シグナル選定（select_candidates）、等分配・スコア加重（calc_equal_weights / calc_score_weights）。スコア合計が 0 の場合は等分配へフォールバック。
  - risk_adjustment: セクターキャップ適用（apply_sector_cap）、市場レジームに応じた投下乗数（calc_regime_multiplier）。
  - position_sizing: 発注株数決定ロジック（risk_based / equal / score）、単元（lot_size）丸め、aggregate キャップ（利用可能現金に合わせたスケーリング）、コストバッファ考慮。
  - portfolio パッケージのエクスポートを整理。
- リサーチ・ファクターモジュール
  - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB 接続を受け取り SQL で計算）。MA200、ATR、平均売買代金などを算出し、データ不足時は None を返す設計。
  - research.feature_exploration: 将来リターン計算（複数ホライズン）、Spearman（ランク）ベースの IC 計算、ファクター統計サマリー。外部ライブラリに依存せず実装。
  - research パッケージは zscore_normalize（data.stats 由来）を含めて公開。
- AI ニュース NLP
  - ai/news_nlp.py: raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント（ai_scores）を書き込む機能を追加。処理はバッチ化（最大 20 銘柄）・トークン肥大対策（記事数上限、文字数上限）・スコアの ±1.0 クリップを実装。
  - API リクエストに対して 429 / ネットワークエラー / タイムアウト / 5xx を想定した指数バックオフリトライを実装（上限回数制御）。
  - タイムウィンドウの計算は JST ベース（前日 15:00 ～ 当日 08:30）を UTC に変換して処理。ルックアヘッドバイアス回避のため datetime.today() を直接参照しない設計。
  - 部分成功時に既存スコアを保護するため、更新は対象コードを絞って DELETE→INSERT（部分置換）する方針。
- ユーティリティ
  - utils.process_priority: プラットフォーム差分を吸収してプロセス優先度（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）を設定するユーティリティを追加。CPU affinity 固定機能も提供。権限不足や未対応 OS の場合は警告を出してスキップ。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を計算し PASS/FAIL 判定を出力。DB が存在しない場合やテーブルが無い場合の耐性（OperationalError の捕捉）を実装。
- DB 初期化・監視
  - monitoring.monitoring_db.init_monitoring_db の呼び出しにより、起動時に監視テーブルが存在することを保証（冪等）。

Changed
- ログと起動挙動
  - 起動時にプロセス優先度を "high" に設定するように各起動スクリプトで最初に呼ぶように統一。
  - run_execution は paper_trading 環境時に MockBrokerClient を使う設計を前提に、ExecutionEngine 周辺の組み立て（OrderRepository、OrderManager、RiskManager、Reconciler）を整理。
- 設定読み込みの優先度
  - OS 環境変数 > .env.local > .env の順でロード。既存 OS 環境変数は保護される（.env.local がそれを上書きしない）。

Fixed / Robustness improvements
- 入力検証・フォールバック処理の強化
  - MONITOR_POLL_INTERVAL: 環境変数が不正（数値でない、0 以下）な場合にデフォルト 60 秒へフォールバックし警告を出力。
  - PAPER_FILL_MODE: 有効値チェックを追加し、不正値は ValueError を送出。
  - calc_score_weights: 全銘柄スコア合計が 0 の場合に等分配へフォールバックして warning を出力。
  - research モジュール群: データ不足時に None を返すことで downstream での例外発生を防止（MA200 カウント不足、ATR カウント不足など）。
  - calc_forward_returns: horizons の入力検証（正の整数かつ <= 252）を追加。
  - calc_ic: 有効ペアが 3 件未満の場合は None を返す。
  - utils のプロセス優先度 / CPU affinity 設定は権限不足や未サポート環境で例外を吸収して警告出力するよう改善。
  - paper_verification_report: DB ファイルが存在しない場合やテーブル欠損による OperationalError を捕捉してレポート生成を継続できるようにした。

Notes / Operational considerations
- 監視デーモン（run_monitoring.py）は「環境にかかわらず」本番 sqlite_path を使用する挙動になっています。運用時は意図を確認してください（ドキュメント文字列に明記あり）。
- Paper Trading 環境は本番 DB と完全分離されることを意図して設計されています（PAPER_TRADING_SQLITE_PATH により上書き可能）。
- .env ファイル読み込みはプロジェクトルートの検出に依存するため、配布後やパッケージ化後の実行環境では自動ロードがスキップされる可能性があります。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して制御してください。
- AI ニュース NLP は OpenAI API キー（OPENAI_API_KEY または関数引数）を必須とし、API 制限やエラーからの回復を試みる実装ですが、API 請求やレイテンシの取り扱いに注意してください。

Deprecated
- なし（初回リリースのため該当なし）

Removed
- なし（初回リリースのため該当なし）

Security
- OpenAI API キー等の秘密情報は環境変数で扱う設計。取り扱いに注意してください（ログ出力に含めない等）。

補記（実装上の小さな注記）
- 一部関数内に TODO コメントあり（例: position_sizing の銘柄別 lot_size 拡張、risk_adjustment の価格フォールバック実装等）。将来の改善候補としてメモしています。
- バージョンはパッケージルートの __version__="0.1.0" を初期リリースとしています。

以上

--- 
（本 CHANGELOG は提示されたソースコードからの推測に基づいて作成しています。実際のコミット履歴やリリースノートと差異があり得ます。）