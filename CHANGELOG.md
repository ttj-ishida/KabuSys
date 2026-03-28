# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装・公開しました。
主にデータ収集・ETL、マーケットカレンダー管理、ファクター計算、ニュースNLP／レジーム判定（OpenAI 統合）、
および環境設定ユーティリティを含みます。

### Added
- パッケージのエントリポイント
  - src/kabusys/__init__.py にてバージョン `0.1.0` と公開 API を定義。

- 環境設定・.env ローダー
  - src/kabusys/config.py
    - プロジェクトルート検出: .git または pyproject.toml を起点に自動検出（CWD 非依存）。
    - .env ファイルパーサ: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
    - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト向け）。
    - Settings クラスを提供（settings インスタンス）
      - J-Quants / kabu API / Slack / DB パス（DuckDB/SQLite） / システム設定（KABUSYS_ENV, LOG_LEVEL）などのプロパティを公開。
      - env 値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
      - is_live / is_paper / is_dev のヘルパー。

- AI（ニュースNLP・レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を元に記事を銘柄別に集約し、OpenAI（gpt-4o-mini）の JSON mode を使って銘柄ごとのセンチメント（-1.0〜1.0）を取得。
    - バッチ処理（デフォルト最大 20 銘柄/コール）、記事数/文字数上限、レスポンス検証、スコアクリッピング、部分的な書き込み（失敗時に他銘柄スコアを保護）を実装。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ。失敗時は安全にスキップして継続。
    - ルックアヘッドバイアス対策: datetime.today()/date.today() を参照せず、target_date ベースで UTC 時間ウィンドウを計算（calc_news_window）。
    - テスト容易性: OpenAI 呼び出し関数はモジュール内で分離されており差し替え可能（unittest.mock.patch を想定）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成し、日次の市場レジーム（bull / neutral / bear）を判定、market_regime テーブルへ冪等書き込み。
    - マクロニュースのフィルタ（キーワードリスト）と OpenAI（gpt-4o-mini）呼び出し。API 障害時は macro_sentiment=0.0 としてフォールバック。
    - API リトライ・バックオフ、JSON レスポンスパースの耐性、ロギングを実装。
    - レジーム合成フローの具体的な定数（重み・閾値）を定義。

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。DuckDB のウィンドウ関数を使用。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率などのボラティリティ・流動性指標を計算。
    - calc_value: raw_financials から最新財務データを取得し PER（EPS が 0/欠損時は None）、ROE を計算。
    - すべての関数は prices_daily / raw_financials を参照し、発注 API 等にはアクセスしない設計。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定基準日から様々なホライズン（例: 1,5,21 営業日）先のリターンを計算。ホライズンは検証済みの整数制約あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（結合・欠損除外・最小有効レコード数チェック）。
    - rank: 平均ランクによる同順位処理（丸めで ties 対応）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - pandas 等外部依存を避け、標準ライブラリ＋DuckDB で実装。

- データプラットフォーム（Data）モジュール
  - src/kabusys/data/calendar_management.py
    - market_calendar に基づく営業日判定（is_trading_day）、次/前営業日取得（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）、SQ 日判定（is_sq_day）。
    - DB が空または未取得日の場合の曜日ベースのフォールバック（週末除外）や健全性チェック、最大探索日数制限で無限ループ回避。
    - calendar_update_job: J-Quants クライアント（jquants_client.fetch_market_calendar/save_market_calendar）を使った夜間バッチ更新、バックフィル、健全性チェック、冪等保存。外部 API エラー時のロギングと安全な挙動。
  - src/kabusys/data/pipeline.py
    - ETL パイプライン向けユーティリティと設計（差分取得、保存、品質チェックの枠組み）。
    - ETLResult データクラス（ETL 実行結果の集約、品質問題・エラーの可視化、to_dict）。
    - DuckDB 上でのテーブル存在チェックや最大日付取得ユーティリティ。
    - バックフィル / カレンダー先読み等の定数を定義。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult の再エクスポート（公開インターフェース）。
  - src/kabusys/data/__init__.py
    - パッケージモジュール（空の初期化だが存在）。

- テスト・運用を想定した設計上の配慮
  - OpenAI 呼び出しや自動 .env ロードはテストで差し替え・無効化可能（関数分離／環境フラグ）。
  - DuckDB のバージョン特有の挙動（例: executemany に空配列を渡せない）を考慮した実装。
  - ルックアヘッドバイアス対策（date.today() 参照禁止、target_date に基づくウィンドウ設計）。
  - ロギングと WARN/INFO/DEBUG の活用により障害時のトラブルシュートを容易化。

### Notes（運用・移行メモ）
- 必須環境変数（Settings により取得される）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（API 呼び出し時）
- DuckDB 側の想定スキーマ（存在を前提とするテーブル）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar, etc.
- OpenAI API のレスポンス形式は JSON mode を前提に設計しているが、不正な文字列や余計な前後テキストが混ざるケースも考慮した堅牢化処理を実装。
- jquants_client は外部モジュール（kabusys.data.jquants_client）として参照しており、API 呼び出し・保存ロジックはその実装に依存します（このリリースでは参照ポイントを提供）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初期実装ではトークンやパスワード等を環境変数から取得する設計。秘密情報は .env/.env.local または OS 環境変数で管理してください。ソースコードに直接埋め込まないでください。

---

今後の変更履歴は本ファイルに逐次記載します。必要に応じて各モジュールの API 変更や DB スキーマ変更を明確に記載してください。