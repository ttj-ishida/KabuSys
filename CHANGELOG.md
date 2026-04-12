CHANGELOG
=========

このファイルは Keep a Changelog 準拠で作成しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

すべての注目すべき変更はここに記載します。

Unreleased
----------

（現在なし）

0.1.0 - 2026-04-12
------------------

Added
- 全体
  - 初回リリース。パッケージ名: kabusys、バージョン 0.1.0 を導入。
  - DuckDB / SQLite を併用したデータ処理基盤を導入（prices_daily, raw_financials, 各種ログ／メトリクステーブル想定）。
- 実行・監視ランナー
  - run_execution.py を追加。
    - ExecutionEngine の起動スクリプト。プロセス優先度を上げてから各コンポーネントを組み立て、セッションを実行。
    - 環境が paper_trading の場合は paper_sqlite_path（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成をサポート（モッククライアントでの paper_trading 対応を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。
  - run_monitoring.py を追加。
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用して監視データを記録。
- 設定（config）
  - Settings クラスを追加し、環境変数と .env ファイルの読み込み・検証を統一。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を探索）。OS 環境変数の保護（protected）機構を有効化。
  - 高度な .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメントの扱い等）。
  - 各種設定プロパティを実装（J-Quants / kabuAPI / LINE / データベースパス / 監視・しきい値 / 環境判定等）。
  - PAPER_FILL_MODE のバリデーションを導入（instant/partial/never/reject）。
- ポートフォリオ構築（portfolio）
  - portfolio_builder: シグナルの候補選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - risk_adjustment: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier（bull/neutral/bear を実装、未知レジームはフォールバック）。
  - position_sizing: 発注株数算出のロジック calc_position_sizes を実装（risk_based / equal / score の allocation_method、lot_size 単位で丸め、aggregate cap と cost_buffer によるスケーリング）。
  - portfolio/__init__.py で主要関数をエクスポート。
  - いずれも純粋関数として設計（DB 参照なし、メモリ内計算）。
- リサーチ（research）
  - factor_research: モメンタム / ボラティリティ / バリュー系ファクター計算（calc_momentum, calc_volatility, calc_value）。DuckDB 接続を受け取り SQL とウィンドウ関数で計算。
  - feature_exploration: 将来リターン算出（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク付けユーティリティ（rank）。
  - research パッケージの __all__ を整備し、zscore_normalize（kabusys.data.stats から）の再エクスポートを含む。
  - 外部ライブラリに依存せず標準ライブラリ / DuckDB のみで実装。
- AI ニュース NLP（ai）
  - news_nlp モジュールを追加。
    - raw_news / news_symbols を集計し OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（ai_score）を生成・ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（target_date ベース、前日 15:00 JST 〜 当日 08:30 JST）を実装。
    - バッチサイズ、1銘柄あたり最大記事数・文字数トリム、バッチごとの JSON Mode 応答検証、スコアの ±1.0 クリップを実装。
    - 429/ネットワーク断/5xx に対する指数バックオフのリトライ（上限）を実装。
    - API キー未設定時の早期エラー判定を実装。
- ツール（tools）
  - paper_verification_report.py を追加。
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から監視・注文ログを集計し、稼働率・注文成功率・送信率・レイテンシ等の指標を出力する検証レポートを実装。
    - CLI 引数 --from / --to / --db に対応。DB が存在しない場合はエラーメッセージを出力して終了。
    - P95 計算、閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を実装。
- ユーティリティ（utils）
  - process_priority モジュールを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を先頭 N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未実装環境では警告を出してスキップするフェイルセーフを備える。
- モニタリング DB 初期化
  - init_monitoring_db 関数（monitoring.monitoring_db 由来と想定）を利用して監視用テーブルの冪等初期化を行う呼び出しを run_execution/run_monitoring で実施。
- その他
  - package の __init__.py にバージョン情報 __version__ = "0.1.0" を設定。
  - 各モジュールに詳細な docstring と設計ノートを併記（将来の拡張点や注意点をコメント）。

Changed
- （初回リリースのため変更履歴はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Deprecated
- （初回リリースのため廃止事項はなし）

Removed
- （初回リリースのため削除事項はなし）

Security
- OpenAI API キーは明示的に引数か環境変数（OPENAI_API_KEY）で指定しない場合エラーとすることで誤動作を防止。
- .env 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト等の安全策）。

Notes / 今後の改善点（コード中コメントより）
- portfolio.position_sizing:
  - 価格（open_prices）欠損時の扱い（0.0 による過少評価）を改善し、前日終値や取得原価でのフォールバックを検討する TODO が残る。
  - 将来的に銘柄別 lot_size を stocks マスタで扱う拡張の余地あり。
- risk_adjustment.calc_regime_multiplier:
  - 未知のレジームで警告して 1.0 にフォールバックする設計。必要に応じて明示的な取扱いを追加可能。
- ai.news_nlp:
  - executemany 前のパラメータ空チェックや部分失敗時のデータ保護（対象コードのみ DELETE → INSERT）など、部分成功の回復戦略を採用。
- config:
  - .env パーサは多くの場合に対応するが複雑なケースのフォールスネガティブに注意。自動ロードはプロジェクトルート検出に依存するため配布後の動作確認が必要。

ライセンス、貢献、バグ報告について
- バグ報告・機能要望はリポジトリの Issue を使用してください。貢献は歓迎します（プルリクを送る前に Issue で相談してください）。

--- 

（以上）