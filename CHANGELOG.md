CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
変更の重大度は Semantic Versioning に準拠しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-31
-----------------

Added
- パッケージ初版リリース (kabusys v0.1.0)
  - パッケージ公開のための基本モジュール群を実装。
  - パッケージメタ情報: __version__ = "0.1.0"、公開APIとして data / strategy / execution / monitoring を __all__ に設定。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート探索: .git または pyproject.toml を基準に探索し、パッケージ配布後でも CWD に依存しない設計。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを考慮）。
  - _load_env_file による上書きポリシー（override / protected）をサポートし、OS 環境変数を保護。
  - Settings クラスを提供し、アプリケーションで利用する主要設定プロパティを定義:
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / KABU_API_BASE_URL
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID
    - DUCKDB_PATH / SQLITE_PATH（Path 型で返却）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（許容値の検証）
    - is_live / is_paper / is_dev のユーティリティプロパティ
  - 必須環境変数未設定時は ValueError を投げる _require を実装。

- ニュース NLP & レジーム判定（kabusys.ai の実装）
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、銘柄ごとに記事を結合して OpenAI（gpt-4o-mini）にバッチ送信してセンチメント（-1.0～1.0）を取得。
    - バッチサイズ、記事数・文字数上限、JSON Mode を使ったレスポンス検証、JSON の前後余計テキストの復元ロジックを実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、その他エラーはスキップして継続するフェイルセーフ動作。
    - スコアは ±1.0 にクリップし、取得成功銘柄のみ ai_scores テーブルへ置換（DELETE → INSERT）する冪等処理。
    - datetime.today()/date.today() を直接参照せず、target_date ベースでウィンドウ計算（ルックアヘッドバイアス防止）。
  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（news_nlp.calc_news_window を経由、重み 30%）を組み合わせて市場レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出しは独立実装で、API キーは引数または環境変数 OPENAI_API_KEY から解決。
    - API 呼び出し失敗時のフォールバック（macro_sentiment=0.0）やリトライ処理を実装。
    - レジーム結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）し、DB 書き込み失敗時は ROLLBACK を試行して例外を伝播。

- 研究用モジュール（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー計算を実装。
    - calc_momentum: 1m/3m/6m リターン、200 日 MA 乖離（データ不足時は None）
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金・出来高比率
    - calc_value: raw_financials から直近財務データを引き、PER・ROE を計算
    - DuckDB を用いた SQL ベース実装、外部 API には依存しない
  - feature_exploration: 将来リターン計算、IC（スピアマンランク相関）、ファクター統計サマリー、ランク付けユーティリティを実装。
    - calc_forward_returns: 任意ホライズンの将来リターンをまとめて取得可能（入力検証あり）
    - calc_ic: factor_records と forward_records を code で結合して Spearman ρ を算出（有効レコード 3 未満は None を返す）
    - factor_summary: count/mean/std/min/max/median を算出
    - rank: 同順位は平均ランク化（丸めて ties 判定）

- データ基盤ユーティリティ（kabusys.data）
  - calendar_management
    - JPX カレンダーの管理機能（market_calendar テーブルの参照 / 更新用ロジック）を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - カレンダー未取得時は曜日ベースのフォールバックを利用し、一貫性を保つ設計。
    - calendar_update_job: J-Quants からの差分取得・バックフィル・健全性チェック・冪等保存の夜間バッチ処理を実装。
  - pipeline / etl
    - ETLResult dataclass を公開し、ETL の実行結果（取得件数・保存件数・品質問題・エラーなど）を構造化して返却。
    - 差分更新、バックフィル、品質チェックの方針を実装するための基盤を整備。
  - jquants_client との連携を想定した設計（fetch / save 系関数を利用）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 設計上の重要事項
- ルックアヘッドバイアス防止: AI スコアリング / レジーム判定 / ETL / 研究モジュールはすべて target_date ベースの時間ウィンドウを使用し、datetime.today()/date.today() を内部参照しない設計にしている。
- フェイルセーフ設計: OpenAI 呼び出しや外部 API の失敗は例外直轄で停止させるのではなく、フォールバック値（0.0）やスキップで継続させる実装が多く含まれる（ログ出力あり）。
- DuckDB 前提: データ処理は DuckDB 接続を受け取り SQL と最小限の Python ロジックで完結するよう設計している（外部依存を避ける）。
- テスト容易性: OpenAI 呼び出し関数はモジュール内で分離してあり unittest.mock.patch により差し替え可能。

開発者向け補足
- 環境変数読み込みの自動化はプロジェクトルート探索に依存するため、配布後に挙動を制御する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョン依存の注意点に対応するため、空チェックを行ってから executemany を呼び出しています。