# CHANGELOG

すべての変更は Keep a Changelog 準拠の形式で記載しています。  
主にコードベースから推測できる機能追加・設計意図・注意点をまとめています。

全般ルール:
- 参照される日付はリリース日（このリポジトリの初期公開相当）を 2026-03-28 としています。
- 本CHANGELOGはコードの内容から推測して作成しており、実際のコミット履歴に基づくものではありません。

## [Unreleased]
- 今後の改善案・未実装メモ（コードから推測）
  - AI API 呼び出しのメトリクス収集／可観測性向上
  - ETL のスケジューリング・ジョブラッパーの追加
  - DB スキーマ（テーブル定義）のマイグレーションユーティリティ
  - OpenAI クライアントの抽象化（テスト用注入をより容易にするラッパー）
  - より詳細なエラーレポーティング（Slack 通知等）の組み込み

---

## [0.1.0] - 2026-03-28

### Added
- パッケージ基盤
  - kabusys パッケージ初期実装。バージョンは 0.1.0。
  - __all__ に data / strategy / execution / monitoring を公開。

- 環境設定/ローディング
  - 環境変数管理モジュール `kabusys.config` を追加。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env/.env.local を読み込む仕組み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応（テスト用）。
    - .env パーサは export 形式、クォート内のエスケープ、インラインコメントの扱いなどを実装。
    - 環境変数の必須チェック（_require）と Settings クラスを提供。主要設定プロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH, SQLITE_PATH
      - KABUSYS_ENV（development/paper_trading/live のバリデーション）
      - LOG_LEVEL（DEBUG/INFO/... のバリデーション）
    - OS 環境変数の保護（.env.local での上書き処理時に既存の OS 環境変数を保護）。

- データプラットフォーム関連
  - data パッケージ（初期モジュール群）
    - calendar_management:
      - JPX カレンダー取り扱い（market_calendar テーブル参照）と夜間更新ジョブ（calendar_update_job）。
      - 営業日判定ユーティリティ: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
      - DB が未取得／一部のみ取得のときは曜日ベースでフォールバックする堅牢な設計。
      - 最大探索日数制限やバックフィル・整合性（sanity）チェックを実装。
      - J-Quants クライアント経由でのフェッチおよび保存処理を想定（jquants_client 呼び出し）。
    - pipeline / etl:
      - ETLResult データクラスを追加（ETL 実行結果の集約）。
      - ETL パイプラインのユーティリティ（差分取得／保存／品質チェック方針の実装設計）。
      - テーブル存在チェックや最大日付取得のユーティリティ。
      - ETL の設計上の方針（backfill、品質チェックの非 Fail-Fast 動作など）を実装。

- 研究（Research）モジュール
  - research パッケージおよび以下の機能を追加：
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）などを DuckDB クエリで計算。
      - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率等を計算。
      - calc_value: PER、ROE を raw_financials と prices_daily から結合して計算。
      - 設計方針として DuckDB の SQL ウィンドウ関数を活用し、外部 API に依存しない実装。
    - feature_exploration:
      - calc_forward_returns: 指定 horizon（営業日数）に対する将来リターンを一括取得する汎用実装（horizons の検証あり）。
      - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。NULL/非有限値の扱い、3 銘柄未満で None を返す。
      - rank: 平均ランクでの同順位処理（浮動小数誤差対策として round を利用）。
      - factor_summary: count/mean/std/min/max/median を算出するユーティリティ。

- AI / NLP モジュール
  - ai パッケージ（news_nlp, regime_detector）を追加。
    - news_nlp.score_news:
      - raw_news と news_symbols を元に銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を取得。
      - バッチサイズ、記事・文字数上限、JSON Mode（厳格 JSON 出力期待）を採用。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライロジック。
      - レスポンスのバリデーション（JSON 抽出、results 配列、code/score 検証、スコアを ±1.0 にクリップ）。
      - スコア取得銘柄のみ ai_scores テーブルを置換（DELETE→INSERT）して部分失敗時のデータ保護。
      - calc_news_window: JST ベースのニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
      - テストの容易性：_call_openai_api 等を単体で patch 可能な設計。
    - regime_detector.score_regime:
      - ETF 1321（日経225 連動 ETF）の 200 日 MA 乖離（重み 70%）と、news_nlp 風のマクロセンチメント（重み 30%）を合成して market_regime を日次で判定。
      - LLM 呼び出しは gpt-4o-mini を使用。API 呼び出しの失敗時には macro_sentiment=0.0 でフェイルセーフ継続。
      - スコア合成・ラベリング（bull/neutral/bear）と market_regime への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
      - OpenAI SDK の例外（RateLimitError, APIConnectionError, APITimeoutError, APIError）を考慮した堅牢なリトライ・エラーハンドリングを実装。

### Changed
- （初期公開のため該当なし）  
  - 設計や実装の注意点は各モジュール内ドキュメントに明記。特に「ルックアヘッドバイアスを避けるため datetime.today()/date.today() を直接参照しない」といった設計方針を一貫して採用。

### Fixed
- （初期公開のため該当なし）  
  - ただし各モジュールに以下の耐障害性処理を実装:
    - OpenAI 呼び出しの再試行と非致命化（macro_sentiment やスコア失敗時は 0.0 や空辞書を返す）。
    - DuckDB の executemany が空リストを許容しない点への対応（空チェックを導入）。
    - .env 読み込み時の I/O エラーは警告として扱い処理続行。

### Security
- セキュリティ関連の注意点（実装より推測）
  - 環境変数に API キーを期待（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN 等）。これらは .env ではなく OS のセキュアな手段で管理することを推奨。
  - .env.local によりローカル上書き可能だが、OS の環境変数は上書き保護される設計。

### Notes / Compatibility
- 依存関係（コード上で利用を想定）
  - duckdb: DB 操作全般に使用。
  - openai SDK: OpenAI の Chat Completions を利用（client.chat.completions.create を呼ぶ形）。
  - jquants_client: data.calendar_update_job / pipeline で外部 J-Quants API 呼び出しを想定（別モジュール実装）。
- DB スキーマ（コードから参照されているテーブル）
  - prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials, news_symbols など。
  - 実行前に対応するテーブル定義／インデックスの準備が必要。
- テスト容易性
  - AI 呼び出し部分（_call_openai_api）や OpenAI クライアント生成がモジュール内に点在するが、関数単位で patch 可能なように設計されているため単体テストが可能。

---

この CHANGELOG はコード本体から推測して作成しています。実際の変更履歴／コミットログと差異がある可能性があるため、リリース運用時は実コミット履歴に基づく追記・修正を行ってください。