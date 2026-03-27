KEEP A CHANGELOG 準拠 — 変更履歴 (日本語)

すべての重要な変更をこのファイルに記載します。
フォーマットは Keep a Changelog に従います。
リリース日はこのコードベース解析時点の日付を使用しています。

なお、本CHANGELOGはソースコードから推測して作成しています。挙動や仕様の詳細は実装を参照してください。

[Unreleased]
- 今後の変更点をここに記載します。

[0.1.0] - 2026-03-27
Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムの基盤機能を追加。
  - パッケージ公開情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - 公開モジュール: data, strategy, execution, monitoring を __all__ に設定。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パーサ実装: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - 読み込み優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - Settings クラスを提供し、以下の環境変数をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV (validation: development/paper_trading/live), LOG_LEVEL (validation: DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - is_live / is_paper / is_dev ヘルパーを提供。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメントを取得して ai_scores テーブルへ保存する処理を実装。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの最大記事数と文字数トリム、JSON レスポンス検証、スコアクリップ（±1.0）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ・リトライ。
    - API キー注入（引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出。
    - ルックアヘッドバイアス対策: datetime.today()/date.today() を参照せず、target_date ベースでウィンドウ計算（calc_news_window）を行う。
    - 公開 API: score_news(conn, target_date, api_key=None)。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（LLM、重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - 1321 のデータ欠損やデータ不足時のフォールバック、中立値 (ma200_ratio=1.0) の扱い。
    - マクロニュースのフィルタリング（マクロキーワード集合）と LLM 呼び出し（gpt-4o-mini）での JSON パース・リトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）。
    - レジーム結果を market_regime テーブルへ冪等 (BEGIN / DELETE / INSERT / COMMIT) に書き込み。
    - 公開 API: score_regime(conn, target_date, api_key=None)。

- データプラットフォーム (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルの有無に応じた営業日判定ロジックを追加。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等のユーティリティ関数を実装。
    - J-Quants クライアントを用いる夜間バッチ更新 calendar_update_job を実装（差分取得、バックフィル、健全性チェック、保存）。
    - DB 未登録日は曜日ベースでフォールバックする一貫した挙動を採用。探索上限日数 (_MAX_SEARCH_DAYS) を設定して無限ループを防止。

  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - 差分取得→保存→品質チェックの ETL フローを想定したユーティリティ群を実装（J-Quants からの差分取得、jq.save_* による冪等保存、quality モジュールによる品質チェック）。
    - ETLResult データクラスを提供し、取得数/保存数/品質問題/エラーを集約、has_errors / has_quality_errors / to_dict を実装。
    - ETLResult を etl モジュールで再エクスポート。

  - 内部ユーティリティ: DuckDB テーブル/最大日付取得等のヘルパーを実装。

- リサーチモジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum: 1M/3M/6M リターン算出、200 日移動平均乖離 (ma200_dev)。データ不足時の None 扱い。
    - Volatility / Liquidity: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を算出。
    - Value: raw_financials から最新財務データを取得し PER / ROE を計算。EPS が 0/欠損時の処理。
    - DuckDB を用いた SQL ベース実装。date, code をキーとする dict のリストを返す。

  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（任意ホライズン、入力検証、LEAD を用いた一括取得）。
    - IC（Information Coefficient）計算 calc_ic：Spearman ランク相関を実装（ties の平均ランク処理を含む）。有効レコード数が少ない場合は None。
    - rank、factor_summary（count/mean/std/min/max/median）などの統計ユーティリティを実装。
    - pandas 等外部ライブラリに依存しない実装方針。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

設計上の注記（主な決定事項・安全策）
- ルックアヘッドバイアスの防止: すべての分析/スコアリング関数は target_date に基づきデータを取得し、内部で datetime.today()/date.today() を参照しない設計。
- DuckDB を主要なローカル分析 DB として使用。SQL と組み合わせて高性能な集計を行う。
- 外部 API（OpenAI / J-Quants）呼び出しは堅牢化（リトライ、指数バックオフ、5xx 判定、フェイルセーフのデフォルト値）を実装。
- DB への書き込みは可能な限り冪等に実装（DELETE→INSERT、ON CONFLICT 等）し、部分失敗時に既存データを不要に消さない工夫を行う。
- テスト容易性のため、OpenAI 呼び出し部分はモック差し替えを想定できる実装（モジュール内の _call_openai_api 関数を patch 可能）。

開発者・貢献者
- 初版（0.1.0）リリース

補足
- 本CHANGELOGは提供されたソースコードから機能・設計を推測して作成しています。追加の変更やリリースノートを付与する場合は、実際のコミット履歴やリリース日を基に更新してください。