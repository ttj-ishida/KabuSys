CHANGELOG
=========

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。
リリース日: 2026-04-17

[0.1.0] - 2026-04-17
--------------------

Added
- 初回リリース。パッケージ基盤・主要機能群を追加。
- 起動スクリプト:
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止は data/stop_requested.flag によるフラグ検知で行う。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は実行環境にかかわらず本番用 sqlite_path を使用する設計。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（デフォルト data/paper_trading.db）へ記録し、本番 DB と分離して運用可能。
    - BrokerClientFactory により（環境に応じて）ブローカークライアントを組み立てる想定。
    - エンジンはデーモンスレッドで実行し、停止フラグで安全に停止する。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイルを管理。

- 設定 / 環境変数管理:
  - src/kabusys/config.py
    - .env/.env.local の自動ロード機能を追加（プロジェクトルートは .git または pyproject.toml で探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パーサは export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメント処理を実装。
    - 環境変数の保護（既存 OS 環境変数を上書きしない）をサポート。
    - Settings クラスを導入し、J-Quants / kabuAPI / LINE / DB / 監視閾値 / システム設定等のプロパティを提供。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。

- ポートフォリオ構築関連（純粋関数群）:
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナルの候補選定 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights を追加。
    - スコア全0 の場合は等配分にフォールバック（警告ログ）。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター上限適用 apply_sector_cap を追加（sell_codes を考慮、"unknown" セクターは制限を適用しない）。
    - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear）を追加。未知レジームは警告のうえ 1.0 にフォールバック。
  - src/kabusys/portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を追加。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）で丸め、per-stock 上限・aggregate cap（利用可能現金）に基づくスケーリング、cost_buffer を考慮した保守的見積り、残余キャッシュによる端数分配を実装。

- 実行ユーティリティ:
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定 set_process_priority と CPU affinity 設定 set_cpu_affinity を追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）に対応。権限不足や未対応 OS でのフォールバック処理あり。

- 研究（Research）モジュール:
  - src/kabusys/research/factor_research.py
    - DuckDB を用いたファクター計算: calc_momentum（モメンタム / MA200乖離）、calc_volatility（ATR/出来高/売買代金指標）、calc_value（PER/ROE）を追加。
    - 大量データを効率的に処理するため SQL ウィンドウ関数を活用。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン calc_forward_returns、IC（calc_ic）、統計サマリ（factor_summary）およびランク関数 rank を追加。
    - 外部ライブラリ非依存（標準ライブラリのみ）で実装。
  - src/kabusys/research/__init__.py
    - 主要関数をエクスポート（zscore_normalize は kabusys.data.stats から参照）。

- AI / ニュース NLP:
  - src/kabusys/ai/news_nlp.py（実装中）
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し、銘柄別スコアを ai_scores に書き込むフローを実装。
    - バッチ処理（最大 _BATCH_SIZE=20）、記事トリム、リトライ（429/ネットワーク/5xx）と指数バックオフ、レスポンスの厳密な JSON バリデーション、スコア ±1.0 でクリップ、部分失敗時の DB 保護（該当コードのみ置換）などを設計。
    - calc_news_window（JST → UTC のウィンドウ計算）を提供。
    - score_news により API キー解決やバリデーションを行う（実装は途中で切れている箇所あり）。

- ツール:
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - システム稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）などを集計し、基準値を用いた PASS/FAIL 判定を出力。
    - CLI 引数 --from / --to / --db をサポートし、DB が存在しない場合の親切なエラーメッセージを出力。

- パッケージ情報:
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
- 初回リリースのため「変更」はなし（新規追加が主体）。

Fixed
- 初回リリースのため「修正」はなし。

Security
- OpenAI API キーを引数または環境変数 OPENAI_API_KEY で明示的に解決する実装。未設定時は明示的にエラーを投げる（score_news）。

Deprecated
- なし。

Removed
- なし。

Notes / Known limitations
- ai/news_nlp.py は途中でファイル末尾が欠損している箇所があり（記事取得の続きが切れている）、実働化には追加実装やテストが必要です。
- calc_position_sizes の将来的な拡張点として、銘柄別の lot_size をサポートするための設計コメントが残っています（現状は共通 lot_size を想定）。
- apply_sector_cap 内の価格欠損時の挙動（price が 0.0 の場合にエクスポージャーが過小見積りされる可能性）について TODO が記載されており、将来的にフォールバック価格の導入が想定されています。
- DuckDB を前提とした SQL 実装のため、prices_daily / raw_financials 等のテーブル定義・データ整備が必要です。
- run_monitoring/run_execution はプロセス優先度設定やファイルベースの停止フラグ等を用いるため、実運用環境では権限や filesystem パスの整合性を事前に確認してください。

ライセンス
- 本リポジトリのライセンス情報はリポジトリルートのライセンスファイルを参照してください（本 CHANGELOG には含まれていません）。

以上。