# Keep a Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。  
リリース日: 2026-04-17

## [0.1.0] - 2026-04-17

### 追加
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、バージョン 0.1.0。
  - __all__ エクスポートを設定（data, strategy, execution, monitoring）。

- 実行/監視用スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。プロセス優先度を設定し、ブローカー／オーダー管理／リスク管理等の依存コンポーネントを組み立ててデーモンスレッドでセッションを実行。
    - Paper Trading（KABUSYS_ENV=paper_trading）時は専用 SQLite（既定: data/paper_trading.db）を使用し、本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）検出で安全に停止可能。
    - PID ファイル出力（data/execution.pid）。
    - RiskManager のデフォルト構成を実装（max_position_pct, max_utilization, rate_limit_per_sec 等）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告後デフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。

- 設定管理
  - config.py
    - Settings クラスを追加し、環境変数から各種設定値を提供（DB パス、API トークン、閾値、環境種別など）。
    - .env/.env.local の自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から検出）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサーを実装（export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープ対応）。
    - 環境変数検証ロジックを追加（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の妥当性チェック）。
    - 各種監視閾値（CPU/MEM/DISK）やファイルパスを Settings 経由で取得可能。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates（スコア降順、タイブレークは signal_rank）。
    - calc_equal_weights（等金額配分）。
    - calc_score_weights（スコア比率配分。全銘柄スコアが 0 の場合は等分配へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap（同一セクター集中度が上限を超える候補を除外。unknown セクターは除外対象外）。
    - calc_regime_multiplier（market regime に応じた資金乗数を返す。未知レジームは警告して 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes（allocation_method: risk_based / equal / score をサポート）。
    - lot_size 単位で丸め、max_position_pct や max_utilization、cost_buffer を考慮したスケーリングロジックを実装。
    - 投資合計が available_cash を超えた場合のスケールダウンと端数処理（再現性を保つため順序安定化を実装）。

- リサーチ／ファクター計算
  - research/factor_research.py
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）。
    - calc_volatility（ATR20、ATR 比率、20日平均売買代金、出来高比）。
    - calc_value（PER, ROE）。
    - DuckDB 接続を受け prices_daily / raw_financials を利用する実装。
  - research/feature_exploration.py
    - calc_forward_returns（複数ホライズンの将来リターンを一括取得）。
    - calc_ic（Spearman のランク相関（IC）計算。データ不足時は None を返す）。
    - rank / factor_summary（ランク化・統計サマリーを提供）。
  - research/__init__.py に主要 API をエクスポート。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news を元に OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し ai_scores テーブルへ保存する処理を実装（バッチ送信、レスポンス検証、スコアクリップ、書き込みは対象コードのみ置換処理）。
    - バッチサイズ、記事数上限、1銘柄あたり文字数上限、リトライ（429/ネットワーク/5xx 用の指数バックオフ）等の堅牢化を実装。
    - タイムウィンドウ計算（JST 基準で前日 15:00 ～ 当日 08:30 を UTC に変換）を提供。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差を吸収したプロセス優先度設定（Windows と POSIX の差分を吸収）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。権限不足や未対応環境では警告ログでスキップ。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。DB（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を表示。
    - P95 計算、日時フィルタ、閾値（稼働率 99%、成功率 90% 等）を実装。

- DuckDB 統合
  - duckdb を利用して時系列・ファクター計算を行う設計を導入（各種モジュールで DuckDB 接続を引数に受ける）。

### 変更（設計上の主要点）
- Paper trading と production の DB を明確に分離
  - settings.paper_sqlite_path を導入し、KABUSYS_ENV=paper_trading 時は専用 DB を使用するよう変更。
  - 監視（run_monitoring）は意図的に環境にかかわらず本番 sqlite_path を使用する設計。

- .env の自動ロードのルール
  - OS 環境変数を保護するため .env は override=False、.env.local は override=True で読み込む（ただし既存の OS 環境変数は保護）。
  - プロジェクトルートが検出できない場合は自動読み込みをスキップ。

- ログ／フォールバック方針
  - 非致命的な問題（優先度設定失敗、ENV パースの不正など）は例外を投げずにログ警告でフォールバックする方針に統一。
  - 一部の関数（ex. calc_score_weights、calc_regime_multiplier）でフォールバックのログ出力を追加。

### 修正（バグ修正・堅牢化）
- .env パーサーの堅牢化
  - クォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、export プレフィックス対応を実装。
  - 無効行の無視や key の存在チェックを厳密化。

- run_monitoring のポーリング間隔取得
  - MONITOR_POLL_INTERVAL の値検証を追加。0 以下や非整数は警告してデフォルト（60 秒）にフォールバック。

- position_sizing のスケーリング・丸めロジック
  - cost_buffer を考慮したスケールダウン処理を導入。残余キャッシュを使った lot_size 単位の追加配分アルゴリズムを実装し再現性を確保。

- research / feature_exploration の入力検証
  - calc_forward_returns の horizons 引数検証（正の整数かつ 252 以下）を追加。

- ai/news_nlp の堅牢化
  - OpenAI API キー未設定時に ValueError を出す明示的なチェックを追加。
  - バッチ処理・リトライ・レスポンスバリデーションを実装し部分失敗に対する保護を強化。

- utils/process_priority の例外処理追加
  - psutil の権限エラーや未実装例外を捕捉し、スキップして警告ログを出力するよう変更。

### ドキュメント / コメント
- 各モジュールに設計ノートや参照ドキュメント位置（PortfolioConstruction.md, StrategyModel.md 等）をコメントとして追加し、実装意図と注意点を明記。
- 各関数に日本語ドクストリングを整備し、引数・戻り値・フォールバック動作を明確化。

### 既知の制約・TODO
- position_sizing: lot_size を銘柄別に持つ拡張（stocks マスタへの lot_size 持ち回し）は TODO。
- sector_exposure 計算で price が欠損（0.0）だと過少見積りされる問題があり、将来的にフォールバック価格（前日終値や取得原価）を導入予定。
- ai/news_nlp の処理は部分失敗時に一部銘柄のスコア更新をスキップする設計だが、完全なトランザクション保証は未実装（部分置換戦略により現状の保護を実現している）。

---

上記はコードベースの現状から推測してまとめた CHANGELOG です。必要に応じて項目の追加・日付調整・詳細化を行います。