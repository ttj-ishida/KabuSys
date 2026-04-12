CHANGELOG
=========

すべての重要な変更は Keep a Changelog（https://keepachangelog.com/ja/）に従って記載しています。

[Unreleased]
------------

- （現在未リリースの変更はありません）

0.1.0 - 2026-04-12
-----------------

Added
- 初回リリース: KabuSys コードベースの主要コンポーネントを追加。
  - 実行・監視
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境変数 KABUSYS_ENV に応じて paper_trading モードを分離し、paper_trading の場合は専用 SQLite（デフォルト: data/paper_trading.db）と MockBrokerClient を利用する仕組みを提供。
    - run_monitoring.py: SystemMonitor のポーリングループを開始する起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用して監視データを一元化する。
    - 起動時にプロセス優先度を "high" に設定するためのユーティリティ呼び出しを組み込み（set_process_priority）。
    - 起動時に監視テーブルを初期化する init_monitoring_db 呼び出しを追加（冪等にテーブル存在を保証）。
  - 環境設定
    - config.Settings クラスを実装。環境変数・.env ファイルから設定を読み取り、型変換・バリデーションを行うプロパティを提供。
    - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。OS 環境変数を保護するための protected 上書き制御や .env.local の優先度対応を実装。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 環境変数・設定項目を多数追加:
      - PAPER_FILL_MODE（paper trading の fill 動作: instant | partial | never | reject）
      - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB パス）
      - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEM/DISK 閾値などの監視関連設定
      - LOG_LEVEL, KABUSYS_ENV（development / paper_trading / live）等
    - 各設定値は妥当性チェック（例: KABUSYS_ENV の許容値、PAPER_FILL_MODE の許容値、LOG_LEVEL の許容値）を行い、不正値は ValueError を送出。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: シグナル選定（score 降順 + tie-breaker）、等重/スコア加重の重み計算。
    - portfolio.position_sizing: allocation_method("risk_based" / "equal" / "score") に基づいた発注株数算出。単元株丸め、1銘柄上限、aggregate cap（利用可能現金とのスケーリング）、cost_buffer（手数料・スリッページ見積り）対応。
    - portfolio.risk_adjustment: セクター集中上限の適用（apply_sector_cap）、市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear のマップ、未知値はフォールバック）。
  - リサーチ（DuckDB 経由のファクター計算）
    - research.factor_research: モメンタム（1/3/6ヶ月、MA200乖離）、ボラティリティ（ATR20、平均売買代金、出来高比）、バリュー（PER, ROE）などの一括計算関数を実装。DuckDB 接続を受け取って SQL ベースで計算。
    - research.feature_exploration: 将来リターン計算（複数ホライズン）、Spearman ランク IC（calc_ic）、ファクター統計サマリ（factor_summary）、rank ユーティリティなどを実装。外部依存なしで統計処理を提供。
  - AI / ニュース
    - ai.news_nlp: raw_news と news_symbols から銘柄ごとのニュースを集約し、OpenAI API（gpt-4o-mini）を用いたセンチメントスコアリング機能を実装。バッチ処理（最大 _BATCH_SIZE=20）、API エラーに対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時に既存スコアを保護する DB 更新戦略（該当コードのみ置換）などのフェイルセーフ設計を採用。
    - calc_news_window ユーティリティを追加（JST の前日 15:00 ～ 当日 08:30 を UTC に変換してウィンドウを生成）。
  - ツール
    - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。期間指定の CLI オプション（--from / --to）と DB パス指定（--db）に対応。稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出し PASS/FAIL 判定を行う。デフォルト閾値を定義（稼働率 99% など）。
  - ユーティリティ
    - utils.process_priority: psutil を用いたクロスプラットフォームのプロセス優先度設定（Windows と POSIX を吸収）と CPU affinity 設定ユーティリティを追加。権限不足等は警告でスキップ。

Changed
- 監視と実行のデータ分離ルール
  - run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番監視 DB）を使用して監視データを記録するように明示（監視データの一元化）。
  - run_execution は paper_trading 環境では settings.paper_sqlite_path を使用し、本番 DB と完全分離する設計（paper_trading のデータは data/paper_trading.db がデフォルト）。
- デフォルト動作・ログ
  - 各起動スクリプトの main() で logging.basicConfig(level=logging.INFO) を呼び出し、デフォルトログレベルを INFO に設定。
- .env の読み込み優先度
  - OS 環境変数 > .env.local > .env の順で読み込み。.env.local は OS 環境変数を上書き可能だが、protected（既存 OS 環境変数）キーは上書きしない振る舞いを確保。

Fixed / Improved
- .env ファイルのパーサを強化
  - コメント行・空行・export KEY=val 形式に対応。
  - シングル/ダブルクォート内のバックスラッシュエスケープ対応や、クォート無し値のインラインコメント判定などを実装。無効な行はスキップし、安全に読み込む。
  - .env の読み込みに失敗した際は warnings.warn を用いてユーザへ通知。
- 設定値バリデーションを追加
  - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等について許容値チェックを実装し、不正な設定は早期に検出して明確なエラーを返す。
- ポジションサイズ計算の堅牢化
  - price 欠損処理・lot_size 単位丸め、aggregate cap によるスケーリングと端数処理（fractional remainder の扱い）を実装。cost_buffer を導入して手数料・スリッページを保守的に見積もる。
- リサーチ計算の欠損制御
  - ファクター計算（MA200・ATR20 等）は十分な窓データがない場合に None を返す仕様を明確化し、NULL 伝播に注意した SQL を構築。
- OpenAI 呼び出しのフェイルセーフ
  - API キー未設定時に明確な ValueError を投げるようにした。API 呼び出しでの 429/タイムアウト/5xx 等は再試行ロジックを通して回復を試み、最終的に失敗しても他銘柄処理へ影響を最小化する設計。

Security
- 環境変数の取り扱い
  - OS 環境変数を保護するため、.env 自動読み込み時に既存の OS 環境変数を上書きしないデフォルト動作、かつ .env.local の上書きでも protected keys を尊重する仕組みを導入。

Notes / Usage
- 監視ループ間隔
  - MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔を秒単位で指定可能。0 以下や非整数は無効と判定され、デフォルト 60 秒にフォールバック（警告ログ出力）。
- Paper Trading の検証
  - paper_verification_report: 使用例
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。
- OpenAI
  - ai.news_nlp.score_news は api_key 引数または環境変数 OPENAI_API_KEY を必要とする。キー未設定時は ValueError。
  - 出力は ai_scores テーブルへ書き込み（部分書き換え戦略により部分失敗時の既存データ保護を意識）。
- 開発者向け
  - 自動 .env 読み込みが邪魔なテスト等の場合、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可能。

Acknowledgments
- 本バージョンはコア機能（実行、監視、ポートフォリオ構築、リサーチ、ニュース NLP、各種ユーティリティ、運用ツール）を実装した初版リリースです。今後のリリースでドキュメント、テスト、エラーハンドリングの強化、インターフェースの安定化を行う予定です。