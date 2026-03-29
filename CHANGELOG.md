# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のリリース方針:
- バージョンは semantic versioning (MAJOR.MINOR.PATCH) に従います。
- 初期リリースでは主要機能群（データ取得・ETL、カレンダー管理、リサーチ、AIによるニュース解析・レジーム判定、設定管理）を含みます。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-29

### Added
- パッケージ基礎
  - パッケージ初期化とエクスポートを追加（kabusys.__init__）。
  - バージョンを `0.1.0` に設定。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local からの自動ローディング機能を実装（プロジェクトルート検出は .git または pyproject.toml）。
  - export 文・クォート・インラインコメントなどを考慮した .env パーサ実装（_parse_env_line）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 環境変数必須チェック `_require` と Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須設定プロパティ。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証。
    - データベースパス用の duckdb_path / sqlite_path プロパティ。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI モジュール（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（ai_score）を計算する `score_news` を実装。
    - JST 時間ウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST）を行う `calc_news_window` を提供。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたり記事数上限・文字数トリム、JSON モードでのレスポンス検証、スコアの ±1.0 クリップ等を実装。
    - API エラー（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフとリトライロジックを搭載。
    - テスト容易性のため OpenAI 呼び出し箇所は patch で差し替え可能（_call_openai_api）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離と、マクロニュースの LLM センチメントを合成して日次レジーム（bull/neutral/bear）を判定する `score_regime` を実装。
    - MA 重み 70%、マクロ重み 30%（定数化）、閾値に基づくラベリング、スコアのクリップ処理。
    - raw_news からマクロキーワードで記事抽出、OpenAI（gpt-4o-mini）でマクロセンチメント評価、API エラー時はフェイルセーフとして macro_sentiment=0.0 を採用。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施。
    - テスト置換可能な OpenAI 呼び出しラッパー（_call_openai_api）。

- データ（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX マーケットカレンダー取得・保持ロジックと営業日判定ユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar が存在しない場合は曜日（土日）ベースのフォールバックを利用。
    - 夜間バッチ用 calendar_update_job を実装（J-Quants クライアント経由で差分取得・保存）。バックフィル・健全性チェックを含む。

  - ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分更新、backfill、品質チェック（quality モジュール連携）を想定した ETL パイプライン基盤を実装。
    - DuckDB を前提としたテーブル存在チェック、最大日付取得ユーティリティなどを提供。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER/ROE）計算関数を実装:
      - calc_momentum, calc_volatility, calc_value を提供。
    - DuckDB 上の prices_daily / raw_financials テーブルのみ参照し、外部 API に依存しない設計。

  - 特徴量探索・統計（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）。
    - IC（Information Coefficient）計算（calc_ic）およびランク関数（rank）。
    - ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず純粋 Python + DuckDB で実装。

- テスト/運用面の配慮
  - OpenAI 呼び出し箇所はユニットテストで patch しやすいように内部関数を分離（各モジュールに _call_openai_api を定義）。
  - DuckDB の executemany に関する制約（空リスト送信不可）を回避するためのチェックを導入。
  - ルックアヘッドバイアス回避の設計（datetime.today()/date.today() を直接参照しない）を各 AI / リサーチ処理で採用。

### Changed
- 初回リリースのため無し（初期導入機能のみ）。

### Fixed
- 初回リリースのため無し。

### Deprecated
- 初回リリースのため無し。

### Removed
- 初回リリースのため無し。

### Security
- 初期版ではセキュリティに関する特記事項なし。ただし OpenAI API キー・各種シークレットは環境変数経由で取り扱う設計。

---

注記:
- OpenAI モデルは gpt-4o-mini を使用するようにハードコーディングされています。将来的にモデル名や呼び出し方式を変更する場合は各モジュール（kabusys.ai.news_nlp, kabusys.ai.regime_detector）の定数を更新してください。
- DB テーブル名（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials, news_symbols など）に依存する実装です。実運用前にスキーマ整備が必要です。
- .env パースや自動ロードの挙動は開発環境での利便性を重視しています。CI/本番では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を推奨します。