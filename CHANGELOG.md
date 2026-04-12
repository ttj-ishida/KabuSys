CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。
フォーマットは "Keep a Changelog" に準拠し、語彙は日本語で記載しています。

ルール:
- バージョンは下へ向かって古くなります（最新が上）
- 日付は YYYY-MM-DD 形式

[Unreleased]
------------

現在の最新版に対する保留中の変更点はありません。

0.1.0 - 2026-04-12
-----------------

Added
- 初期リリース。以下の主要機能を提供。
  - 実行・監視ランナー
    - run_execution.py: ExecutionEngine を起動する CLI エントリポイントを追加。
      - KABUSYS_ENV=paper_trading 時に MockBrokerClient を使用し、paper_trading 用の SQLite DB (デフォルト: data/paper_trading.db) に完全分離して記録。
      - ブローカークライアントの生成を BrokerClientFactory で抽象化。
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を構築。
    - run_monitoring.py: システム監視ループの起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境に関わらず本番用 sqlite_path を使用して状態を記録。
      - プロセス優先度設定（High）を起動時に行うフローを組み込み。

  - 設定管理
    - config.py: 自動 .env ロード機能を追加（プロジェクトルートを .git または pyproject.toml から判定）。
      - 読み込み順序: OS環境変数 > .env.local > .env（OS 環境変数は保護され上書きされない）。
      - .env パーサを実装し、export プレフィックス、引用符で囲まれた値、インラインコメント等に対応。
      - Settings クラスで多くの設定プロパティを提供（DB パス、Paper Trading 設定、監視閾値、PID/KILL ファイルパス、環境判定、ログレベル等）。
      - 環境変数の検証を追加（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。

  - プロセス/CPU ユーティリティ
    - utils/process_priority.py:
      - プラットフォーム差異を吸収してプロセス優先度（high/normal/low）を設定する set_process_priority() を実装。
      - CPU affinity を設定する set_cpu_affinity() を実装（サポートされる OS に限定）。
      - 許可されない操作の際には警告ログを出力して安全にフォールバック。

  - ポートフォリオ構築（純粋関数）
    - portfolio.portfolio_builder:
      - select_candidates: BUY シグナルをスコア降順に並べ上位を選択。
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供。全スコアが 0 の場合は等配分にフォールバック。
    - portfolio.risk_adjustment:
      - apply_sector_cap: セクター集中用上限判定（既存保有を基に新規候補を除外）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）。
    - portfolio.position_sizing:
      - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数算出。単元株（lot_size）丸め、max_position_pct, max_utilization, cost_buffer を考慮した aggregate cap スケーリングを実装。

  - 研究用モジュール（DuckDB ベース）
    - research.factor_research:
      - calc_momentum: 1M/3M/6M リターン・MA200 乖離率を計算。
      - calc_volatility: ATR20, 相対 ATR, 20日平均売買代金, 出来高比率を計算。
      - calc_value: raw_financials と株価を組み合わせて PER/ROE を計算。
      - いずれも DuckDB 接続を受け取り SQL で効率的に処理。
    - research.feature_exploration:
      - calc_forward_returns: 指定ホライズンの将来リターンを算出（horizons 検証あり）。
      - calc_ic: スピアマンランク相関（IC）を実装（欠損・同値処理に配慮）。
      - factor_summary / rank: 基本統計量・ランク計算ユーティリティ。

  - AI ニュース NLP スコアリング
    - ai.news_nlp:
      - raw_news を OpenAI (gpt-4o-mini) でセンチメントスコアリングして ai_scores に書き込むスクリプト群を実装。
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を正確に算出。
      - 銘柄毎に記事を集約し、1 銘柄あたりの文字数・記事数を制限してトークン肥大化対策を実施。
      - 最大 20 銘柄/バッチで API 呼び出し、429/ネットワーク/5xx は指数バックオフでリトライ。
      - API レスポンスのバリデーション、スコアの ±1.0 クリップ、部分成功時のテーブル更新戦略（該当コードのみ置換）を実装。
      - OpenAI API キーの未設定時は明示的なエラーを返す。

  - ツール
    - tools.paper_verification_report:
      - Paper Trading 検証レポート生成コマンドラインツールを追加。
      - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を出力。
      - P95 計算、期間フィルタ、DB パスのオプション指定をサポート。

Changed
- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を設定。
- .env 自動ロード
  - プロジェクトルートの検出を __file__ を基点に行うようにし、CWD に依存しない設計に改善。
  - .env の読み込み時に OS 環境変数を保護する protected 機能を導入（.env.local の上書きルールを含む）。
- DB 接続ポリシー
  - 監視 (run_monitoring) は環境に関係なく本番の sqlite_path を使用する設計に明文化。
  - Execution は paper_trading 環境用に DB を分離（settings.is_paper に基づく切替）。

Fixed
- 入力検証とフォールバックの強化
  - MONITOR_POLL_INTERVAL: 非整数や 0 以下の値を検出してデフォルト (60 秒) にフォールバックし、警告ログを出力。
  - PAPER_FILL_MODE: 許容値以外を指定した場合に ValueError を送出して明示的に失敗させるように改善。
  - calc_forward_returns: horizons 引数の検証を強化（正の整数で 252 以下）。
  - rank / calc_ic: 同順位（ties）処理で丸め誤差に伴う検出漏れを回避するため round(v, 12) を用いる安定化。
  - 多くの集計関数で None / 空リストを扱う際に N/A 表示や None を返すなどフェイルセーフを追加。

Known issues / Notes
- apply_sector_cap の現状の価格欠損処理:
  - price_map に価格が欠けている（0.0）場合、セクターエクスポージャーが過小評価され、ブロックが外れる可能性がある旨を TODO コメントで明記。将来的な価格フォールバック（前日終値など）を検討。
- CPU affinity の動作は OS に依存し、未対応プラットフォームではスキップされる。
- ai.news_nlp の書き込みは部分成功時に該当コードのみを入れ替える設計だが、完全なトランザクション保証は DuckDB のバージョン差に依存する可能性がある（executemany のパラメータ非空チェック等の配慮あり）。
- OpenAI API を使う機能は API キーが必須。キー未設定時は明示的な ValueError が発生する。

Authors
- KabuSys 開発チーム（コードベースから推測して記載）

ライセンス
- リポジトリ内に別途明示がなければ、プロジェクトの既定に従うこと。