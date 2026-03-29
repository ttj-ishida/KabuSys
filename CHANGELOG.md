# Keep a Changelog
すべての公開変更点はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。

### 追加 (Added)
- パッケージ全体の骨組みを実装
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py にて定義)

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込みをプロジェクトルート（.git または pyproject.toml 基準）から行う実装を追加。
  - .env ファイルのパース機能を実装（コメント行 / export プレフィックス / シングル/ダブルクォート / バックスラッシュエスケープ対応、インラインコメントの取り扱いなど）。
  - OS 環境変数を保護するための protected キーセット、override ロジックをサポート。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得ヘルパー _require と Settings クラスを追加。
  - Settings で J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等をプロパティとして提供。環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）を実装。
  - デフォルトの DB パス (DUCKDB_PATH, SQLITE_PATH) の取り扱い。

- AI 関連モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントスコアを取得し ai_scores テーブルへ保存。
    - 処理の特徴:
      - JST の前日 15:00 〜 当日 08:30 を対象ウィンドウとして calc_news_window を実装（UTC-naive datetime を返す）。
      - バッチ処理（1 API コールあたり最大 20 銘柄）。
      - 1 銘柄内は最大記事数と文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - API エラー（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフによるリトライ。
      - レスポンスの堅牢なバリデーションとスコアのクリップ（±1.0）。
      - 部分失敗時に既存スコアを誤って消さないよう、DELETE → INSERT の対象コードを絞った冪等書き込み。
      - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。
    - 公開関数: score_news(conn, target_date, api_key=None)。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で market_regime を決定するロジックを実装。
    - 処理の特徴:
      - ルックアヘッドバイアス防止（対象日未満のデータのみ使用、datetime.today() を参照しない）。
      - マクロ記事の抽出はキーワードベース（_MACRO_KEYWORDS）で最大 20 件まで取得。
      - OpenAI 呼び出しは独立実装でテスト置換可能（_call_openai_api）。
      - API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
      - スコア合成後、market_regime テーブルへ削除→挿入の冪等書き込みを行う（トランザクション処理）。
      - 公開関数: score_regime(conn, target_date, api_key=None)。

- データ処理モジュール (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーを扱うユーティリティ群を実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
      - calendar_update_job: J-Quants API から差分取得して market_calendar テーブルを冪等に更新する夜間バッチ処理
    - 設計上の特徴:
      - market_calendar 未登録時は曜日ベースのフォールバック（週末を非営業日扱い）。
      - DB 登録値を優先し、未登録日は曜日フォールバックで一貫して扱う。
      - 最大探索日数制限（_MAX_SEARCH_DAYS）等の安全装置。
  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETLResult データクラスを実装し、取得数・保存数・品質問題・エラーを集約して返却。
    - 差分更新・バックフィル・品質チェックの設計方針を実装（jquants_client と quality モジュールを利用）。
    - etl モジュールで ETLResult を再エクスポート。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER・ROE）等の計算関数を追加:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - DuckDB を用いた SQL ベースの計算で、prices_daily / raw_financials を参照。データ不足時は None を返す設計。
  - feature_exploration
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)
    - IC（Spearman ρ）計算: calc_ic(factor_records, forward_records, factor_col, return_col)
    - 統計サマリー: factor_summary(records, columns)
    - ランキングユーティリティ: rank(values)
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- その他の公開 API
  - kabusys.ai.__all__ に score_news を追加。
  - kabusys.research.__all__ に主要関数を追加。
  - kabusys.data.etl で ETLResult を再エクスポート。

### 変更 (Changed)
- （初回リリースにつき該当なし）

### 修正 (Fixed)
- （初回リリースにつき該当なし）

### セキュリティ (Security)
- （初回リリースにつき該当なし）

### 技術的な注意事項 / デザインノート
- DuckDB を想定した SQL 実装になっており、空の executemany 引数に対する互換性（DuckDB 0.10 の制約）を考慮している箇所がある。
- OpenAI（gpt-4o-mini）呼び出しは JSON Mode を利用する想定。API 応答の形式が不正な場合でも堅牢に処理するためのパース/補正ロジックを実装している。
- いくつかの処理はルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計（与えられた target_date に対して deterministically 動作する）。
- API キーや外部リソース呼び出し時はフェイルセーフ（デフォルトスコアやスキップ）で処理を継続する方針。

---

貢献・不具合報告は issue を通じてお願いします。