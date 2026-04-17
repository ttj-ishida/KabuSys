# CHANGELOG

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) 準拠の形式を採用しています。

現在のリリース履歴:

## [Unreleased]
注記:
- news_nlp モジュール（OpenAI を用いたニュースセンチメント集計）は実装が進行中です。一部処理（記事フェッチ以降のコード）が未完のため、まだ本番運用には注意が必要です。
- 今後のリリースで E2E テストやエラーハンドリング強化、OpenAI レート制御の調整を行う予定です。

---

## [0.1.0] - 2026-04-17
初回公開リリース。システム全体の主要コンポーネントを実装しました。

### Added
- 全体
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = 0.1.0）。
  - アプリケーション設定管理クラス Settings を実装。環境変数と .env / .env.local ファイルの自動読み込み機能を提供。
  - .env 読み込みのための詳細なパーサ（クォート処理・エクスポート構文・インラインコメント取り扱い対応）を実装。
  - 自動ロードの無効化オプション（KABUSYS_DISABLE_AUTO_ENV_LOAD）を実装。

- 実行・監視
  - run_execution.py: ExecutionEngine を起動するためのエントリポイントを実装。
    - 環境に応じた DB 分離（paper_trading 環境では専用 SQLite を使用）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を構築。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止処理、および実行 PID ファイル管理。
    - スレッドでのエンジン実行と監視ループをサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は本番用 sqlite_path を使用し、停止フラグでループを終了可能。
    - init_monitoring_db による監視テーブル初期化。

- ユーティリティ
  - utils.process_priority: プロセス優先度（Windows / POSIX）と CPU affinity を設定するユーティリティを実装。
    - 権限不足や未対応 OS を考慮したフォールバックと警告を実装。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity を提供。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのソートと上位選択。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限（既存持ち高を計算して候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数。
  - portfolio.position_sizing:
    - calc_position_sizes: weight / candidates / risk ベースで発注株数を算出。単元株（lot_size）丸め、per-stock 上限、aggregate cap、コストバッファ考慮などを実装。
    - risk_based / equal / score の allocation_method をサポート。

- 研究（Research）
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算（DuckDB を用いた SQL 実装）。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率の計算。
    - calc_value: EPS/ROE を用いた PER・ROE の計算（raw_financials の最新レコードを参照）。
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1/5/21）に対する将来リターンの計算。
    - calc_ic: スピアマンランク相関（IC）の計算（欠損や ties を考慮）。
    - factor_summary / rank: ファクターの基本統計量・ランク変換ユーティリティ。
  - research パッケージは zscore_normalize を data.stats からエクスポートして統合。

- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成スクリプトを実装。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（P95 等）を集計して PASS/FAIL 判定を出力。
    - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。

- AI / ニュースNLP
  - ai.news_nlp:
    - raw_news と news_symbols を銘柄単位に集約し、OpenAI (gpt-4o-mini, JSON Mode) へバッチ送信してセンチメントを ai_scores テーブルに書き込む設計を実装。
    - ニュース収集ウィンドウの算出（JST の前日 15:00 ～ 当日 08:30 を UTC に変換）関数 calc_news_window を実装。
    - バッチサイズ・トークン肥大化対策、リトライ（指数バックオフ）、レスポンスバリデーション、スコアの ±1.0 クリップ等の設計方針を定義。
    - （注）記事フェッチ以降の処理が未完の箇所あり（実装中）。

### Changed
- 設定読み込みロジック
  - .env の読み込み順を OS 環境変数 > .env.local > .env に明確化。OS 環境変数は protected として上書きされない。
  - .env パーサで export 構文・クォート内のバックスラッシュエスケープ・インラインコメント処理をサポートし、より堅牢な読み込みを実現。

- DB 周りの振る舞い
  - 監視テーブルの初期化を冪等に実行（init_monitoring_db 呼び出しで既存 DB を壊さない）する仕様に統一。
  - run_execution は paper_trading 環境では paper_sqlite_path を使用して本番 DB と分離。

- 実行環境の扱い
  - Settings.env の検証（development / paper_trading / live のみ許可）を追加し、不正値時に早期失敗させるようにした。
  - PAPER_FILL_MODE の許容値（instant/partial/never/reject）の検証を追加。

### Fixed
- run_monitoring._get_poll_interval:
  - MONITOR_POLL_INTERVAL 環境変数が不正（非整数や 0 以下）でもデフォルトにフォールバックし、警告ログを出すように改善（time.sleep に渡して ValueError にならないように）。
- utils.process_priority:
  - 未対応 OS や権限不足でのエラーをキャッチして警告に切り替えることで、プロセス起動時に例外で終了しないようにした。
- portfolio.calc_score_weights:
  - 全銘柄のスコア合計が 0 の場合に等金額配分へフォールバックし、警告を出すようにした。
- research.feature_exploration:
  - calc_forward_returns の horizons 入力検証を追加（正の整数かつ上限 252 日）。

### Security
- 環境変数管理において OS の既存環境変数を保護する設計（protected set）を導入し、.env による上書きを制限。

---

今後の予定（例）
- news_nlp の記事取得〜API コール〜DB 書き込み処理の完成と E2E テストの追加。
- ExecutionEngine / Broker インターフェースのテストカバレッジ強化。
- DuckDB クエリのパフォーマンス最適化（インデックス/パーティショニング検討）。
- 単体・統合テスト用の .env テストフィクスチャ整備。

--- 

(注) この CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴や設計意図と一部差異がある場合があります。必要に応じて実際の変更履歴（git log 等）に基づく更新を行ってください。