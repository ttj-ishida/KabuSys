Changelog
=========

すべての重要な変更は Keep a Changelog の方針に従って記載しています。
このファイルは人間に読みやすく、バージョン間の差分を把握しやすくすることを目的とします。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

Unreleased
----------

（現在未リリースの変更はありません）

0.1.0 - 2026-04-17
-----------------

Added
- 基本パッケージ初期リリースを追加。
  - パッケージバージョン: __version__ = 0.1.0

- 実行エントリ / デーモン制御
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ data/stop_requested.flag を検出して安全にループを終了。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は実行環境にかかわらず本番 sqlite_path を使用する設計。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、専用の paper_trading DB（デフォルト data/paper_trading.db）に記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグと PID ファイル（data/execution.pid）を用いた安全な起動/停止制御。
    - ExecutionEngine をスレッドで実行し、外部停止要求を受けて安全に停止処理を行う。

- 設定管理
  - config.py: 環境変数 / .env ファイル読み込み・管理を実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）を導入し、CWD に依存しない自動 .env 読み込みを実現。
    - .env, .env.local の読み込み順（OS 環境 > .env.local > .env）と保護（OS 環境変数を上書きしない）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env 行パーサ: export 文、クォートされた値（バックスラッシュエスケープ対応）、インラインコメント対応などをサポート。
    - 各種設定プロパティを提供（DB パス、PID ファイル、kill/stop フラグ、閾値、環境種別検証など）。
    - PAPER_FILL_MODE（paper trading の fill 挙動）や KABUSYS_ENV 値検証を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順の候補選定（signal_rank をタイブレークに使用）。
    - calc_equal_weights, calc_score_weights: 等金額配分とスコア加重配分（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限を適用して候補をフィルタ（"unknown" セクターは上限の対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 各銘柄の発注株数算出（allocation_method="risk_based" / "equal" / "score" をサポート）。
    - 単元株丸め（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ考慮）の実装。
    - aggregate cap によるスケールダウンと残差処理（lot 単位での再配分）を実装。

- 研究（Research）モジュール
  - research/factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比を計算。
    - calc_value: PER/ROE を raw_financials と prices_daily から算出（最新財務レコードの取得ロジックを実装）。
    - DuckDB を利用した SQL ベースの実装。
  - research/feature_exploration.py:
    - calc_forward_returns: 将来リターン（任意ホライズン）を計算。
    - calc_ic: Spearman ランク相関（IC）を実装。充分な有効レコードがない場合は None を返す。
    - rank / factor_summary: ランク付与（同順位は平均ランク）と基本統計量サマリーを提供。
  - research/__init__.py: 必要な関数群をエクスポート（zscore_normalize を kabusys.data.stats から使用）。

- ニュース NLP（OpenAI 連携）
  - ai/news_nlp.py:
    - raw_news から銘柄ごとに記事を集約し、OpenAI API（デフォルトモデル gpt-4o-mini）でセンチメント（-1.0〜1.0）を取得して ai_scores テーブルへ書き込む処理を追加。
    - バッチ処理（最大 20 銘柄／回）、記事数・文字数のトリム、レスポンス検証、スコアの ±1.0 クリップ、エクスポネンシャルバックオフによるリトライ（429/5xx/ネットワーク）などを実装。
    - ニュース取得ウィンドウ（JST 前日 15:00 〜 当日 08:30）を calc_news_window で計算するユーティリティを実装。
    - API キー未設定時に ValueError を送出。
    - （注）ファイル末尾で処理が途中で切れている箇所があり、実装が途中の部分が存在します（後述の Known issues を参照）。

- ユーティリティ
  - utils/process_priority.py:
    - クロスプラットフォームでのプロセス優先度設定ユーティリティを追加（Windows 用優先度定数、POSIX 用 nice 値をマッピング）。
    - set_cpu_affinity で CPU affinity を最初の N コアに固定する機能を追加。権限不足や未サポート環境では警告を出してスキップ。
    - 失敗時の AccessDenied/NotImplemented を安全にハンドリング。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成スクリプトを追加（コマンドライン実行: python -m kabusys.tools.paper_verification_report）。
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ、リスク却下件数。
    - 基準値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義して PASS/FAIL を判定。
    - DB が存在しない場合やテーブル不足（OperationalError）の場合は安全に N/A を返す・処理継続。

- DB 統合
  - SQLite（monitoring / paper_trading）および DuckDB（分析用）を併用する設計を導入。
  - 監視テーブルが存在することを保証するための init_monitoring_db 呼び出しを run スクリプトで行う（冪等）。

Changed
- （初期リリースのため該当なし）

Fixed
- .env パーサの堅牢化:
  - export プレフィックス対応やクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱いを改善。
- calc_score_weights:
  - 全銘柄スコアが 0.0 の場合に等金額配分へフォールバックし、警告を発行する実装を追加。

Known issues / Notes
- ai/news_nlp.py の末尾が途中で切れており、記事取得／DB 書き込みの続き実装がおそらく未完です。実運用前に残りの実装（_fetch_articles の定義や最終書き込み処理）の完成が必要です。
- position_sizing の価格欠損時の挙動:
  - price_map/open_prices に price が欠損（0.0）だとエクスポージャーが過少に見積もられ、セクター上限チェックが甘くなる可能性があります。TODO コメントでフォールバック価格採用の検討を示しています。
- set_process_priority / set_cpu_affinity は OS の権限によって機能しない場合があり、その際は警告を出してスキップします。
- run_monitoring は「Monitoring は本番 sqlite_path を使用する」と明記されています。環境分離が必要な場合は実行前に設定を見直してください。

Security
- 外部 API（OpenAI）利用時に API キーの取り扱いに注意してください。API キーは環境変数（OPENAI_API_KEY）や関数引数で渡す設計です。ログにキーを出力しないでください。

ライセンスや貢献方法についてはプロジェクトルートのドキュメントを参照してください。