Keep a Changelog に準拠した CHANGELOG（日本語）
==============================================

すべての注記は仕様/ソースコードから推測して作成しています。

フォーマットについて: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

0.1.0 - 2026-04-03
------------------

Added
- 初回リリース: kabusys パッケージの公開。
- 基本パッケージ情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - 公開モジュール: data, strategy, execution, monitoring（__all__ に準拠）

- 環境設定 / config
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env/.env.local 読み込みの優先順（OS 環境 > .env.local > .env）と、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env の行パーサを独自実装（export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメントの取り扱いに対応）。
  - Settings クラスを提供し、主要設定をプロパティとして取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）や監視用ファイルパス（PID_FILE_PATH, KILL_FLAG_PATH）
    - 閾値設定（CPU/MEMORY/DISK）
    - 環境（KABUSYS_ENV: development, paper_trading, live の検証）と LOG_LEVEL の検証
  - 必須環境変数未設定時は ValueError を送出する _require() を実装。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄ごとのセンチメント ai_score を計算し ai_scores テーブルに書き込む機能を実装。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換）を対象に収集。
    - バッチ処理: 最大 20 銘柄/リクエスト、1 銘柄あたり最大記事数と文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - OpenAI 呼び出しのリトライ（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフ実装。
    - レスポンス検証とスコアの ±1.0 クリップ、部分成功時に既存スコアを保護するための個別 DELETE → INSERT の冪等書き込み。
    - テスト容易性のため _call_openai_api をモック差し替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルに書き込む機能を実装。
    - マクロキーワードで raw_news をフィルタし、最大 N 件までを LLM に渡す設計（デフォルト gpt-4o-mini）。
    - LLM 呼び出し失敗時は macro_sentiment を 0.0 としてフォールバック（フェイルセーフ）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）、OpenAI 呼び出し周りにリトライ/バックオフ処理。
    - レジーム合成ロジック、スコアのクリップと閾値 (_BULL_THRESHOLD, _BEAR_THRESHOLD)。

- データ処理（kabusys.data）
  - calendar_management
    - JPX カレンダー管理と営業日判定ユーティリティを実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - market_calendar が未取得の場合は曜日（土日）ベースのフォールバックを行う設計。
    - calendar_update_job: J-Quants API からカレンダーを差分取得して保存する夜間バッチ処理（バックフィル、健全性チェックあり）。
    - 最大探索日数や lookahead/backfill の定数設定で安全性を確保。
  - pipeline / etl
    - ETLResult データクラスを追加。ETL 実行結果（取得数、保存数、品質問題、エラー等）を保持し to_dict でシリアライズ可能。
    - 差分取得・保存・品質チェックを想定した ETL 設計（jquants_client, quality と連携）。
    - DuckDB に関する互換性注釈（executemany に空リストを渡さないなど）。

- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新の EPS / ROE を取得して PER / ROE を計算（EPS が 0/欠損のときは None）。
    - 全関数は DuckDB の prices_daily/raw_financials を参照し、外部発注 API 等には依存しない設計。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）で将来リターンを計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。3 レコード未満は None。
    - rank, factor_summary: ランク化と基本統計量（count/mean/std/min/max/median）を提供。
  - data.stats の zscore_normalize を再エクスポート。

- 一般的設計方針（全体）
  - ルックアヘッドバイアス回避のため、datetime.today() / date.today() を関数内部で多用しない設計（多くの関数は target_date を明示的に受け取る）。
  - OpenAI / 外部 API 呼び出しに対してはフェイルセーフ（エラー時にスキップ・フォールバック）とリトライを実装し、処理の継続性を優先。
  - DB 書き込みは可能な限り冪等に設計（DELETE→INSERT、ON CONFLICT を想定）し、部分失敗が他のデータを毀損しないよう保護。
  - DuckDB のバージョン差異への対処（executemany の空リスト回避など）を考慮。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Security
- 環境変数取り扱いに注意:
  - 自動 .env ロードはデフォルトで有効だが、テストなどで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定可能。
  - 必須トークン（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY）は明示的にチェックされ、未設定時は ValueError を送出するため運用時に見落としが起きにくい設計。

Known issues / Notes
- calc_value: PBR や配当利回りは現バージョンでは未実装（注釈あり）。
- news_nlp / regime_detector は OpenAI（gpt-4o-mini）依存。API の利用に際しては API キー・使用コスト・レスポンス仕様に注意が必要。
- monitoring/strategy/execution モジュールはパッケージ公開対象として __all__ に含まれているが、今回の差分には未掲載（別途実装が想定される）。
- DuckDB に依存するため、利用環境に DuckDB が必要。

参考（設定例）
- 必須環境変数例:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - OPENAI_API_KEY（AI 機能を使う場合）
- 任意・デフォルト:
  - KABUSYS_ENV=development (other: paper_trading, live)
  - LOG_LEVEL=INFO
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db

作者注
- 本 CHANGELOG は提供されたソースコードからの推測に基づく記述です。実際のリリースノート作成時はテスト結果、追加の変更履歴（コミットメッセージ等）、外部依存のバージョン情報を併せて反映してください。