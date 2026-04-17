# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
タグ付けのあるリリースはパッケージ内の __version__ に合わせてあります。

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 基本リリース: KabuSys 自動売買フレームワークの初期実装を追加。
  - パッケージメタ情報: src/kabusys/__init__.py にバージョン 0.1.0 を定義。

- 実行／監視用エントリポイントを追加:
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。設定に応じて paper_trading 用の MockBrokerClient を使用可能。
    - paper_trading 環境では専用 SQLite DB (デフォルト: data/paper_trading.db) を利用し、本番 DB と分離。
    - エンジン用 PID ファイル管理、停止フラグ (data/stop_requested.flag) の検出と安全なシャットダウンに対応。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番の sqlite_path を使用して初期化。

- 設定管理モジュールを追加:
  - config.py
    - .env 自動読み込み（.env → .env.local、OS 環境変数優先）を提供。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）に対応。
    - 複雑な .env 解析機能を実装（export プレフィックス対応、引用符内エスケープ、インラインコメント処理、protected オーバーライド）。
    - Settings クラスを追加し、各種環境変数（J-Quants / kabu API / LINE / DB / 監視 / システム設定等）をプロパティで取得可能。
    - Paper Trading 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等）をサポート。
    - 環境値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を行い不正値は例外で通知。

- ポートフォリオ構築関連の純関数群を追加:
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - portfolio/risk_adjustment.py
    - セクター集中除外ロジック (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。
  - portfolio/position_sizing.py
    - position sizing（risk_based, equal, score）ロジックを実装。単元株丸め、per-stock 上限、aggregate cap、cost_buffer を考慮したスケーリングを実装。
  - portfolio/__init__.py で上記 API を公開。

- 研究（Research）モジュールを追加:
  - research/factor_research.py
    - Momentum, Volatility, Value のファクター計算を DuckDB 上で実行する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 計算は prices_daily / raw_financials テーブルのみ参照し、データ不足時は None を返す設計。
  - research/feature_exploration.py
    - 将来リターン計算 (calc_forward_returns)、IC（Spearman ランク相関）計算 (calc_ic)、統計サマリー (factor_summary)、rank ユーティリティを実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - research/__init__.py で主要関数を公開。

- AI ニュース NLP スコアリングを追加:
  - ai/news_nlp.py
    - raw_news / news_symbols / ai_scores を用いたニュースの銘柄別センチメントスコア生成ロジックを実装。
    - OpenAI API（デフォルトモデル: gpt-4o-mini）を用いたバッチ処理（1回あたり最大銘柄数 20）をサポート。
    - スコアは ±1.0 にクリップして ai_scores テーブルに書き戻す。API リトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
    - ニュース収集ウィンドウ計算ユーティリティ (calc_news_window) を提供。
    - （実装の一部はファイル末尾で途中まで記述。設計上のフェイルセーフやバリデーション方針を明記）

- 監視・検証ツールを追加:
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポートを生成する CLI ツールを追加（期間指定オプションあり）。
    - system_status / trade_logs / risk_logs を参照し、稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出して PASS/FAIL 判定を出力。
    - P95 計算、各種 None/データ欠損時のフォールバック処理を実装。

- ユーティリティを追加:
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収し、プロセス優先度設定 (set_process_priority) と CPU affinity 固定 (set_cpu_affinity) を提供。
    - 権限不足や未対応 OS での安全なスキップ処理を実装。

### 変更 (Changed)
- DB 初期化に関する方針:
  - run_execution と run_monitoring で monitoring テーブル群の初期化（init_monitoring_db）を呼び出し、監視テーブルが存在することを冪等的に保証するようにした。

- 環境変数の自動ロード挙動:
  - 自動ロードのデフォルトは有効。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env の読み込み順を OS 環境変数 > .env.local > .env と定義し、OS 環境変数は protected として上書きされない。

### 修正 (Fixed)
- 環境変数パースの堅牢化:
  - .env ファイル解析で export プレフィックス、引用符内のエスケープシーケンス、インラインコメントの取り扱いを改善。無効行は無視。

- ポートフォリオ / ポジション算出の安全弁:
  - position_sizing の aggregate cap スケーリングにおいて、単元株（lot_size）単位での再配分ロジックを追加し、残余キャッシュを考慮した安定的な丸めを実装。

- 監視ループの頑健性:
  - MONITOR_POLL_INTERVAL の不正値（非整数や 0 以下）に対して警告を出しデフォルトにフォールバックする処理を追加。

### 既知の制約 / 注意点 (Known issues / Notes)
- ai/news_nlp.py の処理は大枠が実装されているが、ファイル末尾で処理の一部（記事集約フェーズ以降）が途中で切れているため、実運用前に最終部分（API 呼出しループ、DB 書き込み処理）の完成と十分なテストが必要です。
- position_sizing の注記にある通り、価格データが欠損（0.0）の場合にエクスポージャーの過少見積りや配分ミスが起きる可能性があるため、将来的にフォールバック価格（前日終値等）を導入することを推奨。
- calc_regime_multiplier では未知のレジームに対して 1.0 でフォールバックする挙動を採用しており、想定外のレジームラベルが入るとログに警告が出力されます。

### セキュリティ (Security)
- 現時点でセキュリティに関する修正はありません。

---

（今後のリリースでは ai/news_nlp.py の完全実装、より詳細なテスト、ドキュメンテーションの追加を予定しています。）