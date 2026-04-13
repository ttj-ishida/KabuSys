CHANGELOG
=========
All notable changes to this project will be documented in this file.

この CHANGELOG は Keep a Changelog の慣例に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-13
--------------------

Added
- 初期リリースを追加
  - プロジェクトのバージョンを kabusys.__version__ = "0.1.0" として定義。
- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み実装（プロジェクトルートを .git / pyproject.toml から検出）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは export 形式、クォート（シングル/ダブル）およびエスケープ、行内コメントなどを考慮した堅牢な実装。
  - 必須値チェック（_require）と多くの設定プロパティ（DB パス、API トークン、監視しきい値、プロセス PID/kill フラグパス、環境種別判定など）を提供。
  - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KABUSYS_ENV、LOG_LEVEL 等の環境変数サポートと検証。
- 実行・監視エントリポイント
  - run_execution.py: 実運用エンジン起動スクリプトを追加。プロセス優先度を設定し（set_process_priority）、SQLite / DuckDB 接続を確立。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し MockBroker を想定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
- Execution コンポーネント組み立て
  - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository、OrderManager、RiskManager（RiskConfig 項目を含む）、Reconciler、ExecutionEngine の組み立てとセッション起動を実装。
  - RiskConfig のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を追加。RiskManager が broker.get_available_cash() を初期資金として使用。
- 監視 DB 初期化ユーティリティ
  - init_monitoring_db を呼んで監視用テーブルの存在を保証（冪等）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。コマンドラインから期間指定（--from / --to）可能な検証レポートを標準出力に出力。
  - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ、リスク却下数等を集計し PASS/FAIL 判定を行う。閾値はスクリプト内で定義（例: 稼働率 99% 等）。
  - DB ファイル存在チェックやテーブル不存在時の安全なフォールバックを実装。
- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio_builder: シグナル選定（select_candidates）、等重み（calc_equal_weights）、スコア重み（calc_score_weights）を実装。スコア全て 0 の場合の等重みフォールバックと警告。
  - risk_adjustment: セクター集中上限適用（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。未知レジームは警告を出してフォールバック。
  - position_sizing: allocation_method（"risk_based" / "equal" / "score"）に基づく株数決定ロジックを実装。単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金超過時のスケーリング）や cost_buffer を考慮した保守的見積り、残余キャッシュの分配ロジックを実装。
- 研究・ファクター計算（kabusys.research）
  - factor_research: DuckDB を使った momentum / volatility / value ファクター計算を実装（prices_daily, raw_financials を参照）。MA200, ATR20, 1/3/6 ヶ月リターン等を算出。
  - feature_exploration: 将来リターン（複数ホライズン）計算、Spearman ランク相関（IC）計算、ファクター統計サマリー（count/mean/std/min/max/median）等を実装。pandas 等外部ライブラリに依存しない純 Python 実装。
  - zscore_normalize をデータモジュールから再エクスポート。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI API（gpt-4o-mini）を用いたニュースのセンチメント集約・スコアリング機能を実装。記事集約、トリミング、バッチ送信（最大 20 コード/回）、指数バックオフでのリトライ、レスポンス検証、スコアクリップ、ai_scores への差分書き込み（DELETE→INSERT）を行う。
  - calc_news_window による JST ベースのニュース取得ウィンドウ計算を提供（前日 15:00 JST ～ 当日 08:30 JST）。
- ユーティリティ
  - utils/process_priority.py: Windows / POSIX を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）。権限不足や未対応 OS は警告でスキップする堅牢さ。
- データベース連携
  - DuckDB と SQLite 両方の接続を想定した実装。DuckDB を主に時系列 prices/financials の計算に使用、SQLite はトレードログ・監視等に利用。
- ロギングとエラーハンドリング
  - 多くの箇所で logging を活用し、予期しない例外は exception ログを残してポーリング/処理を継続するフェイルセーフ設計。

Changed
- 初期リリースのため該当なし（今後のリリースで変更を記録）

Fixed
- .env 読み込み時の I/O エラーや不正行に対する堅牢性を強化（警告出力して継続）。
- 環境変数パースのエッジケース（クォート内のエスケープ、行末コメントの扱い等）に対応。

Security
- OpenAI API キーや外部 API トークンは環境変数（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）から取得。キー未設定時は明示的に ValueError を送出して早期終了する箇所を実装（news_nlp.score_news 等）。

Notes / Known limitations
- position_sizing の価格欠損時のフォールバックは TODO コメントあり（将来的に前日終値や取得原価で補完する想定）。
- apply_sector_cap では sector_map にないコードは "unknown" 扱いで上限チェックから除外する設計。運用ルールに応じて変更が必要な場合あり。
- news_nlp は API レスポンスの JSON 厳密検証を行うが、OpenAI の出力変動に対する回復性のため部分失敗時は他銘柄のスコアを保護する設計（差分 DELETE/INSERT）。
- 実運用時はプロセス優先度 / CPU affinity の適用に管理者権限が必要になる場合がある。権限不足は警告でスキップされる。

Acknowledgements
- DuckDB を分析エンジンに採用。
- OpenAI（gpt-4o-mini）をニュースセンチメント推定に利用（オプション）。

今後の予定（例）
- portfolio/position_sizing: lot_size を銘柄別に扱えるよう拡張
- news_nlp: 非同期リクエスト対応やより細かいレート制御
- 実運用向け監視・アラート（LINE 連携等）の追加
- より包括的な単体テストと E2E テストの追加

---