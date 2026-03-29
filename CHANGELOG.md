# Changelog

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

リリース日付はコードベースの現状から推定しています。

## [0.1.0] - 2026-03-29

### Added
- パッケージ初版の公開。
- 基本パッケージ構成を追加:
  - kabusys パッケージのエントリポイント（version: 0.1.0）。
  - サブパッケージ: data, research, ai, monitoring, strategy, execution（`__all__` に公開）。
- 環境変数 / 設定管理（kabusys.config）:
  - .env ファイル（`.env` / `.env.local`）と OS 環境変数を組み合わせた自動読み込み機能を実装。
  - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - プロジェクトルート検出は `.git` または `pyproject.toml` を基準に探索（CWD 非依存）。
  - .env パーサーはコメント・export フォーマット・シングル/ダブルクォート・バックスラッシュエスケープに対応。
  - OS 環境変数を保護するための上書き制御（protected keys）を導入。
  - 必須環境変数取得用ユーティリティ `_require` と、Settings クラスを提供（主要プロパティ例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV、LOG_LEVEL）。
  - `env` 値や `log_level` のバリデーション（許容値チェック）を実装。
- AI 関連（kabusys.ai）:
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）:
    - raw_news + news_symbols を集約して銘柄ごとのニューステキストを生成し、OpenAI（gpt-4o-mini）のJSONモードでバッチ評価。
    - バッチ処理（最大20銘柄/チャンク）、記事数や文字数制限（最大記事数、文字トリム）を実装。
    - 再試行（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフを実装。
    - レスポンスのバリデーションとスコアクリッピング（±1.0）。
    - DuckDB への冪等的書き込み（該当コードのみ DELETE → INSERT）を実施。
    - ユーティリティ: calc_news_window(target_date)、score_news(conn, target_date, api_key=None) を公開。
    - テスト時に内部 OpenAI 呼び出しを差し替え可能（関数単位で patch 可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321 の 200日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - マクロキーワードで raw_news をフィルタし、OpenAI（gpt-4o-mini）でセンチメントを取得、欠落時はフェイルセーフで 0.0 を使用。
    - API 再試行・バックオフと 5xx ハンドリング、JSON パース失敗のフォールバックを実装。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）する API: score_regime(conn, target_date, api_key=None) を提供。
- Data / ETL（kabusys.data）:
  - カレンダー管理（kabusys.data.calendar_management）:
    - JPX カレンダーを扱うためのユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未設定の場合は曜日ベースでフォールバック（週末を非営業日扱い）。
    - カレンダーの夜間バッチ更新 job: calendar_update_job(conn, lookahead_days=90)（J-Quants から差分取得し冪等保存）。
    - 最大探索日数制限や健全性チェック（未来日が極端に大きい場合はスキップ）を実装。
  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）:
    - ETLResult データクラスを公開（取得数、保存数、品質チェック結果、エラーの集約）。
    - 差分取得・バックフィルロジック、品質チェックの収集方針（重大な問題があっても ETL は継続し呼び出し元で対処）を実装。
    - テーブル最大日付取得などのヘルパー実装。
- Research（kabusys.research）:
  - ファクター計算（kabusys.research.factor_research）:
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日ATR・相対ATR・平均売買代金・出来高比率）、Value（PER, ROE）を DuckDB の prices_daily / raw_financials を参照して計算する関数を提供（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の扱い（None を返す）や、計算範囲の安全バッファを採用。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - 将来リターン計算（calc_forward_returns）: 複数ホライズンをまとめて取得、入力検証あり（horizons は正の整数、最大252）。
    - IC 計算（calc_ic）: スピアマンランク相関（ランクは平均ランク、ties の扱いを含む）。
    - ランク関数（rank）: 同順位は平均ランクで処理、丸めで ties の誤判定を防止。
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。
- 実装上の設計指針・安全装置:
  - ルックアヘッドバイアス対策として、すべての日次処理は明示的な target_date 引数を使用し、datetime.today() / date.today() 参照を最小化（ただし calendar_update_job はバッチで today を利用）。
  - OpenAI 呼び出しの失敗は多数の箇所でフォールバック（スコア 0.0 やスキップ）する方針を採用し、処理の継続性を確保。
  - DuckDB に対する executemany の制約（空リスト不可など）に配慮した書き込み方法を採用。
  - モジュール間の結合を抑えるために、OpenAI 呼び出しラッパー関数はモジュールごとに独立実装（テスト時に個別差し替え可能）。

### Changed
- (初回リリースのため該当なし)

### Fixed
- API 呼び出しや DB 書き込みでのフォールトトレランスを強化:
  - OpenAI API に対する再試行（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフを実装。最終失敗時に安全なデフォルト（例えば macro_sentiment=0.0）へフォールバック。
  - DB 書き込み時に例外が発生した場合は ROLLBACK を試行し、ROLLBACK 自体が失敗した場合は警告ログを出力して上位へ例外を伝播。
  - JSON パース失敗時の保護的処理（外側の {} を抽出して再パースする等）を導入して LLM レスポンスの変動に耐性を持たせた。

### Removed
- (初回リリースのため該当なし)

### Security
- OpenAI API キー（環境変数: OPENAI_API_KEY または各関数の api_key 引数）や各種トークン/パスワードは必須チェックを実装。未設定時は ValueError を投げ処理を中断する箇所あり（明示的なエラーメッセージを表示）。
- .env の取り扱いは OS 環境変数の上書きを保護する仕組みを用意。

### Breaking Changes
- (初回リリースのため該当なし)

---

注記:
- この CHANGELOG はリポジトリ内のソースコードとコメントから推測して作成しています。実際のリリースノートでは、変更の背景、既知の問題、利用方法（必須環境変数など）をドキュメントに追記することを推奨します。