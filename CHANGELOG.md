# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

フォーマットの意味:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連

---

## Unreleased
（なし）

---

## [0.1.0] - 2026-03-28

### Added
- 初回リリース: kabusys パッケージ（日本株自動売買システム）のベース実装を追加。
  - パッケージのバージョンは src/kabusys/__init__.py にて `__version__ = "0.1.0"` を設定。

- 環境設定管理 (kabusys.config)
  - プロジェクトルート自動検出機能を追加（.git または pyproject.toml を基準に探索）。
  - .env/.env.local の自動ロードロジック（OS 環境変数 > .env.local > .env の優先順位）。
  - .env ファイルのパース機能を実装（`export KEY=val` 形式、クォート内エスケープ、コメント取り扱い対応）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - Settings クラスを追加:
    - 必須設定の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - デフォルト値を持つ設定（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーション（許容値チェック）。
    - is_live / is_paper / is_dev のヘルパープロパティ。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）でセンチメントを評価し、ai_scores テーブルへ書き込む。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）用の calc_news_window を実装。
    - バッチ処理（最大20銘柄／チャンク）、1銘柄あたりの最大記事数・文字数トリム、JSON Mode 応答のバリデーションを実装。
    - 429・接続断・タイムアウト・5xx に対する指数バックオフリトライ、エラー時は該当チャンクをスキップ（フェイルセーフ）。
    - レスポンスパース時の冗長テキスト対応（最外の {} を抽出する復元ロジック）。
    - DuckDB への冪等的な書き込み（DELETE → INSERT、部分失敗時に既存データを保護）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルへ保存。
    - MA200 乖離計算、マクロニュース抽出（キーワードリスト）、OpenAI 呼び出しとリトライ、スコア合成ロジックを実装。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 とするフェイルセーフ。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT + ROLLBACK の保護）。
    - モデル・重み・閾値・バックオフ挙動などの定数化。

- データプラットフォーム (kabusys.data)
  - カレンダー管理（kabusys.data.calendar_management）
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day の営業日判定ユーティリティを実装。
    - market_calendar データが無い場合の曜日ベースのフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等的に更新（バックフィル・健全性チェック付き）。
    - 最大探索日数制限、バックフィル、サニティチェックなどの安全策を実装。

  - ETL パイプラインおよびユーティリティ（kabusys.data.pipeline, data.etl）
    - ETLResult データクラスを追加（取得数・保存数・品質チェック結果・エラー一覧などを保持）。
    - テーブル存在チェックおよび最大日付取得ユーティリティを実装。
    - 差分取得・バックフィル方針、品質チェックの扱い（Fail-Fast ではなく問題を収集して上位で判断）をドキュメント化。
    - data.etl で ETLResult を再エクスポート。

- リサーチモジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を DuckDB SQL で計算。
    - calc_volatility: 20日 ATR, ATR 比率, 20日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials と結合して PER, ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB を用いた窓関数ベースの実装、データ不足時の None 戻し。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターン算出（LEAD を使用）。
    - calc_ic: スピアマンランク相関（IC）を実装（欠損・同順位処理あり）。
    - rank: 同順位を平均ランクで扱うランク変換ユーティリティ（丸めで ties 検出の安定化）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算。
  - すべて標準ライブラリ＋DuckDB のみで完結し、外部依存（pandas 等）を避ける設計。

- 共通設計上の注記（ドキュメント化）
  - ルックアヘッドバイアス防止のため、score 系関数では datetime.today()/date.today() を直接参照せず、target_date 引数で操作する方針を採用。
  - OpenAI 呼び出しはモジュール間でプライベート関数を共有せず、各モジュールで独立実装（テスト時に patch で差し替え可能）。
  - DuckDB への書き込みは冪等性を意識（DELETE→INSERT、ON CONFLICT 等）して実装。
  - OpenAI 失敗系は基本的にフェイルセーフ（スコアを 0 や空結果でフォールバック）を優先。

### Changed
- 初版リリースのため該当なし。

### Fixed
- 初版リリースのため該当なし。

### Security
- 初版リリースのため該当なし。
  - 注意点: OpenAI API キー、J-Quants トークン、Kabu API パスワード、Slack トークンなどは環境変数で管理する必要があります。必須環境変数が未設定の場合は Settings のプロパティが ValueError を投げます。

---

## マイグレーションノート / 利用開始時の注意
- 必須環境変数:
  - OPENAI_API_KEY（score_news, score_regime の呼び出し時に必要。api_key 引数で上書き可能）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を含むディレクトリ）を基準に行われます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- デフォルトのデータベースパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- OpenAI 呼び出しはリトライ・バックオフを備えていますが、使用量に応じたレート制限・コストに注意してください。
- DuckDB バージョンや executemany の挙動に依存する箇所があるため、互換性確認を推奨します（コード内に DuckDB 0.10 に関する注記あり）。

---

開発に関する問い合わせや、不足している機能（例: PBR・配当利回りの実装など）は issue を立ててください。