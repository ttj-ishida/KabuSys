# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
重要な変更点・追加機能・バグ修正・既知の制約をコードベースから推測してまとめています。

現在のリリース
----------------

[0.1.0] - 2026-04-17
-------------------

Added
- 全体
  - パッケージ初期リリース相当の機能群を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 実行 / 監視
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite DB（data/paper_trading.db をデフォルト）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動（スレッドで実行）を実装。
    - 停止フラグ（data/stop_requested.flag）を検知してエンジンを停止する仕組みを追加。実行中 PID ファイル（data/execution.pid）を扱う設定を導入。
    - RiskManager のデフォルト設定を含む RiskConfig を導入（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。initial_portfolio_value はブローカーから取得した利用可能現金で初期化。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はロギングしてデフォルトへフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データは一貫した場所に保存）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了する、KeyboardInterrupt による終了をハンドリング。

- 設定 / 環境読み込み
  - config.py: 環境設定管理モジュールを追加。
    - .env/.env.local の自動読み込み機能（プロジェクトルートの検出は .git / pyproject.toml を探索）を提供。OS 環境変数は保護され、.env.local は上書きされる。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env 行パーサー改善: コメント、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープを扱う。
    - Settings クラスを提供し、各種設定値（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / システムフラグ等）をプロパティとして取得可能に。
    - 入力検証: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の有効値チェックを実装。未設定の必須変数参照時は明確な例外を送出。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同スコア時は signal_rank 昇順）で選定。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算。全銘柄スコアが 0 の場合は等配分へフォールバックし WARNING を出力。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を実装（既存保有のセクター別時価を計算し、上限を超えるセクターの新規候補を除外）。"unknown" セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは警告を出して 1.0 にフォールバック。

  - portfolio/position_sizing.py
    - calc_position_sizes: 発注株数算出ロジックを実装（allocation_method: "risk_based", "equal", "score" をサポート）。
    - 単元（lot_size）で丸め、per-position 上限（max_position_pct）や aggregate cap（available_cash）を考慮してスケーリングするロジックを組み込んだ。コストバッファ（cost_buffer）を考慮。
    - risk_based モードでは stop_loss_pct を用いたリスク算出に基づく算出を実装。
    - aggregate スケーリング時に残余キャッシュで端数配分を行う公平化ロジックを実装。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority: Windows / POSIX（Linux, Darwin, FreeBSD）を吸収してプロセス優先度を設定するユーティリティを追加。権限不足や未対応 OS の場合は警告ロギング。
    - set_cpu_affinity: カレントプロセスを先頭 N コアにピン留めするユーティリティを追加。入力検証とエラーハンドリングを実装。

- 研究 / ファクター計算
  - research/factor_research.py
    - calc_momentum: mom_1m/3m/6m および 200日移動平均乖離率を DuckDB 上で効率的に計算する実装を追加（データ不足は None を返す）。
    - calc_volatility: ATR(20) / ATR% / 平均売買代金 / 出来高比率を計算。true_range の NULL 伝播を明示的に扱う。
    - calc_value: raw_financials から直近財務データを取得して PER / ROE を計算。

  - research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターンを一度のクエリでまとめて取得する実装を追加（ホライズン入力検証あり）。
    - calc_ic: スピアマンランク相関（IC）を計算する機能を追加（十分なサンプルがない場合は None）。
    - rank / factor_summary: ランク変換・統計サマリー機能を追加。None 値と非有限数を除外して集計。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポートジェネレータを追加。CLI 引数（--from, --to, --db）をサポート。
    - 稼働率・注文成功率・送信率・P95 レイテンシなどの指標を算出して PASS/FAIL 判定を行う。
    - P95 計算、日付フィルタ生成、DB 存在チェック・例外ハンドリングを含む。

- AI / ニュース NLP（部分実装）
  - ai/news_nlp.py
    - raw_news から銘柄別に記事を集約して OpenAI（gpt-4o-mini）でセンチメントスコアを算出し、ai_scores テーブルへ書き込む設計を追加。
    - バッチ送信、トークン過肥大対策（記事数・文字数制限）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアの ±1.0 でのクリッピング、部分更新（対象コードのみ DELETE → INSERT）等の設計が含まれる。
    - calc_news_window 関数により JST/UTC のニュースウィンドウ計算を提供。
    - （ファイル末尾で処理の途中まで実装されており、その後の _fetch_articles などの補助関数は省略／未表示）

Changed
- なし（初回リリースのため、変更はなし）

Fixed
- なし（初回リリース）

Removed
- なし

Deprecated
- なし

Security
- なし

既知の制約 / 注意点
- run_monitoring は監視用 DB として Settings.sqlite_path（デフォルト data/monitoring.db）を常に使用する設計のため、開発環境と本番環境で監視 DB を分離したい場合は環境変数やコードの分岐で対応が必要。
- ai/news_nlp.py は複雑な外部 API 呼び出しを伴い、API キーやネットワークエラーの処理、レスポンスバリデーションが重要。ファイルは途中で切れているため、実装完了・テストが必要。
- position_sizing の price フォールバック: price_map に価格がない（0）場合、エクスポージャーが過小見積もられブロックが回避される可能性がある旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバックが望ましい。
- .env 読み込みはプロジェクトルート検出に依存する（.git または pyproject.toml）。配布後にルートが特定できない場合は自動ロードをスキップするため、明示的に環境変数を設定する必要がある。
- set_process_priority / set_cpu_affinity は権限不足やプラットフォーム差により期待通り動作しない場合がある（標準出力に警告を出してスキップする）。

今後の提案 / TODO（コード中の注記に基づく）
- stocks マスタに単元（lot_size）を持たせ、銘柄別の lot_map をサポートすることで position_sizing を拡張する。
- position_sizing の価格欠損時のフォールバック価格ロジックを実装する（前日終値や取得原価）。
- ai/news_nlp.py の残り実装（記事フェッチ、API 呼び出しループ、DB 書き込み）と十分なリトライ/部分コミットのテストを完了する。
- run_monitoring/run_execution の PID / フラグファイルの運用・ローテーション・クリア動作をドキュメント化する。

補足
- 本 CHANGELOG はソースコード内の設計コメント・ログ文・関数名・引数・注釈等から推測して作成しています。実際のリリース履歴が別途ある場合はそちらを優先してください。