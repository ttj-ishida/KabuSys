CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  
リリースは "Added / Changed / Fixed" セクションで記載します。

Unreleased
----------

（現在のところ未リリースの差分はありません。）

0.1.0 - 2026-04-13
------------------

Added
- 基本パッケージ初期実装を追加
  - パッケージバージョンを __version__ = "0.1.0" として公開。

- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動エントリポイントを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite DB を使用（data/paper_trading.db をデフォルト）して本番 DB と分離。  
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行。
    - リソース確保のため DuckDB / SQLite 接続を確立し、終了時に確実にクローズ。

  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値はデフォルトにフォールバック。  
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。

- 設定管理
  - config.py: .env 自動読み込み・パース実装を追加。  
    - プロジェクトルート探索（.git / pyproject.toml 基準）を行い、.env / .env.local を自動ロード（OS 環境変数を優先、.env.local は上書き可能）。  
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションをサポート。  
    - 細かい .env パーシング機能を実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理）。  
    - Settings クラスでアプリケーション設定をラップ（各種環境変数の取得・検証を提供）。  
    - 設定項目例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE（検証あり）、PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値, KABUSYS_ENV, LOG_LEVEL 等。

- ポートフォリオ構築ユーティリティ
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選択（signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 重み計算（スコア全ゼロ時は等配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有評価、当日売却予定の除外対応）。unknown セクターは上限適用対象外。  
    - calc_regime_multiplier: 市場レジームに対する投下資金乗数（bull/neutral/bear のマッピング、未知の場合は警告とフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method を等配分/スコア加重/リスクベースでサポート。  
    - 単元株（lot_size）丸め、1 銘柄上限・全体投下上限（available_cash）に応じたスケーリング処理、cost_buffer を考慮した保守的見積り、残余配分の端数処理等を実装。

- 研究・ファクター計算
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（データ不足時は None）。DuckDB による窓関数利用で効率化。  
    - calc_volatility: ATR(20)・相対 ATR・平均売買代金・出来高比率を計算。true_range の NULL 伝播を明示的に制御。  
    - calc_value: raw_financials から最新財務データを結合して PER/ROE を算出。
  - research.feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを一括取得（デフォルト [1,5,21]）。入力検証あり。  
    - calc_ic / rank / factor_summary: スピアマン IC 計算（ランク相関）、順位付け（同位は平均ランク）、ファクター統計サマリー（count/mean/std/min/max/median）を提供。  
  - research パッケージでは zscore_normalize を外部 (kabusys.data.stats) から再エクスポート。

- ニュース NLP（AI）統合
  - ai.news_nlp:
    - raw_news を OpenAI（gpt-4o-mini）にバッチ送信して銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ書き込み。  
    - タイムウィンドウは JST ベース（前日 15:00 ～ 当日 08:30）を UTC に変換して取得。calc_news_window を提供。  
    - バッチ処理（最大 20 銘柄/コール）、記事・文字数トリム、429/ネットワーク/5xx に対する指数バックオフ（最大リトライ回数設定）、レスポンス検証、スコアクリッピング、部分失敗時の既存データ保護（対象コード絞り込みで DELETE→INSERT）などフェイルセーフ設計。  
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。

- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成スクリプトを追加。  
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、P95 レイテンシを算出し、閾値比較（アップタイム 99%、fill 90%、send 95%、P95 latency 200ms）による PASS/FAIL 判定を出力。  
    - コマンドライン引数 --from/--to/--db をサポート。DB 無しやテーブル欠損時のフェイルセーフ処理（OperationalError を補足）。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収して優先度設定を提供（high/normal/low）。AccessDenied 等を穏やかに扱い警告ログでスキップ。  
    - set_cpu_affinity: 最初の N コアにプロセスをピンニングするユーティリティ（None で無効）。引数検証と例外処理を実装。

Changed
- データベース取り扱い方針
  - 監視（run_monitoring）は環境にかかわらず本番 sqlite_path を参照する仕様に明確化。  
  - 実行エンジンは paper_trading 環境で専用 DB を使用することで、本番 DB と完全分離する設計に変更/確立。

- .env ロード戦略
  - 読み込み優先順は OS 環境変数 > .env.local > .env。OS 環境変数は保護され、.env.local は OS 環境変数を上書きしないよう保護を導入。

- 設定検証強化
  - Settings の各プロパティに入力検証を追加（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の有効値チェック）。不正値は ValueError を送出して早期検知。

Fixed
- 環境変数/設定の堅牢化
  - .env パーサでクォート内のバックスラッシュエスケープやインラインコメント処理を正しく扱うように修正（以前の簡易実装での誤解析を回避）。  
  - MONITOR_POLL_INTERVAL のパースで 0 以下や非整数値が指定された場合に警告を出してデフォルトにフォールバックするように修正（time.sleep に渡す不正値回避）。  
  - process_priority 設定で権限不足や未対応プラットフォーム発生時に例外で止めないよう例外処理を追加（警告ログでスキップ）。  
  - calc_score_weights: 全銘柄のスコア合計が 0 の場合に等金額配分へフォールバックし警告を出すように修正。

Notes
- DuckDB / SQLite を併用する設計のため、各モジュールは接続オブジェクトを受け取り純粋関数的に動作する箇所と、実行時に接続を開いて使用する箇所が混在しています。テスト時は環境変数で DB パスを切り替えてください。
- OpenAI 等外部 API を使う機能は API キーの管理・利用制限に注意してください。API 呼び出しはリトライ・バリデーションのフェイルセーフを備えていますが、運用時のエラー監視を推奨します。

--- 
（以上）