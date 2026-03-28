# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています（日本語）。

## Unreleased

- (今後の変更をここに記載)

## [0.1.0] - 2026-03-28

初期リリース。日本株自動売買システムのコア機能をまとめて公開します。以下はコードベースから推測した主な機能、設計上の方針、および注意点です。

### Added
- パッケージと公開 API
  - kabusys パッケージ初期バージョン（__version__ = 0.1.0）。
  - パッケージの公開モジュール: data, research, ai, execution, monitoring（__all__ に基づく）。

- 設定管理 (`kabusys.config`)
  - .env ファイル / 環境変数の自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env の堅牢なパーサ実装（export 形式対応、クォート内エスケープ、インラインコメント処理など）。
  - Settings クラスによるプロパティアクセスで必要な環境変数を明確化・検証:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - 任意・デフォルトあり: KABU_API_BASE_URL, DUCKDB_PATH (data/kabusys.duckdb), SQLITE_PATH (data/monitoring.db)
    - KABUSYS_ENV 値検証（development / paper_trading / live）
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI モジュール (`kabusys.ai`)
  - news_nlp:
    - ニュースのタイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST のウィンドウ）calc_news_window。
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）の JSON mode を用いてバッチでセンチメントを算出、ai_scores テーブルへ書き込み（部分置換: 対象コードのみ DELETE → INSERT）。
    - バッチング（最大20銘柄/コール）、1銘柄あたり記事数・文字数上限の対策、リトライ（429/ネットワーク/タイムアウト/5xx に対して指数バックオフ）、レスポンスバリデーション、スコアクリップ（±1.0）。
    - テスト用に _call_openai_api を patch できるように設計。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離 (ma200_ratio) とマクロニュースの LLM センチメントを重み付け（70% / 30%）して日次の market_regime を判定・保存。
    - マクロキーワードによるニュース抽出、OpenAI 呼び出し（gpt-4o-mini）と JSON パース、リトライ戦略、フェイルセーフ（API 失敗時 macro_sentiment=0.0）。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- Research モジュール (`kabusys.research`)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算（prices_daily を参照）。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: latest 財務データから PER・ROE を算出（raw_financials / prices_daily）。
    - DuckDB の SQL ウィンドウ関数を活用した実装。データ不足時は None を返す設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマン（ランク相関）による IC 計算（rank ユーティリティを含む）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - 標準ライブラリのみで実装（pandas 等に依存しない）。

- Data モジュール (`kabusys.data`)
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - calendar_update_job: J-Quants API から差分取得 -> 保存（fetch_market_calendar / save_market_calendar 呼出しを想定）。
    - バックフィル、先読み、健全性チェックを実装（例: 過度に将来の日付はスキップ）。
    - カレンダーデータ未取得時は曜日ベースのフォールバックを使用。
  - pipeline / etl:
    - ETLResult データクラス（target_date, fetched/saved counts, quality_issues, errors）を定義し、to_dict を提供。
    - 差分更新、backfill、品質チェック（quality モジュール利用）に対応する設計方針を実装。
    - DuckDB 互換性のための注意点（executemany に空リストを渡さない等）を反映。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- DuckDB と DB 書き込み
  - 各所で冪等性を考慮した DELETE→INSERT の置換方式、および BEGIN/COMMIT/ROLLBACK によるトランザクション制御。
  - executemany の空リスト回避や list 型バインド回避など、DuckDB バージョン差に対応する実装。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーを環境変数 OPENAI_API_KEY または各関数の api_key 引数で受け取る。AI 機能（score_news, score_regime）はキー未設定時に ValueError を送出し実行を停止する設計。

---

## 既知の制約・注意事項（コードから推測）
- AI 機能の実行には OpenAI の API キーが必須（api_key 引数または環境変数 OPENAI_API_KEY）。
- 環境変数の必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）が未設定だと Settings の該当プロパティ参照時に ValueError が発生するため、実運用前に .env を適切に設定する必要があります。
- DB スキーマ（テーブル名やカラム）がコードの期待と一致していることが前提（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）。
- 日付処理は意図的に date.today()/datetime.today() の直接参照を避けており、関数は target_date を明示的に受け取る設計。これによりルックアヘッドバイアスを抑制するが、運用側は適切な target_date を渡す必要があります。
- OpenAI 呼び出しは一部リトライ・フォールバックを実装しているが、完全な成功保証はない（失敗時はスコア 0.0 で継続する等のフェイルセーフ動作）。
- jquants_client（外部モジュール）に依存する箇所がある（カレンダーや ETL のデータ取得/保存）。これらの実装が必要。

---

必要があれば、各モジュールごとにより詳細な変更履歴や設計メモ、想定される DB スキーマ（DDL）や .env.example のテンプレートも作成します。どの範囲を深掘りしますか？