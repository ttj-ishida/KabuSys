CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。
リリースはセマンティックバージョニングに従います。

Unreleased
----------
（次バージョンに向けた変更履歴をここに記載します）

0.1.0 - 2026-04-16
-----------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - 高水準のサブパッケージを追加:
    - portfolio: 候補選定、重み計算、ポジションサイズ算出、セクター集中抑制、レジーム乗数
    - research: ファクター計算（モメンタム/ボラティリティ/バリュー）、特徴量探索（将来リターン計算、IC計算、統計サマリー）
    - execution: ExecutionEngine 起動スクリプトと実行関連のコンポーネント（OrderManager, OrderRepository, RiskManager, Reconciler 等）※エンジン主要処理は別モジュールに分離
    - monitoring: SystemMonitor を用いた監視ループ起動スクリプト
    - ai: ニュース NLP スコアリング（OpenAI を用いたセンチメント解析）※API 呼び出しまわりを実装
    - tools: Paper Trading 検証レポート生成スクリプト
    - utils: プロセス優先度・CPU affinity 設定ユーティリティ
  - パッケージメタ情報: __version__ = "0.1.0"

- 実行・監視用エントリポイントを追加
  - run_execution.py
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用して本番 DB と分離
    - BrokerClientFactory 経由でブローカークライアントを生成
    - ExecutionEngine を別スレッドでデーモン起動し、data/stop_requested.flag により外部停止が可能
    - data/execution.pid を PID ファイルに使用
  - run_monitoring.py
    - SystemMonitor を利用したポーリングループ
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 停止フラグ（data/stop_requested.flag）検知でループ終了
    - 監視は環境にかかわらず本番 sqlite_path を使用するよう設計

- 設定・環境変数読み込み機能を実装（kabusys.config）
  - .env, .env.local の自動ロード（CWD に依存しないプロジェクトルート検出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化
  - .env パーサ: export 形式、クォート（シングル/ダブル）内のエスケープ、インラインコメントの取り扱い対応
  - Settings クラスで主要設定をプロパティとして提供（DB パス、API トークン、閾値、環境判定等）
  - PAPER_FILL_MODE のバリデーション（有効値チェック）
  - はじめての起動時に kill/flag 関連オプションや PID ファイルパスを管理するプロパティを提供

- DuckDB / SQLite の統合
  - DuckDB 接続を受け取り研究・AI モジュールで高速 SQL 集計を実行
  - 監視テーブルの初期化ユーティリティ（init_monitoring_db）を起動前に実行する呼び出しを追加

- ポートフォリオ構築モジュール
  - portfolio_builder:
    - select_candidates: スコア降順 + signal_rank によるタイブレークをサポート
    - calc_equal_weights / calc_score_weights: スコア総和が 0 の場合は等金額配分にフォールバック（警告ログ）
  - risk_adjustment:
    - apply_sector_cap: セクター毎の既存エクスポージャ算出とセクター上限超過時の候補除外（"unknown" セクターは除外対象外）
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームはフォールバック）
  - position_sizing:
    - risk_based / equal / score の配分ロジックを実装
    - lot_size（単元株）に基づく丸め処理、単銘柄上限・投下資金上限の適用
    - cost_buffer を用いた保守的コスト見積りと、利用可能現金を超えた場合のスケーリング処理（残差に応じた lot_size 単位の再配分）

- 研究（research）機能
  - factor_research:
    - calc_momentum / calc_volatility / calc_value を実装（DuckDB のウィンドウ関数を活用）
    - データ不足（行数不足）を考慮して None を返す設計
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを一括取得
    - calc_ic / rank / factor_summary: スピアマン相関（IC）計算、ランク付け、基本統計量出力
    - 外部ライブラリ非依存で標準ライブラリのみで実装

- AI ニューススコアリング（ai/news_nlp.py）
  - raw_news / news_symbols を集約して OpenAI （gpt-4o-mini）にバッチ送信
  - 最大 20 銘柄 / バッチ、記事数・文字数上限でトークン肥大を抑制
  - レスポンス検証、スコア ±1.0 クリップ、429/5xx/ネットワークエラーに対する指数バックオフのリトライ制御
  - AI 出力は厳密な JSON のみを期待するシステムプロンプトを定義
  - 注意: ソースコード中で score_news の後半が途中で切れている（実装継続の TODO が存在）

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポートを生成
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出し PASS/FAIL 判定
    - P95 計算、期間フィルタ、各種デフォルト閾値を定義
    - コマンドライン引数 --from / --to / --db をサポート

- ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX を吸収したプロセス優先度設定（nice / HIGH_PRIORITY_CLASS 等）
    - set_cpu_affinity による CPU コア固定機能
    - 権限不足や未対応 OS に対しては安全にスキップして警告ログを出す

Changed
- auto env ロードの優先順位を明確化（OS 環境変数 > .env.local > .env）
- .env ロード時の上書き制御（protected set により既存 OS 環境変数を保護）
- run_monitoring / run_execution 起動手順を整理:
  - プロセス優先度設定を起動直後に実行
  - 監視 DB 初期化を起動時に冪等に保証
  - paper_trading 環境では SQLite を分離して使用

Fixed
- MONITOR_POLL_INTERVAL の不正値処理を強化（不正値時は警告を出してデフォルトにフォールバック）
- position_sizing のスケールダウン処理で lot_size 丸めと残余配分を安定化（再現性のためソートキーに code を使用）
- .env パーザでクォート内のエスケープとインラインコメント処理を正しく扱うよう改善

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- OpenAI API キーの取り扱い: score_news は明示的な api_key 引数または OPENAI_API_KEY 環境変数を要求。未設定の場合は ValueError を送出して誤使用を防止。

Notes / Known issues
- ai/news_nlp.py の score_news 関数の処理がソース上で途中（ファイルの末尾が切れている）になっており、DB への書き込み（ai_scores 更新）処理の完全実装が未反映です。実運用前に該当箇所の実装完了とテストを推奨します。
- 一部の TODO コメント（price のフォールバックロジックや銘柄別 lot_size サポート等）が残っています。将来の改善項目として記録しています。
- 実行時にプロセス優先度 / CPU affinity の設定は権限によって失敗する場合があります（ログで警告しスキップする設計）。運用環境の権限設定に注意してください。

References
- コード内ドキュメント（モジュール docstring）および PortfolioConstruction.md / StrategyModel.md 等の設計注記に準拠して実装しています（該当ドキュメントはリポジトリ内に存在する想定）。
- バージョンは kabusys.__version__ に合わせて 0.1.0 を初回リリースとしています。