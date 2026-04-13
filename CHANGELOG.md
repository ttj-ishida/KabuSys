CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースから推測して作成した変更履歴です（自動生成のため表現は推測を含みます）。

[Unreleased]


[0.1.0] - 2026-04-13
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0 を導入。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

- 実行系 / 監視起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイントを追加。
    - 環境に応じてブローカークライアントを生成（BrokerClientFactory を使用）。
    - paper_trading 環境では paper_trading 専用の SQLite DB を使用して本番 DB と分離。
    - 監視テーブルが存在することを保証するため init_monitoring_db を呼び出し（冪等）。
    - プロセス優先度を起動時に "high" に設定する処理を追加。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec など）を実装。
    - ExecutionEngine を起動してセッションを実行し、終了時に DB を確実にクローズ。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - MONITOR_POLL_INTERVAL に不正な値（0 以下や整数以外）が指定された場合は警告を出しデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定、DuckDB 接続を利用。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。OS 環境変数の上書きを防ぐ protected 機構を実装。
    - .env ファイルの堅牢な行パースを実装（export 形式、シングル/ダブルクォートのエスケープ対応、インラインコメント処理など）。
    - Settings クラスを導入し、各種環境変数アクセスをプロパティ化（DB パス、API トークン、PID/kill フラグのパス、監視閾値、環境判定など）。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値検証を実装（不正値は例外を送出）。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム非依存でプロセス優先度を設定するユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）の差分を吸収して nice/priority を設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
    - アクセス権限や未実装 API を安全にスキップするための警告処理を実装。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等配分/スコア加重配分 (calc_equal_weights, calc_score_weights) を実装。
    - スコアが全て 0 の場合は等配分にフォールバックして警告を出力。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有のセクター別エクスポージャー計算、除外ロジック、"unknown" セクター無視）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear マッピング、未知レジームは警告のうえ 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - ポジションサイズ算出ロジック calc_position_sizes を実装。
      - allocation_method="risk_based" / "equal" / "score" をサポート。
      - 単元株（lot_size）で丸め、1 銘柄上限・集計上限（available_cash）を考慮したスケールダウンアルゴリズムを実装。
      - cost_buffer を加味した保守的コスト見積り、残余キャッシュでの端数配分ロジックを実装。
      - 価格欠損時のスキップやログ出力を実装。
    - 将来的な拡張点（銘柄ごとの lot_size マップなど）を TODO コメントで明示。

- 研究・因子計算
  - research/factor_research.py
    - Momentum（1m/3m/6m、MA200乖離）、Volatility（ATR20、平均売買代金、出来高比率）、Value（PER/ROE）などの因子計算を実装。
    - DuckDB の SQL ウィンドウ関数を用いた効率的な実装（必要行数チェック、欠損処理を含む）。
  - research/feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン、入力検証あり）。
    - IC（Spearman ランク相関）計算 calc_ic、ランク化ユーティリティ rank、ファクター統計要約 factor_summary を実装。
    - 外部依存を使わない実装（標準ライブラリのみ）を志向。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI API（gpt-4o-mini）を使って銘柄ごとのセンチメントをスコア化して ai_scores テーブルへ書き込む機能を追加。
    - バッチ処理（最大 20 銘柄/バッチ）、記事数・文字数トリム、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフのリトライを実装。
    - タイムウィンドウ計算（JST 基準の前日 15:00 〜 当日 08:30）を実装する calc_news_window。
    - API キー解決やフェイルセーフ（API 未設定時は ValueError）を実装。
    - （実装方針として）ルックアヘッドバイアスを避けるため datetime.today()/date.today() を参照しないよう留意。

- CLI ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI を追加（--from/--to/--db オプション対応）。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出。
    - P95 計算、日付フィルタ生成、閾値による PASS/FAIL 判定（稼働率 99% 等）を実装。
    - DB が存在しない場合の適切なエラーメッセージ出力を実装。

Changed
- DB 周りの設計方針を明確化
  - 監視関連は環境に依存せず本番 sqlite_path を参照する仕様を明示。
  - paper_trading 環境では paper_trading 専用の SQLite を使用し、本番 DB と分離する方針を導入。

- .env 読み込み
  - 自動読み込みの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を導入（テスト等で自動読み込みを抑止可能）。

Fixed
- 環境変数の堅牢性向上
  - MONITOR_POLL_INTERVAL に 0 以下や非整数が指定された場合のハンドリングを追加し、time.sleep に渡す不正値による例外を回避。
  - .env のクォート/エスケープ/インラインコメント処理による誤読を修正（より現実的な .env フォーマットに対応）。

- DB 初期化の冪等性
  - init_monitoring_db の呼び出しを追加し、監視テーブルが存在しない場合でも安全に起動できるようにした。

Security
- API キーの取り扱い
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から読み取り、未設定時は明示的にエラーを返すようにした（無条件で露出しないように注意）。

Notes / Known limitations
- ai/news_nlp.py は設計方針や主要ロジックを実装しているが、長いファイルの一部が途中で切れている可能性がある（ログや DB 書き込みの最終処理は実装済みと推測されるが、実運用前に追加確認が必要）。
- position_sizing の将来的な拡張（銘柄ごとの lot_size マスタ、価格フォールバック）は TODO として残している。
- research / factor 計算は DuckDB のテーブル構成（prices_daily, raw_financials 等）に依存するため、実データ投入後のテストが必要。

以上が現在のコードベースから推測できる主な変更点・機能一覧です。必要であれば、各項目をさらに詳しく（該当ソース行や関数の説明付きで）展開します。