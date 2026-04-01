# Changelog

すべての変更は Keep a Changelog の規約に従って記載しています。  
このファイルにはパッケージの重要な追加・変更・修正点を日本語でまとめています。

## [0.1.0] - 2026-04-01

### Added
- パッケージ初期公開: kabusys v0.1.0
  - パッケージ公開用のエントリポイントを追加（src/kabusys/__init__.py）。
  - __all__ で主要サブパッケージを公開（data, strategy, execution, monitoring）。

- 環境設定モジュール（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート判定は .git または pyproject.toml）。
  - .env パーサーは export 形式、シングル/ダブルクォート、エスケープ、コメント処理に対応。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - OS 環境変数を保護するための上書き制御（protected set）を実装。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID の必須チェック
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等のデフォルト値
    - CPU/MEMORY/DISK 閾値設定（float）
    - KABUSYS_ENV 値の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/...）および便利な is_live / is_paper / is_dev フラグ

- データプラットフォーム（src/kabusys/data）
  - ETL 関連:
    - ETLResult データクラスを公開（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py で再エクスポート）。
    - 差分取得・保存・品質チェックの設計に対応するユーティリティを実装（duckdb ベース）。
    - DuckDB のテーブル存在チェック・最大日付取得等のユーティリティを実装。
    - ETL の設計方針（バックフィル、部分失敗時の保護、品質チェックの収集）を反映。
  - カレンダー管理（src/kabusys/data/calendar_management.py）:
    - market_calendar テーブルを基にした営業日判定ロジックを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがない場合は曜日ベースのフォールバック（週末除外）を採用。
    - calendar_update_job：J-Quants から差分取得して冪等保存（バックフィル・健全性チェックあり）。
    - 最大探索日数やバックフィル日数等の安全装置を実装。

- 研究（research）パッケージ（src/kabusys/research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン・200 日移動平均乖離を計算。
    - calc_volatility: 20 日 ATR・相対 ATR・20 日平均売買代金・出来高比率を計算。
    - calc_value: raw_financials から PER / ROE を計算（EPS が 0 または欠損の場合は None）。
    - DuckDB SQL を主に用いる実装で、外部 API には依存しない設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算。
    - calc_ic: スピアマンランク相関（IC）を計算するユーティリティ（欠損・少数レコード処理あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
    - rank: 同順位は平均ランクで処理するランク変換ユーティリティ。
  - research.__init__ で主要関数群を再エクスポート（zscore_normalize は data.stats から再利用）。

- AI 関連（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）で一括センチメント評価して ai_scores テーブルへ書き込む。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ（calc_news_window）を実装。
    - 1 銘柄あたりの最大記事数 / 最大文字数制限、チャンク処理（最大 20 銘柄）を実装。
    - API 呼び出しは 429/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ。非再試行系はスキップして継続する設計（フェイルセーフ）。
    - レスポンスの厳密バリデーション（JSON 抽出、results 配列、コード整合性、数値チェック）を実装。スコアは ±1.0 にクリップ。
    - DuckDB の executemany の制約（空リスト不可）を考慮した安全な DB 書き込みロジック。
    - 単体テスト容易化のため _call_openai_api を差し替え可能に設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）:
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - マクロキーワードで raw_news をフィルタし、最大 20 件まで LLM に渡す。LLM は gpt-4o-mini を使用。
    - API 呼び出しのリトライ・エラー処理、JSON パース失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ設計。
    - レジームスコアはクリップされ、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - ルックアヘッドバイアス防止のため、内部で datetime.today()/date.today() を参照しない設計（target_date ベース）。

### Changed
- 初期公開のため該当なし（新規追加中心）。

### Fixed
- API エラー・パースエラーに対して例外を直接上げずフェイルセーフにフォールバックする実装を採用（運用での堅牢性向上）。
- DuckDB の互換性問題（executemany に空リスト不可）への対応を実装。

### Security
- OpenAI / J-Quants / kabu API 用の機密トークンは環境変数で管理する設計（Settings で必須チェック）。
- 自動 .env ロード時に既存 OS 環境変数を保護する仕組みあり（.env.local は上書き可能だが OS 環境変数は protected）。

### Notes / Known issues
- OpenAI に依存する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）が必須。API 利用コストとレート制限に注意してください。
- news_nlp / regime_detector は gpt-4o-mini の JSON Mode を想定してレスポンスをパースしますが、外部モデルや将来の SDK 変更により挙動が変わる可能性があります。テスト時は _call_openai_api をモックしてください。
- 時間の扱いは一部で UTC naive な datetime を使用（JST ↔ UTC の変換ロジックは calc_news_window などで明示）。タイムゾーン混入に注意してください。
- DuckDB バージョン依存の挙動（例: executemany の空リスト制約）に留意してください。互換性のための既知のワークアラウンドを実装済み。
- calendar_update_job の健全性チェックや _MAX_SEARCH_DAYS 等の安全装置は過度に保守的な設定により一部運用で更新が行われない場合があります。運用状況に合わせて設定を調整してください。

### Migration
- 新規リリースのため移行手順は不要ですが、環境変数（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD, OPENAI_API_KEY など）の準備が必要です。
- 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

（補足）この CHANGELOG はソースコードからの推測に基づいて作成しています。実際のリリースノートに含めるべき運用手順、依存関係、既知のバグ修正等は必要に応じて追記してください。