CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングに従います。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-17
-------------------

Added
- 基本アーキテクチャとユーティリティを追加（初回リリース）。
  - パッケージメタ情報
    - kabusys.__version__ = "0.1.0" を導入。
  - 設定・環境変数管理（src/kabusys/config.py）
    - .env / .env.local 自動ロード機能を実装（OS 環境変数優先、.env.local は上書き）。
    - export KEY=val 形式やクォート、インラインコメントを考慮した堅牢なパーサ実装。
    - 必須環境変数取得関数 _require() と Settings クラス（J-Quants / kabu API / DB パス / 監視閾値 等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - 入力値バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX を吸収する set_process_priority(level)。
    - プロセスを最初の N コアに固定する set_cpu_affinity(cpu_count)。
    - 権限・未サポート環境の際は警告ログでフォールバック。
  - 実行 / 監視起動スクリプト
    - 実行エンジン起動スクリプト run_execution.py
      - KABUSYS_ENV=paper_trading 時に paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成。
      - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てとデーモンスレッド実行。
      - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）の取り扱い。
    - 監視起動スクリプト run_monitoring.py
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はフォールバック。
      - 監視は環境にかかわらず本番 sqlite_path を使用する（監視データ一元化）。
      - SystemMonitor の check_once を定期実行、例外時はログを出して次ポーリングに継続。
  - Paper Trading 検証レポートツール（src/kabusys/tools/paper_verification_report.py）
    - SQLite（PAPER_TRADING_SQLITE_PATH）から過去期間の検証指標を集計し、人間向けレポートを出力。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を算出し、閾値比較による PASS/FAIL 判定を行う。
  - ポートフォリオ構築ライブラリ（src/kabusys/portfolio/*.py）
    - portfolio_builder.py
      - select_candidates（スコア降順選定）
      - calc_equal_weights / calc_score_weights（等重・スコア重み配分、全スコア 0 の場合フォールバック）
    - risk_adjustment.py
      - apply_sector_cap（セクター集中制限: 既存保有比率に基づいて候補除外）
      - calc_regime_multiplier（市場レジームに応じた投下資金乗数）
      - ロギングと未知レジーム時のフォールバック挙動を実装
    - position_sizing.py
      - calc_position_sizes（allocation method: risk_based / equal / score 対応）
      - lot_size（単元）丸め、単銘柄上限・aggregate cap（利用可能現金によるスケーリング）、cost_buffer を考慮した安全な配分
      - スケーリング時の端数処理（lot 単位で残差順に追加配分）
  - リサーチ / ファクター計算（src/kabusys/research/*.py）
    - factor_research.py
      - calc_momentum, calc_volatility, calc_value（DuckDB 上で prices_daily / raw_financials を参照し純粋関数で計算）
      - 各種ウィンドウ・欠損取り扱い（十分なデータがなければ None）を実装
    - feature_exploration.py
      - calc_forward_returns（任意ホライズンの将来リターン計算）
      - calc_ic（Spearman ランク相関による IC 計算）
      - factor_summary / rank（基礎統計量とランク付けユーティリティ）
    - research パッケージの公開 API を __init__.py で整理
  - AI ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py, ベータ実装）
    - OpenAI API（gpt-4o-mini）でニュースを銘柄ごとにセンチメント（-1.0〜1.0）評価し ai_scores へ書き込む設計。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策、リトライ（429/5xx 等）と指数バックオフ、レスポンス検証、スコアクリップを備える。
    - calc_news_window(target_date) により JST ウィンドウを UTC に変換するユーティリティを実装。

Changed
- （新規リリースのため変更履歴なし）

Fixed
- （新規リリースのため修正履歴なし）

Deprecated
- （なし）

Removed
- （なし）

Notes / Known issues / TODO
- ai/news_nlp.py は設計が詳細に実装されているものの、現状のコードは（提供ソースの範囲で）途中で切れており、記事取得関数（_fetch_articles など）や一部の後続ロジックが未実装 / 未提供です。OpenAI キー未設定時は明示的に例外を投げます。
- ポートフォリオ関連
  - apply_sector_cap: price_map に価格欠損がある場合のエクスポージャー過小評価のリスクを指摘する TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討する想定。
  - position_sizing: 将来的に銘柄別 lot_size を導入する TODO コメントあり（現状は共通 lot_size）。
- DuckDB / executemany: ai モジュール設計において DuckDB の executemany の制約（空パラメータ禁止）を考慮した実装注意が記載されています。
- プロセス優先度 / CPU affinity: 実行環境によっては権限不足や未サポート API により設定が失敗する可能性があり、その場合は警告ログでフォールバックします。
- run_monitoring は監視用 DB に常に本番 sqlite_path を使用します（監視データの一元化設計）。paper_trading 環境でも監視 DB は本番を参照する点に注意してください。
- run_execution は paper_trading 環境では paper_sqlite_path を使用し、本番 DB と注文ログを分離する設計です。
- 環境変数パーサは多くのケースをカバーしますが、非常に特殊な .env 構文には未対応の可能性があります。
- 複数ファイル内に設計上の TODO コメントが残っています（将来的な機能拡張の目印）。

作者ノート
- 各モジュールは「外部 API への直接アクセスを行わない」設計（リサーチ・ポートフォリオ計算は DuckDB / メモリ内計算に限定）と、paper_trading と本番のデータ分離を重視しています。
- ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）への参照が各所にあり、実運用前にそれら仕様の確認を推奨します。

----- 

（本 CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴・差分に基づく正確な変更履歴はバージョン管理システムのログを参照してください。）