CHANGELOG
=========

すべての注目すべき変更をここに記載します。  
フォーマットは Keep a Changelog に準拠しています。

注: このリポジトリの現在のパッケージバージョンは src/kabusys/__init__.py の __version__ に合わせて 0.1.0 としています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-31
-------------------

Added
- 基本パッケージ構成
  - パッケージルートと公開 API を定義（kabusys.__init__）。
  - バージョン情報を 0.1.0 に設定。

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
  - 高度な .env パーサ実装:
    - export KEY=val 形式、シングル／ダブルクォート、バックスラッシュによるエスケープ、行末コメントの扱いに対応。
  - Settings クラスを提供し、アプリケーションで必要な設定値をプロパティ経由で取得可能。
    - 必須キー検証（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
    - デフォルト値の提供（例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）
    - is_live / is_paper / is_dev ユーティリティプロパティ

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し銘柄ごとのセンチメントを OpenAI（gpt-4o-mini）で評価して ai_scores テーブルへ書き込む。
    - 処理特徴:
      - JST のタイムウィンドウ（前日 15:00 ～ 当日 08:30）を UTC に変換して使用（calc_news_window）。
      - 1 銘柄当たり最大記事数／文字数でトリム（バッチ肥大化対策）。
      - 最大 20 銘柄単位でバッチ送信（_BATCH_SIZE）。
      - 429／ネットワーク断／タイムアウト／5xx を対象に指数バックオフでリトライ。
      - レスポンスの強固なバリデーションと JSON 復元ロジック（前後の余計なテキストを除去）。
      - スコアは ±1.0 にクリップ。
      - DuckDB 互換性考慮: executemany に空リストを渡さない等の対策。
      - フェイルセーフ: API の失敗はスキップして他銘柄の処理は継続。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）を行い market_regime テーブルへ冪等的に書き込む。
    - 特徴:
      - prices_daily と raw_news を参照して MA とニュースを取得。
      - マクロニュースはキーワードフィルタリングして上限件数を LLM に送信。
      - OpenAI API 呼び出しに対するリトライ・エラーハンドリング（フェイルセーフでは macro_sentiment=0.0 を使用）。
      - レジーム合成ロジックと閾値（BULL/BEAR）を実装。
      - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT、例外時は ROLLBACK を試行。

- Data / ETL / カレンダー (kabusys.data)
  - calendar_management
    - JPX カレンダー（market_calendar）を扱うユーティリティを実装。
    - 営業日判定 API（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）を提供。
    - DB データがまばらな場合は曜日ベースでフォールバックする設計。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等保存。バックフィル、健全性チェックを実装。
  - pipeline / ETL
    - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を kabusys.data.etl で再エクスポート）。
    - ETL の差分取得、保存、品質チェックのための骨格を実装。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得等。
    - 設計上の注記: backfill を含めた差分ロジック、品質問題は収集して呼び出し元に委ねる方針。

- Research（kabusys.research）
  - factor_research
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、出来高指標）、Value（PER, ROE）等のファクター計算を実装。
    - DuckDB 上で SQL を用いた計算を行い (date, code) キーの辞書リストを返す設計。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。
  - re-export: 主要関数をパッケージレベルで公開。

- 共通設計方針・堅牢性対策
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を直接参照しない設計（全ての関数は引数の target_date を使用）。
  - OpenAI 呼び出しは JSON Mode を利用し厳密な JSON 出力を期待、パース失敗時は安全にフォールバック。
  - API 失敗時のフェイルセーフ（LLM失敗で 0.0 を用いる、部分失敗で他データを保護する等）。
  - DuckDB の特性（executemany の空リスト禁止等）を明示的に考慮した実装。
  - トランザクション制御と ROLLBACK 試行（DB 書き込みの冪等性を重視）。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Security
- OpenAI API キーは明示的に必要（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出する箇所が複数あり。
- 必須の外部トークンやパスワード（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）は Settings で必須検証を行う。

Notes / Developer hints
- 主要な必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OPENAI_API_KEY は AI 機能を使うために必要（関数呼び出し時に引数で注入可能）。
  - KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
- DuckDB との相互作用において executemany に空リストを渡すと問題となるため、実装は空チェックを行っている。
- OpenAI の呼び出し部分はテスト容易性を考慮して _call_openai_api を実装し、テスト時にはパッチ可能。

既知の制限 / TODO（将来の改善候補）
- PBR・配当利回り等の一部バリュー指標は未実装（calc_value 参照）。
- news_nlp のバッチサイズやモデル選択は定数化されており、運用時にチューニング可能。
- jquants_client（外部APIクライアント）の具体実装はこの差分のコードに依存しているため、本 CHANGELOG では抽象的に扱う。

-------------
この CHANGELOG はコードベースを読み解いて推測して作成したものです。実際の変更履歴やリリースノートの要件に応じて適宜修正してください。