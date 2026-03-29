# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
慣例に従い、重要な変更点をカテゴリ別に記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージ名 kabusys とバージョン `0.1.0` を導入（src/kabusys/__init__.py）。
  - サブパッケージの公開 API を定義: data, strategy, execution, monitoring。

- 設定管理（kabusys.config）
  - .env / .env.local 自動読み込み機能を実装。プロジェクトルートの検出は `.git` または `pyproject.toml` を起点に行うため、CWD に依存しない。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定することで無効化可能。
  - `.env` ファイルのパースは以下をサポート:
    - 空行・コメント行の無視
    - export KEY=val 形式
    - シングル/ダブルクォートされた値のエスケープ解釈
    - インラインコメントの適切な扱い（クォート有無での差別化）
  - 環境変数取得ラッパー `_require` と Settings クラスを提供。Settings は以下のプロパティを持つ:
    - jquants_refresh_token (JQUANTS_REFRESH_TOKEN 必須)
    - kabu_api_password (KABU_API_PASSWORD 必須)
    - kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
    - slack_bot_token (SLACK_BOT_TOKEN 必須)
    - slack_channel_id (SLACK_CHANNEL_ID 必須)
    - duckdb_path / sqlite_path（デフォルトパスを提供）
    - env / log_level のバリデーション (`development`, `paper_trading`, `live` / `DEBUG`〜`CRITICAL`)
    - is_live / is_paper / is_dev の便利プロパティ

- AI モジュール（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（ai_score）を計算して ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ（JST 前日15:00〜当日08:30、UTC に変換して比較）計算ユーティリティ `calc_news_window` を提供。
    - バッチ処理（最大 20 銘柄／リクエスト）、記事数・文字数のトリム、JSON Mode 結果のバリデーション、スコアの ±1.0 クリップを実装。
    - レートリミット・接続断・タイムアウト・5xx は指数バックオフでリトライ。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - テスト容易性のため OpenAI 呼び出し箇所を _call_openai_api で切り出し、テスト用に差し替え可能。
    - API キー未設定時は ValueError を送出。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込みを行う。
    - マクロニュース抽出用のキーワードリスト（日本・米国系）を内蔵。
    - OpenAI 呼び出しは JSON モードで結果を期待、複数エラーケース（RateLimit, APIConnectionError, APITimeoutError, 5xx 等）に対してリトライとフォールバック（macro_sentiment=0.0）を実装。
    - レジームスコア計算はクリップして閾値判定（_BULL_THRESHOLD/_BEAR_THRESHOLD）を行う。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等操作。書き込み失敗時は ROLLBACK を試行し例外を伝播。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX 市場カレンダーを管理するユーティリティを実装。
    - 営業日判定・次/前営業日取得・期間内営業日リスト取得・SQ判定等の API を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合は曜日ベース（土日を非営業日）でフォールバックする設計。
    - calendar_update_job: J-Quants から差分を取得して market_calendar を更新する夜間バッチ処理を実装。バックフィルや健全性チェックを含む。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを実装し、ETL 実行結果・品質チェック結果・エラー一覧などを管理可能にした。
    - 差分更新・バックフィル・品質チェック・idempotent 保存（jquants_client の save_* を想定）を行う設計（実装のためのユーティリティを用意）。
    - 内部ユーティリティ: テーブル存在チェック、各テーブルの最大日付取得、トレーディングデイ補正などを実装。
    - etl モジュールは ETLResult を再エクスポート（kabusys.data.etl）。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン / MA200 乖離）、Volatility（20日 ATR, 相対 ATR, 平均売買代金, 出来高比率）、Value（PER, ROE）を DuckDB の prices_daily / raw_financials から計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 入力は DuckDB 接続のみ。外部 API へはアクセスしない想定。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターンの計算（calc_forward_returns、horizons の検証と安全な SQL 生成）。
    - IC（Information Coefficient）計算（Spearman のランク相関を実装、calc_ic）。
    - ランク関数（同順位は平均ランク）、統計サマリー（count/mean/std/min/max/median）を実装（rank, factor_summary）。
  - 研究ユーティリティのエクスポートを __init__ でまとめて公開（zscore_normalize を含む）。

- DuckDB を第一選択のローカル DB として利用する設計を明示。多くの関数は DuckDB 接続を引数に取り SQL と Python の組合せで処理を行う。

### Changed
- （初版につき変更履歴なし）

### Fixed
- （初版につき修正履歴なし）

### Deprecated
- （初版につき無し）

### Removed
- （初版につき無し）

### Security
- 環境変数の必須項目（OpenAI / J-Quants / Slack / kabu API パスワード等）が未設定の場合は明示的にエラーまたは例外を出す設計。`.env.example` を作成しての利用を想定。
- .env 読み込み時に OS 環境変数を保護するため、既存の OS 環境変数は上書きされない（ただし .env.local は override=True で上書き可、保護対象キーは OS 環境変数のスナップショットにより除外される）。

### Known issues / Limitations
- 日時はモジュール内で timezone-aware な datetime を使わず、UTC-naive / date オブジェクトを前提としている箇所あり。JST ↔ UTC の変換ロジックは明示的に行っているが、タイムゾーン混在に注意が必要。
- 一部ファクター（PBR・配当利回り）は未実装（calc_value の将来拡張対象）。
- OpenAI 呼び出しでの JSON パースに失敗するケースはフェイルセーフでスコア 0.0（またはチャンクスキップ）にフォールバックする設計。運用時はログで詳細を確認すること。
- DuckDB の executemany に空リストを渡すとエラーとなるため、空チェックや個別 DELETE を行う実装上の制約がある。DuckDB のバージョン互換性に依存する部分がある。

### Upgrade notes
- 環境変数読み込み: 自動ロードを無効化したい CI/テスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- AI 機能を利用するには `OPENAI_API_KEY` を環境変数に設定するか、関数の api_key 引数にキーを渡してください。
- ETL / calendar のバッチ処理を利用する場合は DuckDB に必要なテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）を用意してください（テーブルスキーマはドキュメント参照を想定）。

---

（補足）この CHANGELOG はコードベースから推測して作成しています。実際の運用上の仕様や追加の変更点がある場合は、適宜更新してください。