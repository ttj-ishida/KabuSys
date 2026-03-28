# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
このファイルはコードベースから推測して作成した初期リリース向けのログです。

## [0.1.0] - 2026-03-28

### Added
- 初期リリース（0.1.0）。
- パッケージの公開インターフェース
  - パッケージルート: kabusys.__version__ = "0.1.0"。
  - __all__ により主要サブパッケージ（data, research, ai など）を公開。

- 設定・環境変数管理（kabusys.config）
  - .env および .env.local の自動ロード機能を実装（プロジェクトルートは .git / pyproject.toml を探索して決定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ実装（export 形式対応、クォート・エスケープ・コメント処理対応）。
  - 環境変数の必須取得ヘルパー _require と型チェックを持つ Settings クラスを提供。
  - 主要な設定項目をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev の便捷プロパティ

- データ基盤ユーティリティ（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブル読み書き、夜間バッチ calendar_update_job）。
    - 営業日判定ユーティリティ: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB 未取得時の曜日ベースフォールバック、最大探索日数制限、バックフィル・健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラス（ETL 実行結果の集約、品質問題の集約、辞書化メソッド）。
    - ETL パイプライン設計に基づく差分取得/保存/品質チェックの設計方針（jquants_client, quality との連携を想定）。
    - _table/_get_max_date 等の内部ユーティリティを提供。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- 研究（research）モジュール（kabusys.research）
  - factor_research:
    - モメンタムファクター calc_momentum（1M/3M/6M リターン、200日 MA 乖離）。
    - ボラティリティ／流動性 calc_volatility（20日 ATR、相対ATR、平均売買代金、出来高比率）。
    - バリュー calc_value（PER、ROE、raw_financials からの直近財務データ利用）。
    - DuckDB SQL を利用した高効率実装。データ不足時の None 返却などの堅牢性を備える。
  - feature_exploration:
    - 将来リターン calc_forward_returns（任意ホライズン、入力検証、1クエリ実装）。
    - IC（Information Coefficient）calc_ic（スピアマンランク相関、レコード結合と欠損ハンドリング）。
    - rank（同順位は平均ランク処理）。
    - factor_summary（count/mean/std/min/max/median の算出）。
    - pandas 等に依存しない純標準ライブラリ実装。

- AI / NLP 機能（kabusys.ai）
  - news_nlp:
    - score_news: raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini、JSON mode）で銘柄ごとにセンチメントを評価。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算 calc_news_window を提供。
    - バッチ化（最大 20 銘柄/コール）、1銘柄あたり記事数と文字数のトリム（上限あり）。
    - API 呼び出しでの 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列・code/score 検証）、スコアを ±1.0 にクリップ。
    - DuckDB への冪等書き込み（DELETE→INSERT の部分置換）で部分失敗時の保護。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
  - regime_detector:
    - score_regime: ETF 1321（日経225連動）200日 MA 乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）判定。
    - マクロニュース抽出（キーワードリスト）、OpenAI（gpt-4o-mini）による JSON 出力のパースとリトライ。
    - レジームスコア合成ロジック（クリッピングと閾値判定）、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - ルックアヘッドバイアス回避のため日付比較は target_date 未満のみ使用、datetime.today() を参照しない設計。
    - API エラー時はフェイルセーフ（macro_sentiment = 0.0）で継続。

- 共通設計上の配慮
  - DuckDB を主な時系列データストアとして想定（prices_daily, raw_news, raw_financials, market_calendar, ai_scores, market_regime 等）。
  - API 呼び出しは堅牢にリトライ/フェイルセーフ実装。
  - DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT を想定）。
  - ルックアヘッドバイアス対策として内部で現在日付を直接参照しない API 設計。
  - テスト容易性（OpenAI 呼び出し関数の差し替えポイント等）を考慮。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Security
- 初期リリースのため該当なし。  
  （注意: OpenAI API キーや各種トークンは環境変数で管理する設計。JQUANTS_REFRESH_TOKEN、OPENAI_API_KEY、SLACK_BOT_TOKEN 等は外部に漏洩しないよう運用上の注意が必要）

---

注記:
- 本 CHANGELOG はソースコードの実装内容から機能・振る舞いを推測して作成しています。実際のリリースノートとして利用する場合は、リリース担当者の確認・追記（既知の既知バグ、既存互換性・制限、デプロイ手順など）を推奨します。