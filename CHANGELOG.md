CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に基づきます。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-17
-------------------

Added
- 初期リリース: KabuSys v0.1.0 を追加。
- 基本構成・環境変数管理:
  - Settings クラス（src/kabusys/config.py）を実装。.env/.env.local の自動読み込み機能、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化、プロジェクトルート自動検出（.git または pyproject.toml）をサポート。
  - .env パーサーを堅牢化（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープの処理、行内コメント処理）。
  - 必須環境変数未設定時は _require() が例外を送出することで早期検出。

- 実行・監視用エントリポイント:
  - 実行エンジン起動スクリプト run_execution（src/kabusys/run_execution.py）を追加。
    - ExecutionEngine をスレッドで起動・監視し、data/execution.pid を利用。
    - KABUSYS_ENV=paper_trading 時は専用 paper_trading DB（data/paper_trading.db、PAPER_TRADING_SQLITE_PATH で上書き可）を使用し、本番 DB と完全分離。
    - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ file による外部停止検知（data/stop_requested.flag）。
  - 監視ループ起動スクリプト run_monitoring（src/kabusys/run_monitoring.py）を追加。
    - SystemMonitor の単発チェックをループで定期実行。ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き（デフォルト 60 秒）。
    - 監視用途では KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明記。
    - 停止フラグ検知でループ終了。

- DB / 分析基盤:
  - DuckDB と SQLite の両方を利用する設計を導入（Settings でパス管理）。
  - monitoring 用 DB 初期化ユーティリティ init_monitoring_db（参照）を run スクリプトで呼び出し、テーブル存在保証。

- Portfolio（銘柄選定・配分）:
  - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights（src/kabusys/portfolio/portfolio_builder.py）。
    - スコア降順ソート、同点の tie-break に signal_rank を使用。
    - スコア合計が 0 の場合に等金額配分へフォールバック。
  - risk_adjustment: apply_sector_cap（セクター過集中除外）, calc_regime_multiplier（市場レジームに応じた乗数）（src/kabusys/portfolio/risk_adjustment.py）。
    - セクター不明("unknown") はセクター上限適用除外、既存保有の売却予定銘柄の除外対応。
    - 未知レジームではログ警告の上 1.0 でフォールバック。
  - position_sizing: calc_position_sizes（株数決定ロジック）（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score の配分方式を実装。
    - 単元（lot_size）丸め、1 銘柄上限・合計投下上限（available_cash）でスケールダウン、cost_buffer（手数料・スリッページ見積り）を加味した保守的算出。
    - aggregate cap 適用時の端数処理（lot 単位での再配分ロジック）を実装。
    - 将来的な拡張点として銘柄別 lot_size マップへの対応 TODO を明記。

- 研究（Research）機能:
  - factor_research:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）、calc_volatility（ATR20、流動性指標）、calc_value（PER/ROE）を実装（src/kabusys/research/factor_research.py）。
    - DuckDB SQL を用いて prices_daily / raw_financials を参照する形で高速に計算。
  - feature_exploration:
    - calc_forward_returns（将来リターン）、calc_ic（Spearman ランク相関による IC）、factor_summary（統計サマリ）、rank（ランク付け）を実装（src/kabusys/research/feature_exploration.py）。
    - pandas 等の外部依存を使わず標準ライブラリで実装。
  - research パッケージの __all__ を整備し、zscore_normalize（data.stats 依存）も再エクスポート。

- AI / ニュース NLP:
  - ai/news_nlp.py を追加。
    - OpenAI（gpt-4o-mini）を用いたニュース記事のセンチメントスコアリング設計を実装。
    - 処理フロー: タイムウィンドウ計算、銘柄毎記事集約（最大記事数・最大文字数でトリム）、最大20銘柄ずつのバッチ送信、429/ネットワーク/5xx のリトライ（指数バックオフ）、レスポンス検証、スコア ±1.0 クリップ、部分成功時の db 上書き保護（対象コードのみ置換）等を設計仕様として実装。
    - calc_news_window（ニュース収集ウィンドウ UTC 計算）を実装。
    - score_news の雛形（API キー解決、ウィンドウ計算、記事集約フェーズの開始）を実装。注: ファイル末尾が途中で切れており score_news の完全実装は未完（実装途中）。
  - 大量 API 呼び出しに備えた設計（バッチ、トリム、リトライ）を導入。

- ツール:
  - tools/paper_verification_report.py を追加。
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率・送信率、リスク却下数、レイテンシ統計 P95 等）を集計し、PASS/FAIL 判定付きの CLI レポートを出力。
    - 日付フィルタ (--from / --to)、--db オプションをサポート。閾値はソースコード中で定義（稼働率 99% など）。
    - DB が未作成やテーブル欠損の場合に N/A を返すなど堅牢性を確保。

- ユーティリティ:
  - process_priority（src/kabusys/utils/process_priority.py）を実装。
    - Windows / POSIX(Linux/Mac/FreeBSD) を吸収してプロセス優先度（high/normal/low）を設定。set_cpu_affinity で CPU ピンニング機能も提供。
    - 権限不足や未対応 OS の場合は警告ログを出すフェールセーフ。

Changed
- 初期リリースのため該当なし。

Fixed
- MONITOR_POLL_INTERVAL のパースを堅牢化（0 以下や非数値はデフォルトにフォールバックし、警告ログを出力）（src/kabusys/run_monitoring.py）。

Security
- 環境変数管理で秘匿情報（API キー等）は Settings 経由で明示的に要求する設計。未設定時は早期に ValueError を送出。

Known issues / Notes
- ai/news_nlp.py の score_news はファイル末尾が途中で切れており、記事フェッチ/API 呼び出し/DB 更新の最終処理が未完です。実運用前に実装完了と十分な検証が必要です。
- position_sizing の価格欠損時（price == 0.0）に関する挙動について TODO コメントあり（前日終値等のフォールバックを検討）。
- 一部処理は DuckDB のバージョンや SQLite スキーマに依存（本番投入前にデータスキーマの整合性確認が必要）。
- process_priority / set_cpu_affinity は権限やプラットフォームによっては無視される場合があり、その場合は警告ログで通知されます。

Authors
- コードベースの初期実装一式（複数モジュール）をまとめてリリース。

References
- 追加・実装されたモジュールは src/kabusys 以下を参照してください。