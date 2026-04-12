CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
安定性と可読性のため、主要な追加・変更点を日本語でまとめています。

Unreleased
----------

- （なし）

0.1.0 — 2026-04-12
------------------

Added
- 基本機能の初期実装を追加（初回リリース）。
  - パッケージメイン情報
    - kabusys.__version__ = "0.1.0"
  - 実行エントリスクリプト
    - run_execution.py: 実運用 / paper_trading モード対応の ExecutionEngine 起動スクリプトを追加。Paper Trading 時は専用 SQLite（data/paper_trading.db デフォルト）を使用し MockBrokerClient を利用可能にする。
    - run_monitoring.py: SystemMonitor をポーリングで回す監視プロセス起動スクリプトを追加。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する点を明記。
  - 設定管理
    - config.Settings: 環境変数 / .env 自動ロード機能（.env, .env.local の読み込み順、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）と多くの設定プロパティを実装（DB パス、PID / kill flag、しきい値、環境種別判定など）。値検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）を実装。
    - .env パーサの実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理を含む堅牢なパーサを提供。
  - 実行制御ユーティリティ
    - utils.process_priority: Windows / POSIX の差異を吸収するプロセス優先度設定（high/normal/low）を追加。CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。アクセス権限や未対応 OS の場合は警告を出して安全にスキップ。
  - ポートフォリオ構築
    - portfolio.portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全ゼロ時のフォールバック警告あり。
    - portfolio.risk_adjustment: セクター上限適用（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。未知レジームのフォールバック挙動を明記。
    - portfolio.position_sizing: 各銘柄の発注株数決定ロジックを実装（risk_based / equal / score）。単元株丸め、per-position 上限、aggregate cap（available_cash によりスケーリング）、cost_buffer を用いた保守的評価、残差を用いた追加配分ロジックを備える。
  - リサーチ / ファクター計算
    - research.factor_research: momentum / volatility / value ファクターを DuckDB 経由で計算する関数を実装（MA200、ATR20、各モメンタム等）。データ不足時の None 考慮、ウィンドウ幅の説明あり。
    - research.feature_exploration: 将来リターン計算（複数ホライズン）、IC（Spearman ρ）計算、ランク変換、ファクター統計サマリーを実装。外部ライブラリに依存しない実装。
    - research.__init__: zscore_normalize のエクスポートを含む主要 API を公開。
  - AI ニュース NLP
    - ai.news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を実装。主な設計/実装事項:
      - ニュース時間ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）計算
      - 1 銘柄あたり記事数・文字数上限、最大バッチサイズ（20）、スコアクリップ（±1.0）
      - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフでのリトライ
      - レスポンスバリデーションと部分失敗に対する既存スコア保護のための部分削除→挿入の安全な DB 更新戦略
      - OPENAI_API_KEY 未設定時は ValueError を送出
  - ツール
    - tools.paper_verification_report: paper trading 用の検証レポート生成 CLI を追加。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL を表示する。デフォルト DB は data/paper_trading.db。閾値はソース内で定義（稼働率 99.0%、成功率 90% など）。
  - DB / クエリ
    - DuckDB と SQLite の両方を用いる設計を導入。duckdb_path / sqlite_path の設定プロパティと接続箇所を追加。

Changed
- N/A（初回リリースのため変更履歴なし）。

Fixed
- .env ファイル読み込み時の堅牢性向上:
  - クォート内のバックスラッシュエスケープを正しく処理するよう改善。
  - インラインコメントの判定ロジックを強化（クォート有無で挙動を分離）。
- run_monitoring のポーリング間隔取得で不正値（0 や負数、非整数）を安全に扱い、デフォルトへフォールバックして警告を出す処理を追加。

Security
- ai.news_nlp: OpenAI API キーの未設定を検出して明示的にエラーを返すようにし、誤動作で無保証の API 呼び出しを行わないようにした。

Notes / Implementation details
- Paper Trading 分離:
  - paper_trading 環境では SQLite を分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）しているため、本番データに影響を与えずに検証が可能。
- モニタリング:
  - run_monitoring は監視 DB と duckdb に接続して SystemMonitor を周期実行する想定。監視が常に本番 sqlite_path を使用する旨を明記（開発環境でも監視 DB は本番相当の path を参照する）。
- ロギング:
  - 起動スクリプトは基本的に logging.basicConfig(level=logging.INFO) を使用。Settings.log_level を活かす箇所は今後の改善対象。
- 設計方針:
  - 多くのモジュールは「DB 参照を明示」または「純粋関数でメモリ内計算のみ」といった責務分離を意識して実装されている（例: portfolio モジュールは DB を参照しない純粋関数群、research モジュールは DuckDB 接続を受ける）。

今後の改善案（例）
- Settings の log_level を起動時に適用する（現在は basicConfig に固定）。
- news_nlp のより細かいエラーレポーティング・メトリクス収集。
- position_sizing の lot_size を銘柄別に拡張する（stocks マスタの導入）。
- duckdb の接続プール化やクエリ最適化によるパフォーマンス改善。

ライセンスや貢献ガイドライン等は別途記載してください。