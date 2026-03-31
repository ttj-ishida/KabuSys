# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このファイルはリポジトリの現行コードベースから機能実装内容を推測して作成した初期の変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-31

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0"、公開モジュール指定）。
- 環境変数 / 設定管理モジュール (kabusys.config)
  - .env ファイルおよびOS環境変数の自動読み込み機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD に依存しない）。
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサを実装（コメント・export 形式・クォート・エスケープ対応、インラインコメント処理）。
  - Settings クラスを提供し、以下の設定プロパティを取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (デフォルト: data/kabusys.duckdb), SQLITE_PATH (デフォルト: data/monitoring.db)
    - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL の検証
    - is_live / is_paper / is_dev ヘルパー
  - 必須環境変数未設定時に ValueError を送出する _require 実装。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - DuckDB の raw_news / news_symbols を読み込み、銘柄ごとにニュースを集約して OpenAI (gpt-4o-mini) にバッチ送信しセンチメントを算出。
    - バッチサイズ・トークン肥大化対策（_BATCH_SIZE=20、1銘柄あたり最大記事数・文字数制限）を実装。
    - JSON Mode を想定したレスポンス検証と復元処理（前後余計テキストの復元）。
    - 429・ネットワークエラー・タイムアウト・5xx に対する指数バックオフによるリトライ。
    - スコアは ±1.0 にクリップ。失敗時はフェイルセーフでスキップ（例外を伝播しない）。
    - calc_news_window により JST のニュース収集ウィンドウを明確化（前日15:00〜当日08:30 JST を UTC に変換）。
    - score_news(conn, target_date, api_key=None) を公開。APIキー未指定時は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError を送出。
    - DB への書き込みは冪等的（DELETE → INSERT）で部分失敗時の既存データ保護を考慮。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュース（LLM）センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news をフィルタし、OpenAI（gpt-4o-mini）により macro_sentiment を JSON で取得。
    - API 呼び出しの再試行（429/接続エラー/タイムアウト/5xx）とフェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - レジームスコア合成ロジック・閾値定義・冪等的 DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - score_regime(conn, target_date, api_key=None) を公開。APIキー未指定時は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError を送出。
    - ルックアヘッドバイアス対策を考慮した設計（target_date 未満のデータのみ使用、datetime.today() を参照しない）。

- Data / ETL / カレンダー・管理 (kabusys.data)
  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult データクラスを追加（取得件数、保存件数、品質チェック結果、エラー等を保持）。
    - 差分取得とバックフィル方針、品質チェックの概念を実装方針として定義。
    - DuckDB の最大日付取得やテーブル存在チェック等のユーティリティ。
  - ETL 公開インターフェース (kabusys.data.etl)
    - pipeline.ETLResult を再エクスポート。
  - 市場カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを用いた営業日判定ユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録値を優先しつつ未登録日は曜日ベースでフォールバックする一貫したロジック。
    - JPX カレンダーを J-Quants API から差分取得して更新する calendar_update_job の実装（バックフィル、健全性チェック、ON CONFLICT 型の冪等保存想定）。
    - 最大探索範囲を設定して無限ループを防止。
    - jquants_client を通じたフェッチ/保存処理の呼び出し箇所を確保。

- Research モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離の計算（prices_daily を SQL で取得）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率の計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を算出（prices_daily と組合せ）。
    - 全結果は (date, code) をキーとする dict のリストで返却。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を使用）を一括取得。
    - calc_ic: スピアマンのランク相関（IC）を実装。データ不足時は None を返す。
    - rank: 同順位は平均ランクを返すランキング実装（丸めで ties を安定化）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算する統計サマリー。

- パッケージのエクスポート調整
  - research/__init__.py で主要な関数を再エクスポートして使いやすく整備。
  - ai/__init__.py で score_news を公開。

### Changed
- 初版につき該当なし。

### Fixed
- 初版につき該当なし。

### Security
- 初版につき該当なし。

### Notes / Migration
- OpenAI API の利用
  - news_nlp.score_news および regime_detector.score_regime は OpenAI API キーが必要（引数で渡すか環境変数 OPENAI_API_KEY を設定）。未設定時は ValueError を送出します。
  - API とのやり取りは gpt-4o-mini 想定の JSON Mode を使用。API レスポンスのパースが失敗するケースを想定してフェイルセーフ処理を行っています。
- 環境変数
  - 実行に必要な環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）を .env または環境に設定してください。Settings は必須キー未設定時に明確なエラーを出します。
  - 自動 .env ロードはプロジェクトルート検出に依存するため、配布後は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用するか環境変数を直接設定してください。
- デフォルト DB パス
  - DuckDB のデフォルトパスは data/kabusys.duckdb、SQLite のデフォルトは data/monitoring.db。
- ルックアヘッドバイアス対策
  - AI モジュール・Research モジュール共に内部で datetime.today()/date.today() を直接参照せず、関数引数の target_date に対して deterministic に動作する設計です。

もしリリースノートに追記してほしい項目（例: 実際のコミット情報、担当者、リリース方法、既知のバグリスト）があれば知らせてください。追加で反映します。