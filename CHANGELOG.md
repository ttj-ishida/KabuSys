CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。
フォーマットは「Keep a Changelog」に準拠しています。
（https://keepachangelog.com/ja/1.0.0/）

Unreleased
----------

（現在のブランチに未リリースの変更はありません）

0.1.0 - 2026-04-17
------------------

初回リリース。自動売買システム "KabuSys" のコア機能群を実装しました。
以下は主な追加機能・設計上のポイントと細かな挙動改善の一覧です。

Added
- 基本パッケージ情報
  - pakage 初期バージョンを定義: kabusys.__version__ = "0.1.0"

- 設定管理（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml ベース）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - より堅牢な .env パーサ（export フォーマット、引用符内のバックスラッシュエスケープ、インラインコメント処理）
  - 環境変数の必須チェック関数 _require と Settings クラスを提供
  - 各種設定プロパティを実装（DB パス、Paper Trading 設定、監視しきい値、環境名/ログレベル検証 など）
  - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）

- 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
  - ExecutionEngine 起動ロジックを実装
  - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用（data/paper_trading.db がデフォルト）／本番 DB と分離
  - BrokerClientFactory 経由でブローカークライアントを生成（MockBrokerClient の切替を想定）
  - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて Engine を起動
  - RiskManager にデフォルト RiskConfig を導入（max_position_pct, max_utilization, rate_limit_per_sec, ...）
  - Engine は別スレッドで run_session を実行。停止フラグ（data/stop_requested.flag）を検出して安全に停止
  - 実行 PID ファイル（data/execution.pid）サポート

- 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
  - SystemMonitor のポーリングループを実装
  - 環境に関わらず監視は本番 sqlite_path を使用
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書きが可能（デフォルト 60 秒）
  - 不正な MONITOR_POLL_INTERVAL はデフォルトにフォールバックして警告ログを出力
  - 停止フラグ（data/stop_requested.flag）検知によるループ終了、KeyboardInterrupt のハンドリング

- 監視 DB 初期化ユーティリティ呼び出し（init_monitoring_db）を run_* スクリプトから呼出し、監視テーブルの存在を保証

- プロセス優先度 / CPU 固定ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) — Windows / POSIX を吸収した共通インターフェース
  - set_cpu_affinity(cpu_count) — 指定コア数にプロセスを固定
  - 設定失敗時は警告ログを出してフォールバック

- ポートフォリオ構築ライブラリ（src/kabusys/portfolio/*）
  - 候補選定・重み計算（portfolio_builder.py）
    - select_candidates: スコア降順、同点は signal_rank 小さい方を優先
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等分配にフォールバックして WARNING）
  - セクター制約・レジーム乗数（risk_adjustment.py）
    - apply_sector_cap: 既存保有を考慮したセクター集中制限（sell_codes により当日売却予定を除外可能）
    - calc_regime_multiplier: "bull"/"neutral"/"bear" マッピング、未知レジームは警告して 1.0 にフォールバック
  - ポジションサイズ計算（position_sizing.py）
    - risk_based / equal / score の割付方式を実装
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）適用、aggregate cap（available_cash）によるスケールダウン
    - cost_buffer を加味した保守的コスト見積り、余剰キャッシュでの端数配分ロジック

- 研究（research）モジュール（src/kabusys/research/*）
  - factor_research.py
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials を用いたファクター計算
    - 200日 MA や ATR 等をウィンドウ集計で算出（データ不足時には None を返す）
  - feature_exploration.py
    - calc_forward_returns: 任意ホライズンの将来リターン計算（複数ホライズンを一括取得）
    - calc_ic: スピアマンランク相関（IC）計算（結合・None 除外・有効レコード数チェック）
    - rank / factor_summary: 順位付け（同順位は平均ランク）や統計サマリ（count/mean/std/min/max/median）

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI API（gpt-4o-mini 想定）でセンチメント付与して ai_scores テーブルへ書き込む処理を実装
  - ニュース対象ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ（calc_news_window）
  - バッチ送信（最大 _BATCH_SIZE=20）、記事トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
  - API エラー（429、ネットワーク、タイムアウト、5xx）に対する指数バックオフのリトライ
  - レスポンス検証、スコアを ±1.0 にクリップ、部分成功時の DB 更新戦略（該当コードのみ置換）
  - API キーは引数 or 環境変数 OPENAI_API_KEY から解決。未設定なら ValueError を送出

- CLI ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 用検証レポート生成スクリプトを追加
  - 指標:
    - 稼働率（uptime）しきい値 99.0%
    - 注文成立率（fill rate）しきい値 90.0%
    - 送信率（send rate）しきい値 95.0%
    - P95 レイテンシしきい値 200 ms
  - 日付フィルタ（--from / --to）、--db による DB パス指定、PAPER_TRADING_SQLITE_PATH 優先
  - 各種クエリの実行と PASS/FAIL 判定を出力（N/A/データなしの扱いに配慮）
  - P95 の計算実装（_p95）

Changed
- 全体のログ出力レベルを INFO 基準で初期化する箇所を複数のエントリポイント（run_*）に追加
- DuckDB / SQLite を併用する設計（分析用 DuckDB と 状態保存用 SQLite の使い分け）

Fixed / Robustness improvements
- MONITOR_POLL_INTERVAL が不正（非整数、0 以下 等）でもデフォルトにフォールバックして監視ループが停止しないように警告と保護処理を追加（run_monitoring.py）
- process_priority の未対応 OS / 権限不足時は警告ログでスキップ（psutil の例外を補足）
- .env の読み込み失敗時（ファイル IO エラー）を警告に変換してプロセス停止を防止
- 各種集計関数で対象データが存在しない場合に None / 0 を返すなど、DB スキーマ未整備やデータ不足に耐性を持たせた実装
- feature_exploration.rank: 浮動少数の丸めで ties 検出漏れを防ぐため round(v, 12) を用いる

Notes / Implementation details
- 多くのモジュールは「DB を直接更新する」「外部 API にアクセスする」箇所を分離しており、テストや Paper Trading（モック）での実行を想定した設計になっています。
- DuckDB を分析向けに併用し、prices_daily/raw_financials の SQL 集計を中心にファクターや統計を計算します。
- Paper Trading と Live のデータ分離を厳格に行い、本番データの汚染を防止する設計方針を採用しています。
- いくつかの TODO コメントや将来的な拡張点（銘柄別 lot_size、前日の終値などの価格フォールバック等）がソース内に残っています。

Security
- 特に機密情報の扱いに関しては、環境変数経由でのキー管理を想定しています（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
- .env の自動上書きは OS 環境変数を protected として扱い、上書きを制御する仕組みを実装しています。

Deprecated
- なし

Removed
- なし

Acknowledgements / Contributors
- 本初版は主要機能の実装にフォーカスしています。今後はテストカバレッジの拡充、CLI/ドキュメントの整備、運用に関する監視・アラート強化を予定しています。

もし CHANGELOG に追記したい差分（例えば細かいバグ修正や挙動の変更点）があれば、該当ファイル名と簡単な説明を教えてください。必要に応じて追記・修正します。