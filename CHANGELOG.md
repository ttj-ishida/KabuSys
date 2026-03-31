# CHANGELOG

すべての変更は "Keep a Changelog" の方針に従って記載しています。  
本ファイルには、このコードベースの初期リリース（0.1.0）に相当する主要な追加・設計決定・修正点を、ソースコードの内容から推測してまとめています。

全ての注目すべき変更はここに記録します。セマンティックバージョニングを使用しています。

## [0.1.0] - 2026-03-31

### 追加
- パッケージ初期構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理（kabusys.config）
  - .env/.env.local ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行うため CWD に依存しない。
    - 読み込み優先度: OS 環境変数 > .env.local（上書き） > .env（未設定時のみ）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで自動ロードを無効化可能（テスト用途）。
  - .env パーサ実装（kabusys.config._parse_env_line）
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ処理対応、コメントルール（クォート有無での扱い差）など堅牢なパース。
  - 環境変数必須チェック（_require）と Settings クラスを実装。
    - 必須設定例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト値付き設定: KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、KABUSYS_ENV
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。
    - Settings に便利なブールプロパティ is_live / is_paper / is_dev を追加。

- AI（自然言語処理）関連機能（kabusys.ai）
  - ニュース NLU（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）に送信しセンチメントを取得する機能を実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を標準とし、UTC に変換して DB クエリで扱う（calc_news_window）。
    - バッチ処理: 1 API 呼び出しあたり最大 20 銘柄（_BATCH_SIZE）でチャンク送信。
    - 1 銘柄あたり最大記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）によりトークン肥大化を抑制。
    - JSON Mode 応答の堅牢なパースとバリデーション（_validate_and_extract）を実装。余分な前後テキストの復元や未知コード無視、数値検証、スコア ±1.0 クリップを行う。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ実装。失敗時はログを残して当該チャンクをスキップ（フェイルセーフ）。
    - 書き込みは部分成功を考慮し、取得成功したコードのみ DELETE → INSERT で置換（トランザクション／ROLLBACK 考慮）。
    - OpenAI クライアント呼び出しは _call_openai_api に抽象化し、テスト時にモック可能に設計。
    - 公開 API: score_news(conn, target_date, api_key=None) — 書き込み件数を返す。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する機能を実装。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロニュースは raw_news からマクロキーワード（日本・米国・グローバルの主要語）でフィルタしてタイトルを取得し、OpenAI による JSON 出力をパースして macro_sentiment を取得。
    - API 呼び出しのリトライ、5xx の扱い、JSON パース失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - レジームスコア合成と閾値判定（_BULL_THRESHOLD/_BEAR_THRESHOLD）を実装。結果は market_regime テーブルに冪等的に（DELETE/INSERT）保存。
    - OpenAI 呼び出しはテストで差し替え可能に抽象化。
    - 公開 API: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを基に営業日判定・前後営業日検索・期間内営業日取得・SQ 日判定を提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar が未取得または該当日が未登録の場合は曜日ベース（土日）でのフォールバックを実装。
    - calendar_update_job による J-Quants API からの差分取得・バックフィル（直近 _BACKFILL_DAYS 再フェッチ）・健全性チェック（将来日付の異常検出）と保存処理を実装。
    - DB 存在チェックや NULL 値検出時のログ処理を実装。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETL 実行結果を表現するデータクラス ETLResult を実装（取得件数・保存件数・品質問題・エラー一覧を保持）。
    - テーブル存在チェック、最大日付取得等のユーティリティを実装。
    - 差分更新、バックフィル、品質チェックを行う方針を反映する設計（実装は pipeline の枠組み）。
  - etl モジュールでは ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算する calc_momentum を実装。
    - Volatility / Liquidity: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算する calc_volatility を実装。
    - Value: raw_financials から最新財務データを取得して PER（EPS が 0/欠損なら None）、ROE を計算する calc_value を実装。
    - DuckDB のウィンドウ関数を多用し、営業日ベースの窓を考慮した設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト [1,5,21]）をサポート。Horizon の検証（正の整数かつ <= 252）と一括 SQL による取得を実装。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関をランク化ユーティリティ rank を用いて計算。十分な有効レコードがない場合は None を返す。
    - rank: 同順位は平均順位を割り当てる実装。丸め（round(..., 12)）により浮動小数点の ties 判定を安定化。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー機能を実装。
  - research パッケージは必要なユーティリティを再エクスポートする __init__ を提供。

- パッケージ初期公開 API
  - kabusys.__init__ で主なサブパッケージ（data, research, ai, ...）を __all__ に追加して公開。

### 変更（設計上の重要点）
- ルックアヘッドバイアス防止の設計方針を一貫して採用
  - 各種処理（score_news, score_regime, factor 計算等）で datetime.today()/date.today() を本処理内部で直接参照しない。外部から target_date を与えるインターフェースを採用。
  - DB クエリでも target_date 未満／LEAD/ LAG の指定等により将来データ利用を防止。

- エラー／堅牢性設計
  - OpenAI 呼び出し周りはリトライ（429 / ネットワーク / タイムアウト / 5xx）を実装し、全失敗時はフェイルセーフ動作（スコア 0.0 を採用するなど）で継続する方針。
  - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を確保し、例外時は ROLLBACK を試行。ROLLBACK 失敗は警告ログを残す。
  - DuckDB のバージョン差異（executemany に空リストを与えられない等）を回避するためのチェックを挟んでいる。
  - ロギングを各所に追加し、問題箇所の診断を容易にしている。

### 修正（実装上の注意点）
- JSON Mode の応答で余分なテキストが混入するケースに対して、最外の {} を抽出して復元する耐性ロジックを実装（news_nlp._validate_and_extract）。
- OpenAI SDK の APIError に対して status_code が存在するかどうかに依存しない実装（getattr）にし、将来の SDK 変更に強くしている（regime_detector / news_nlp 共通）。

### 既知の制約 / 注意事項
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY により解決。未設定時は ValueError を発生させる設計。
- 一部関数は DuckDB 接続オブジェクトを直接受け取り、テーブル構造（prices_daily, raw_news, ai_scores, market_calendar, raw_financials など）への依存がある。
- ETL の実行フロー（差分取得・品質チェックの詳細）は pipeline モジュールの方針に従う（QualityIssue 型などを通じて品質情報を伝搬）。
- 現時点で PBR や配当利回りなど一部バリューファクターは未実装。

### セキュリティ
- 特別なセキュリティ修正はこのバージョンで報告されていません。環境変数や API キーは OS 環境で管理することを推奨します。

---

今後のリリース案（想定）
- 0.2.0: 発注・実行（execution モジュール）実装、監視（monitoring）機能拡張、ETL の自動スケジューリング実装
- 0.1.x: バグ修正、テストカバレッジ拡充、OpenAI 呼び出し周りの堅牢化、J-Quants クライアントの差分取得最適化

（この CHANGELOG はソースコードから推測して作成しています。実際のコミット履歴を基にしたものではない点をご留意ください。）