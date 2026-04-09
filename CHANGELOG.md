# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
日付はこのリリース作成日: 2026-04-09

## [Unreleased]
- 次のリリースに向けた未反映の変更はありません（初回リリース）。

## [0.1.0] - 2026-04-09

初回公開リリース。主な追加・設計方針・実装ポイントを以下にまとめます。

### Added
- パッケージ公開
  - パッケージ名: kabusys、バージョン: 0.1.0
  - top-level: src/kabusys/__init__.py にて __version__ と主要サブパッケージをエクスポート（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
    - 自動 .env 読み込み:
      - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local をロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
      - .env/.env.local の読み込みは OS 環境変数を保護する仕組み（protected set を使用）。
    - 高度な .env パーサ実装:
      - export KEY=val 形式、シングル/ダブルクォート内のエスケープ、インラインコメント処理等に対応。
    - 必須環境変数取得時の _require による明示的なエラー報告。
    - 各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_*、DBパス、監視設定、PAPER_FILL_MODE 等）。
    - PAPER_FILL_MODE のバリデーション（instant, partial, never, reject を許容）。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL のバリデーション。
    - ユーティリティプロパティ: is_live / is_paper / is_dev。

- AI（ニュース NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news + news_symbols を集約し、OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメント（ai_score）を算出し ai_scores テーブルへ保存するフローを実装。
    - 対象時間ウィンドウ（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で計算。
    - バッチ処理（最大 20 銘柄 / 呼び出し）、1 銘柄あたり記事数と文字数のトリム制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - OpenAI 呼び出しでのリトライ（429・ネットワーク断・タイムアウト・5xx を指数バックオフで再試行）、レスポンスのバリデーション（JSON 抽出 / results 構造 / 型チェック）、スコアの ±1.0 クリップ。
    - 部分失敗対策として、成功取得分のみを DELETE → INSERT によって ai_scores に置換（部分失敗時に既存スコアを保護）。
    - テスト容易性のため _call_openai_api をパッチ差替え可能。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定する処理を実装。
    - prices_daily からの ma200_ratio 計算（look-ahead バイアス防止のため target_date 未満のみ使用、データ不足時は中立扱い）。
    - raw_news からマクロキーワードでフィルタしてタイトルを取得、OpenAI により macro_sentiment を算出（記事がない場合は LLM 呼び出しをスキップし 0.0 を採用）。
    - OpenAI 呼び出しはリトライ実装・エラー時フォールバック (macro_sentiment=0.0)。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - テスト容易性のため news_nlp と内部的に _call_openai_api を共有せず独立実装。

- データプラットフォーム（DuckDB ベース）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day など。
    - DB にカレンダーが無い場合は曜日ベースのフォールバック（土日非営業日）。
    - next/prev_trading_day は最大探索日数制限を設けて安全に探索。
    - calendar_update_job: J-Quants API から差分取得→保存（バックフィル・健全性チェック・例外処理あり）。
    - jquants_client（外部モジュール）経由での取得・保存を想定。

  - src/kabusys/data/pipeline.py と etl.py
    - ETL パイプラインの基本概念を実装（差分取得・保存・品質チェックの流れ）。
    - ETLResult dataclass を実装（取得/保存件数、品質問題リスト、エラーリスト等を保持、to_dict による直列化）。
    - デフォルトのバックフィル日数・カレンダー lookahead 等の定義。
    - quality モジュールとの連携を想定（品質問題は収集して呼び出し元で判断）。

  - src/kabusys/data/__init__.py と etl 再エクスポート
    - ETLResult をデータ API として再エクスポート。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ（ATR 等）、バリュー（PER, ROE）などのファクター算出機能を実装。
    - DuckDB の window / analytic 関数を使った SQL ベースの実装。
    - 関数: calc_momentum, calc_volatility, calc_value（それぞれ date, code ベースの dict list を返す）。
    - データ不足時の None 設定やログ出力。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（可変ホライズン、入力バリデーション）。
    - IC（Information Coefficient）計算 calc_ic（Spearman ランク相関）。
    - rank（同順位は平均ランク）と factor_summary（count/mean/std/min/max/median）のユーティリティ実装。
    - 標準ライブラリのみで完結する設計（pandas 等には依存しない）。

- テスト/保守性向上のための設計配慮（全体）
  - ルックアヘッドバイアス防止: 各所で datetime.today() / date.today() を参照しない、関数は target_date を引数で受ける設計。
  - DuckDB を一次データストアとして利用する前提で SQL と Python を組み合わせた実装。
  - OpenAI API 呼び出し部分は各モジュールで独立して実装し、ユニットテストで差し替え可能（patchable）。
  - フェイルセーフ設計: API 失敗時は例外を投げずスコアを 0.0 にフォールバックするなどの保守的動作。
  - ロギングを各モジュールに導入（警告・情報レベルのログ出力）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

### Notes / 開発者向け補足
- OpenAI API キーは関数引数経由で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照。未設定の場合は ValueError を送出。
- .env 自動読み込みの挙動に依存するテストを行う場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用して自動ロードを抑止可能。
- DuckDB の executemany に空リストを渡すとエラーになるため、実装内で空チェックを行っている（互換性考慮）。
- jquants_client / quality モジュールは外部依存（別モジュール実装）を想定しており、テスト時はモックすること。

---

今後の予定（例）
- strategy / execution / monitoring サブパッケージの実装拡充（アルゴリズム実装・発注クライアント等）。
- テストカバレッジの拡充、CI による静的解析・型チェックの導入。
- OpenAI 呼び出し回数削減のためキャッシュやより緻密なバッチ戦略の追加。