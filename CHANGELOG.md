# Changelog

すべての変更は Keep a Changelog のフォーマットに従い、Semantic Versioning を採用しています。
初期リリースの内容はソースコードから推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API として data / strategy / execution / monitoring を __all__ に設定。

- 設定 / 環境変数管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - export KEY=val 形式やクォート文字列のエスケープ、行末コメント処理などに対応した .env パーサを実装。
  - override / protected オプションを持つ .env ロード処理を実装し、OS 環境変数の保護をサポート。
  - Settings クラスを実装し、以下の設定プロパティを提供：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
    - is_live / is_paper / is_dev のブールヘルパー

- データプラットフォーム / ETL (kabusys.data.pipeline, kabusys.data.etl)
  - ETL パイプラインの骨格と ETLResult データクラスを実装。
  - 差分取得、バックフィル、品質チェックを行う設計（jquants_client と quality モジュールとの連携想定）。
  - DuckDB を想定したテーブル存在確認や最大日付取得ユーティリティを実装。
  - ETL の結果を辞書に変換する to_dict() を実装（品質問題をシリアライズ）。

- カレンダー管理 (kabusys.data.calendar_management)
  - JPX マーケットカレンダー管理ロジックを実装。
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
  - calendar_update_job により J-Quants API から差分取得して market_calendar に冪等保存するバッチ処理を実装。
  - DB 未取得日のフォールバック（曜日ベース）や探索上限 (_MAX_SEARCH_DAYS)、バックフィル・健全性チェックを実装。

- ニュース NLP（マクロ / 銘柄ごとのセンチメント） (kabusys.ai.news_nlp, kabusys.ai.regime_detector)
  - news_nlp.score_news:
    - raw_news / news_symbols から指定時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を集約し、銘柄毎に最新記事を結合して OpenAI（gpt-4o-mini）へバッチ送信。
    - バッチサイズ _BATCH_SIZE=20、1銘柄当たり最大記事数や文字数を制限してトークン肥大化を抑制。
    - JSON Mode を期待し、レスポンスのバリデーションとスコア（±1.0 クリップ）抽出を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ、失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）。
    - ai_scores テーブルへ置換（DELETE → INSERT）する方式で部分失敗時に既存データを保護。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動）について直近 200 日の終値から MA200 乖離を計算。
    - マクロ経済ニュースをフィルタしてタイトルを抽出し、LLM（gpt-4o-mini）でマクロセンチメントを評価。
    - MA200 乖離（重み 70%）とマクロセンチメント（重み 30%）を合成し regime_score を算出（クリップ -1.0〜1.0）。
    - 閾値により regime_label を bull / neutral / bear に分類し market_regime テーブルへ冪等書き込み。
    - API 呼び出しのリトライ、パース失敗時のフォールバック（macro_sentiment = 0.0）を実装。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（DuckDB SQL ベース、データ不足時は None）。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials の最新財務情報と株価を組み合わせて PER / ROE を算出。
    - 各関数は prices_daily / raw_financials のみ参照し、外部発注等に影響しない設計。
  - feature_exploration:
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて一度に取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算（3件未満で None を返す）。
    - rank: 同順位は平均ランクを返すランク関数（round(v,12) による安定化）。
    - factor_summary: count/mean/std/min/max/median の基本統計量集計。

- データ品質 / エラー処理に関する設計方針（コード内に明示）
  - ルックアヘッドバイアス防止のため datetime.today() / date.today() をスコア・集計処理の自動参照に使わない設計。
  - DB 書き込みは冪等（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK 管理）で実施。
  - API 呼び出しは失敗時のフェイルセーフ（部分失敗を許容し処理を継続）を採用。
  - DuckDB バージョン差異や executemany の制約を考慮した実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは関数引数か環境変数 OPENAI_API_KEY で注入する設計。コード内でハードコーディングする実装はなし。

---

注記:
- 上記はソースコード（src 以下）から推測してまとめたリリースノートです。実際のリリース日や変更点はリポジトリの Git 履歴に基づいて調整してください。