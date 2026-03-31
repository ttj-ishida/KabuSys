# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

- リリース年月日はコミット時点またはパッケージ公開日を記載します。
- "Unreleased" セクションは次のリリースに向けた変更点を記載します。

---

## [Unreleased]

- （未リリースの変更はここに記載）

---

## [0.1.0] - 2026-03-31

初期リリース。

### Added
- パッケージ基盤
  - kabusys パッケージ初期構成。トップレベルで data / strategy / execution / monitoring を公開。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して決定。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント判定（非クォート部では '#' の前が空白/タブならコメント扱い）などをサポート。
  - 必須環境変数取得時の検証機能（未設定時は ValueError を送出）。
  - 主要設定プロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（API 呼び出し時に参照））とデフォルトパス（duckdb/sqlite/pid 等）を提供。
  - KABUSYS_ENV の検証（development/paper_trading/live）および LOG_LEVEL の検証。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news / news_symbols から指定ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）内のニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメントスコアを取得。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたり記事数・文字数のトリム実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンスバリデーション（JSON 抽出、"results" リスト、code と score の検証、数値変換、±1.0 でクリップ）。
    - DuckDB への書き込みは部分失敗に耐える設計（該当 code のみ DELETE → INSERT、executemany の空リストハンドリング考慮）。
    - API キーは引数で注入可能（テスト容易性）、未設定時は環境変数 OPENAI_API_KEY を参照。未設定なら ValueError。

  - regime_detector.score_regime:
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定・ market_regime テーブルへ冪等書き込み。
    - マクロニュースは news_nlp.calc_news_window を用いたウィンドウで抽出、LLM 呼び出しは独自の実装でモジュール結合を避ける。
    - API エラー時は macro_sentiment = 0.0 にフォールバック（警告ログを出力して継続）。
    - OpenAI の呼び出しはリトライ（最大回数・指数バックオフ）を行う。API キーは引数で注入可能または環境変数 OPENAI_API_KEY。
    - レジーム合成スコアをクリップし、閾値に応じてラベル付与。

- Data モジュール (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）: 営業日判定（is_trading_day）、next/prev_trading_day、get_trading_days、is_sq_day を実装。
    - DB 登録が無い場合は曜日（平日）ベースでフォールバック。DB 登録ありの場合は DB 値を優先し、未登録日は曜日フォールバックで補完する一貫したロジック。
    - next/prev の探索に上限（日数制限）を設けて無限ループ防止。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィル（直近 _BACKFILL_DAYS を再取得）と健全性チェック（将来日付の異常検出）を実装。

  - pipeline / ETL:
    - ETLResult クラスを提供（ETL 実行結果、品質問題、エラー一覧を格納）。
    - ETL の設計方針文書化（差分更新、バックフィル、品質チェックの扱い等）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得等（DuckDB 前提）。（pipeline モジュールから ETLResult を再エクスポート）

- Research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、ATR 相対値、20 日平均売買代金、出来高比率を計算。
    - calc_value: PER（EPS が 0/欠損時は None）、ROE を raw_financials と prices_daily から計算。
    - 全関数は DuckDB を用いた SQL 実行で実装。結果を (date, code) キーの dict リストで返す。

  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて一括取得。
    - calc_ic: Spearman（ランク相関）による IC 計算（NULL/非有限値除外、最小サンプル数チェック）。
    - rank, factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）算出。標準ライブラリのみで実装。

### Changed
- なし（初版のため該当なし）。

### Fixed
- なし（初版のため該当なし）。

### Security
- なし（特記すべきセキュリティ修正は無し）。

### Notes / Implementation details / 開発者メモ
- OpenAI 関連
  - 使用モデル: gpt-4o-mini（news_nlp, regime_detector）。出力は JSON モードを期待。
  - API 呼び出しはテスト時に差し替え可能（各モジュールの _call_openai_api をモック対象に想定）。
  - レスポンスパース失敗や API エラーはフェイルセーフで処理を継続（スコアは 0.0 または空辞書にフォールバック）。

- DuckDB / DB 書き込み
  - 重要な DB 書き込み処理は冪等性を意識して DELETE → INSERT または ON CONFLICT の方針を使用。
  - DuckDB のバージョン差異（executemany の空リスト不可など）を考慮したコードになっている。

- ルックアヘッドバイアス回避
  - 全ての分析/スコアリング関数は内部で datetime.today()/date.today() を直接参照しない設計。target_date を必須にして未来データ参照を防止。

### Breaking Changes
- 初回リリースのため既存互換問題は無し。ただし以下の点は注意:
  - 必須環境変数がいくつか存在する（起動時または API 呼び出し時に ValueError を投げる箇所あり）。運用前に .env を適切に設定してください。
  - .env の自動ロードはプロジェクトルート検出に依存する（.git または pyproject.toml）。配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

### Required / Recommended environment variables
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- SLACK_BOT_TOKEN（必須）
- SLACK_CHANNEL_ID（必須）
- OPENAI_API_KEY（score_news / score_regime 呼び出し時に必須）
- オプション: DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT 等（デフォルト値あり）

---

参考:
- 詳細な設計方針やアルゴリズムは各モジュールの docstring 内に記載されています（news_nlp, regime_detector, factor_research, pipeline, calendar_management 等）。必要に応じて該当ソースを参照してください。