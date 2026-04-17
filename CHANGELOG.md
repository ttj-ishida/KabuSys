CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています（https://keepachangelog.com/ja/）。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 初期リリースとして主要機能を実装。
  - 実行エンジン起動スクリプトを追加（run_execution.py）。
    - プロセス優先度を高 (`high`) に設定して起動。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - ストップフラグ検知（data/stop_requested.flag）で安全に停止。実行 PID ファイルの利用。
    - RiskManager のデフォルト設定（max_position_pct 等）を内蔵。
  - システム監視ループ起動スクリプトを追加（run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - check_once() の例外はログ出力して次ポーリングへ継続。
  - 設定管理モジュールを追加（config.py）。
    - プロジェクトルート自動検出（.git / pyproject.toml）による .env 自動ロード（.env → .env.local、OS 環境変数保護）。
    - export 付き行、クォート文字列、インラインコメントのパース対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - Settings クラスに各種プロパティ（DB パス、PID ファイル、しきい値、env 検証等）を実装。
    - PAPER_FILL_MODE の妥当性チェック、PAPER_TRADING_SQLITE_PATH の指定対応。
  - プロセス制御ユーティリティを追加（utils/process_priority.py）。
    - Windows と POSIX（Linux/Mac/FreeBSD）での優先度設定を吸収。
    - CPU affinity 設定ユーティリティを提供。
    - 権限不足などでの失敗は警告ログにフォールバック。
  - ポートフォリオ構築関連関数群を実装（kabusys.portfolio）。
    - portfolio_builder: 候補選定（select_candidates）、等金額・スコア加重配分（calc_equal_weights / calc_score_weights）。
    - risk_adjustment: セクターキャップ適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
    - position_sizing: 単元株丸め、リスクベース／等配分／スコア配分に基づく発注株数計算（calc_position_sizes）。aggregate cap（利用可能現金）に対するスケールダウンおよび残差処理を実装。
  - 研究用モジュールを追加（kabusys.research）。
    - factor_research: Momentum / Volatility / Value ファクター計算（calc_momentum, calc_volatility, calc_value）。DuckDB を用いた SQL ベースの実装。
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク関数（rank）。
    - research パッケージの __all__ を整備し zscore_normalize をエクスポート。
  - Paper Trading 検証レポート生成ツールを追加（tools/paper_verification_report.py）。
    - CLI で期間指定可（--from / --to / --db）。
    - system_status / trade_logs / risk_logs を集計して稼働率・注文成功率・送信率・P95 レイテンシ等を出力。閾値による PASS/FAIL 判定を実装。
  - ニュース NLP スコアリング基盤を追加（ai/news_nlp.py）。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST 相当）の calc_news_window を実装。
    - OpenAI（gpt-4o-mini）を用いたバッチスコアリングの設計と定数定義（バッチサイズ、リトライ戦略、スコアクリッピング等）。
    - API キー解決、入力トリム（最大記事数 / 最大文字数）やエラーハンドリング方針を定義。
    - （ファイルは長いため途中で実装が続く。）
  - パッケージ初期化情報（__init__.py）とバージョン番号を追加（__version__ = "0.1.0"）。

Changed
- 初期リリースのため該当なし（新規実装中心）。

Fixed
- .env パーサーの堅牢化（export プレフィックス、クォート内部のバックスラッシュエスケープ、インラインコメント扱いの改善）。
- calc_score_weights: 全銘柄のスコアが 0 の場合に等金額配分へフォールバックする挙動を明示し警告ログを追加。
- calc_volatility / calc_momentum 等でデータ不足（窓不足）時に None を返すようにして不正な計算を防止。

Deprecated
- なし

Removed
- なし

Security
- 外部 API キー（OpenAI 等）は明示的に引数または環境変数経由で解決する設計とし、未設定時は ValueError を送出して誤操作を防止。

Notes / Known issues / TODOs
- ai/news_nlp.py は設計と前半処理が実装済みだが、ファイルが途中で切れている（記事取得や API 呼び出しの詳細処理は継続実装が必要）。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価など）は未実装（TODO コメントあり）。
  - 将来的に銘柄別 lot_size をサポートするための拡張を検討中。
- process_priority の優先度設定は権限やプラットフォームに依存するため、権限不足時は警告ログでスキップする挙動。
- run_monitoring は「監視は常に本番 sqlite_path を使用する」との設計（監視データの分離方針）。運用時の期待動作に注意。

作者注記
- 本 CHANGELOG はソースコード内のコメントや実装から推測して作成しています。実際のリリースノートや運用ドキュメントと差異がある場合はそちらを優先してください。