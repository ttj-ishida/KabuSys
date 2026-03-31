CHANGELOG
=========

この変更履歴は「Keep a Changelog」形式に準拠しています。  
リリース日はコードベースの最終更新（このファイル作成時点）を基準に推測しています。実際のリリース日・内容は適宜調整してください。

履歴
----

Unreleased
- なし

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージ公開用 __init__.py にて __version__ = "0.1.0" を定義。
  - export対象モジュール候補として "data", "strategy", "execution", "monitoring" を公開（strategy / execution / monitoring は今回のコードでは実体が含まれていないため将来的な追加想定）。
- 環境設定管理 (kabusys.config)
  - .env/.env.local ファイルまたは OS 環境変数から設定を自動ロードする機能を実装（プロジェクトルートは .git または pyproject.toml を基準に自動検出）。
  - 自動ロードを抑止する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
  - .env 行パーサ (_parse_env_line) の強化:
    - export PREFIX 対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い。
  - .env ロード時の保護機能: OS の既存環境変数を protected として上書き抑止、.env.local での上書きサポート。
  - Settings クラスを提供し、必須設定取得時のバリデーション（未設定時は ValueError を送出）。主な設定項目:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等のデフォルト
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値のチェック）
    - シンプルな is_live / is_paper / is_dev 判定プロパティ
- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp):
    - raw_news と news_symbols を用い、銘柄ごとにニュースを集約して OpenAI (gpt-4o-mini, JSON mode) へバッチ送信し ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄 / コール）、1 銘柄あたりの記事件数・文字数上限のトリム、レスポンスの厳密なバリデーション実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対するエクスポネンシャルバックオフと再試行。
    - レスポンスパース失敗や API エラーは例外を投げずにログ出力してスキップするフェイルセーフ設計。
    - 時間ウィンドウ計算 (calc_news_window) によるルックアヘッドバイアス排除（datetime.today を直接参照しない設計）。
    - DuckDB への書き込みは冪等（DELETE → INSERT、BEGIN/COMMIT）かつ部分失敗時に既存データを保護（書き込み対象コードで絞る）。
  - 市場レジーム判定 (kabusys.ai.regime_detector):
    - ETF 1321 の 200 日移動平均乖離 (重み 70%) とマクロニュースの LLM センチメント (重み 30%) を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出しのリトライ、API やパース失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - prices_daily / raw_news / market_regime テーブルを利用し、冪等書き込みを実施。
- Data モジュール (kabusys.data)
  - マーケットカレンダー管理 (calendar_management):
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日判定ユーティリティを実装。
    - market_calendar テーブルが未取得の場合の曜日ベースフォールバック、DB 登録値優先の一貫したロジック、最大探索日数制限で無限ループ防止。
    - JPX カレンダーを J-Quants API から差分取得する夜間バッチ (calendar_update_job) を実装（バックフィル・健全性チェック含む）。
  - ETL パイプライン (pipeline.py / etl.py):
    - ETLResult データクラスを定義し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を構造化して返却可能。
    - 差分更新・バックフィル・品質チェック（quality モジュール）を想定した設計。
    - _table_exists やその他 DuckDB ヘルパー関数を実装。
    - data.etl から ETLResult を再エクスポート。
  - jquants_client（参照）経由でのデータ保存処理を想定（実装本体は別モジュール 想定）。
- Research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB 上で SQL を駆使して各種ファクター（モメンタム、MA200乖離、ATR、流動性、PER・ROE 等）を算出。
    - データ不足時の None 扱い、結果は date/code を含む dict リストで返却。
  - feature_exploration:
    - calc_forward_returns（任意ホライズンでの将来リターン）、calc_ic（Spearman ランク相関による IC）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
- 汎用・運用上の配慮
  - DuckDB の executemany が空リストを受け付けない特性（DuckDB 0.10）を考慮したガード実装。
  - ロギング・警告を多用し問題発生時の観測性を確保。
  - LLM 呼び出しや日付処理でルックアヘッドバイアスを避ける設計方針を明示。

Security
- API キーやトークンなどの必須環境変数（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）は Settings で required として扱われ、未設定時は ValueError を送出。
- .env 自動ロード時に OS 環境変数が上書きされないよう保護（protected set）を行う。

Fixed
- 初期リリースのため該当なし。

Changed
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Deprecated
- 初期リリースのため該当なし。

Notes / Known issues
- 一部ファイルが参照する外部モジュール（例: kabusys.data.jquants_client, kabusys.data.quality や strategy/execution/monitoring の具象実装）は今回のコードスニペットに含まれていません。実行環境ではこれらの実装が必要です。
- pipeline.py の末尾に一部コード断片（_get_max_date 以降）が途中で切れている箇所が見られます。リポジトリの完全版で補完が必要です。
- OpenAI SDK の具体的バージョン差異により例外クラスや属性名（status_code 等）が変わる可能性があるため、実運用環境では SDK バージョン固定とテストを推奨します。
- news_nlp / regime_detector の LLM 呼び出しは JSON モードの厳密な出力を前提としているため、プロンプトやモデル挙動によるパースエラーに留意してください。パース失敗時は該当チャンクをスキップして継続する動作です。
- config の自動 .env ロードはプロジェクトルート検出に .git または pyproject.toml を使用します。パッケージ配布後や特殊な配置では期待通りに検出できない可能性があるため、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を使用し手動で設定を行ってください。

参考（簡易）
- 必須環境変数例:
  - OPENAI_API_KEY（AI 呼び出し時）
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD（kabu API）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知）
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db

もし詳細なリリース日付や未掲載のモジュール（jquants_client 等）について追加情報があれば、CHANGELOG を更新してより正確な履歴を作成します。