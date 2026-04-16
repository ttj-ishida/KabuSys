CHANGELOG
=========

本ファイルは Keep a Changelog の形式に準拠しており、コードベース（src/ 以下）から推測される変更・追加点を日本語で記載しています。内容はソースコードの実装・コメントに基づく推測です。

Unreleased
----------

（なし）

0.1.0 - Initial release
-----------------------

Added
- コア起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイント。スレッドでセッションを実行し、外部停止フラグ（data/stop_requested.flag）で安全に停止可能。
  - run_monitoring.py: SystemMonitor をポーリングする起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。

- 設定管理
  - config.py: 環境変数/.env ファイルの読み込みロジックを実装。自動ロードのスキップ（KABUSYS_DISABLE_AUTO_ENV_LOAD）やプロジェクトルート検出（.git / pyproject.toml）に対応。
  - Settings クラスで多くの設定をプロパティとして提供（DBパス、各種閾値、環境判定、paper_trading 関連など）。

- 監視関連
  - monitoring_db 初期化（init_monitoring_db を呼び出す場所を確保）。run_monitoring/run_execution の起動時に監視テーブルの存在を冪等的に保証。

- 実行関連コンポーネント（Execution サブシステム）
  - BrokerClientFactory によるブローカークライアント生成（環境に応じて MockBrokerClient を選択可能）。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み合わせてエンジンを起動。paper_trading 環境では専用 SQLite DB（data/paper_trading.db）を使用して本番 DB と分離。

- ポートフォリオ構築ユーティリティ
  - portfolio_builder.py: 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - position_sizing.py: position size 算出（risk_based / equal / score）・単元株（lot_size）丸め・aggregate cap によるスケールダウンと残差配分ロジック。
  - risk_adjustment.py: セクターキャップ適用（apply_sector_cap）・市場レジーム乗数（calc_regime_multiplier）。

- 研究／ファクター計算
  - research/factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB を使った SQL 実装）。
  - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、スピアマンによる IC（calc_ic）、ファクター統計サマリ（factor_summary）等。
  - research パッケージから zscore_normalize 等のエクスポート。

- AI ニューススコアリング
  - ai/news_nlp.py: raw_news を OpenAI API（gpt-4o-mini を想定）でバッチスコアリングし、ai_scores テーブルへ書き込む処理を実装。タイムウィンドウ計算、チャンク/バッチ、リトライ（指数バックオフ）、レスポンス検証、スコアクリップ等を含む。APIキー引数経由または OPENAI_API_KEY 環境変数をサポート。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）等を算出し PASS/FAIL 判定を行う。コマンドライン引数で期間・DBを指定可能。

- ユーティリティ
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定（set_process_priority）および CPU affinity 固定（set_cpu_affinity）。Windows / POSIX(nice) に対応し、権限不足時は警告でスキップ。

Changed
- .env 読み込みの挙動整理
  - OS 環境変数を保護する protected 機能を導入し、.env と .env.local の上書き順序を明確化（OS 環境変数 > .env.local > .env）。export KEY= 値やクォートされた値、インラインコメントに対応するパーサを実装。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。

- 監視ループの堅牢化
  - MONITOR_POLL_INTERVAL の値検証を追加。0 以下や不正な値を検出した場合はデフォルト（60秒）にフォールバックして警告を出力。
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（運用上の非分離点を明示）。

- ExecutionEngine の挙動
  - paper_trading 環境では専用 SQLite を使用し、本番 DB との完全分離を実現。
  - エンジン起動前に停止フラグを確認し、既に停止フラグが立っていれば起動しない。

- ポートフォリオ／リスク処理の方針
  - calc_score_weights は全スコアが 0 の場合、等分配にフォールバックして WARNING を発行。
  - calc_regime_multiplier は未知レジームで 1.0 にフォールバックして警告を出す。

- レポート／統計の扱い
  - paper_verification_report はテーブル欠如や OperationalError 発生時に安全に N/A を返す（例外で停止させない）。

Fixed
- 起動時エラー耐性の改善
  - run_monitoring で MONITOR_POLL_INTERVAL に負の値や 0 を与えると time.sleep が ValueError を発生させる可能性があるため、入力検証とフォールバックを実装。

- DB 初期化の冪等性
  - init_monitoring_db の呼び出しにより、監視テーブルの存在確認・作成を起動時に保証（複数回呼んでも安全）。

- レポート計算の境界ケース対応
  - _p95（P95 計算）と各種欄（None / 空データ）に対する保護を追加。データがない場合は N/A を出力する。

- research/feature_exploration.calc_forward_returns の入力バリデーションを追加（horizons が正の整数かつ <= 252）。

- utils/process_priority と set_cpu_affinity は権限不足や未対応 OS で安全に失敗（警告）するよう改善。

Breaking Changes
- run_monitoring が常に本番用 sqlite_path を使用する仕様は、従来開発環境での監視用 DB 分離を期待していた場合に影響します（モードに依存しない設計）。開発時に分離した監視 DB を使いたい場合は環境変数の調整が必要です。

Notes / Known issues (推測)
- ai/news_nlp.py の末尾が未完の状態（ソースの断片で終端）、記事取得部分や実際の API 呼び出しループの実装が不完全に見える。実運用では記事集約・DB 書き込み箇所の最終確認が必要。
- position_sizing の price フォールバックは未実装（price が欠損時にエクスポージャーが過少見積りされる旨の TODO が存在）。
- 将来的に単元株数を銘柄別対応に拡張する余地あり（TODO コメントあり）。

Acknowledgements
- 本 CHANGELOG は src/ 以下の実装・コメントからの推測に基づいて作成しています。実際のリリース履歴や意図とは差異がある場合があります。正式な履歴はバージョン管理コミットログやリリースノートと合わせてご確認ください。