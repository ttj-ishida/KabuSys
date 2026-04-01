Keep a Changelog
=================

全ての重要な変更はこのファイルで追跡します。
フォーマットは Keep a Changelog に準拠します。

0.1.0 - 2026-04-01
------------------

Added
- パッケージの初期リリースを追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py にて定義）

- 環境設定管理 (kabusys.config)
  - .env/.env.local ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルートは .git または pyproject.toml を基準に特定（CWD に依存しない実装）。
  - .env パーサ実装:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント対応。
    - override / protected キー指定で OS 環境変数保護対応。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / システム設定等をプロパティ経由で取得。
    - 必須環境変数未設定時のエラーチェック（_require）。
    - KABUSYS_ENV と LOG_LEVEL の検証（有効値チェック）を実装。
    - デフォルトパス（duckdb, sqlite, pid）とデフォルト閾値を提供。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI（gpt-4o-mini）でセンチメントを評価。
    - チャンク処理（最大 _BATCH_SIZE=20 銘柄）・1 銘柄あたり記事数/文字数のトリム制御（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - OpenAI 呼び出しは JSON Mode を利用し、429/ネットワーク断/タイムアウト/5xx は指数バックオフでリトライ。
    - レスポンス検証ロジックを実装（JSON 抽出、"results" 構造検証、コード照合、数値検証、スコアの ±1.0 クリップ）。
    - 成功分のみ ai_scores テーブルへ冪等的に DELETE → INSERT（部分失敗時に他コードの既存データを保護）。
    - テスト容易性のため _call_openai_api を差し替え可能。
    - calc_news_window によるニュース収集ウィンドウ計算（JST 基準で前日15:00〜当日08:30 を UTC naive に変換）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily からの MA 計算、raw_news からのマクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を算出。
    - API エラーやパース失敗はフェイルセーフとして macro_sentiment=0.0 にフォールバック。
    - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

- Data モジュール (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダー（market_calendar）を扱うユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - 夜間バッチ calendar_update_job を実装し、J-Quants API から差分取得→保存（バックフィル・健全性チェックあり）。
  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラス（target_date, fetch/save カウント, quality_issues, errors 等）を実装して公開。
    - 差分取得 / 保存 / 品質チェックの方針をコードに反映（差分バックフィル、冪等保存、品質問題は収集して継続）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得等を実装。
  - jquants_client と quality との連携を想定した設計（実装はそれらのモジュールに依存）。

- Research モジュール (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比）、バリュー（PER, ROE）を DuckDB クエリで計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 計算は prices_daily / raw_financials のみ参照。データ不足時は None を返す等の堅牢性を確保。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns, 複数ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算（calc_ic）とランク化ユーティリティ（rank）。
    - ファクター統計サマリー（factor_summary）。
  - 研究用ユーティリティは外部ライブラリに依存せず標準ライブラリと DuckDB の SQL で実装。

- パッケージ公開/エクスポート
  - 各サブパッケージで主要関数を __all__ にてエクスポート（例: kabusys.ai.score_news / score_regime、kabusys.research.* 等）。
  - kabusys.data.etl で ETLResult を再エクスポート。

Changed
- 初回リリースのため、既存コードの設計方針・API を文書化（モジュール docstring に詳細記載）。

Fixed
- （初回リリースにつき該当なし）

Security
- OpenAI API キーは引数で注入可能。環境変数未設定時に明示的エラーを出すことで誤設定を検出しやすくしている。

Notes / 設計上の重要点（既知の制約）
- ルックアヘッドバイアス回避:
  - 各 AI / 研究関数は datetime.today()/date.today() を直接参照せず、必ず target_date を引数で受け取る設計。
- フェイルセーフ挙動:
  - 外部 API（OpenAI / J-Quants 等）失敗時は可能な限り局所的にフォールバック（スコア 0.0、対象除外等）して処理を継続。
- DuckDB 互換性:
  - executemany の空リストバインドなど DuckDB バージョン差異を考慮した実装を行っている（空時には実行をスキップ）。
- テスト性:
  - OpenAI 呼び出しを差し替え可能にしてユニットテストを容易にするフックを設置。
- ロギング:
  - 重要な分岐やフェイルセーフ時に logger を通じて警告/情報を出力するよう実装。

今後の予定（TODO / 予定機能）
- pipeline モジュールの残り実装（ETL の差分計算・品質チェックの呼び出しテンプレート等）とテスト。
- jquants_client / quality 等外部依存モジュールとの統合テスト。
- 追加のファクター（PBR・配当利回り等）実装。
- モデル/プロンプトチューニングおよび OpenAI レスポンス検証の強化。

ライセンス・貢献
- 初回リリース。貢献・バグ報告は issue/PR を通じて受け付けてください。