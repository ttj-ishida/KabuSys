# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-27

初回リリース。日本株のデータ収集・解析・研究・AIスコアリング・市場レジーム判定を行う自動売買／研究ユーティリティ群を提供します。

### 追加 (Added)

- パッケージ全体
  - kabusys パッケージ初期公開。
  - パッケージのエクスポート: data, strategy, execution, monitoring（src/kabusys/__init__.py）。

- 環境設定 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサーは export KEY=val 形式、クォート内のエスケープ、コメント処理に対応。
  - 必須環境変数の取得ヘルパー _require。
  - Settings クラス（settings インスタンス）を公開。主なプロパティ:
    - jquants_refresh_token (JQUANTS_REFRESH_TOKEN)（必須）
    - kabu_api_password (KABU_API_PASSWORD)（必須）
    - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
    - slack_bot_token (SLACK_BOT_TOKEN)（必須）
    - slack_channel_id (SLACK_CHANNEL_ID)（必須）
    - duckdb_path (DUCKDB_PATH, デフォルト: data/kabusys.duckdb)
    - sqlite_path (SQLITE_PATH, デフォルト: data/monitoring.db)
    - env (KABUSYS_ENV, 値検証: development / paper_trading / live)
    - log_level (LOG_LEVEL, 値検証: DEBUG/INFO/WARNING/ERROR/CRITICAL)
    - is_live / is_paper / is_dev ブール判定

- AI モジュール (src/kabusys/ai/)
  - news_nlp (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）を用いてセンチメント（-1.0〜1.0）を算出。
    - ニュース対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）。
    - バッチ処理: 最大 20 銘柄／API 呼び出し、1 銘柄あたり最大 10 記事、最大 3000 文字にトリム。
    - JSON Mode を使った厳密な JSON 出力を期待し、レスポンス検証と部分失敗時のフェイルセーフ処理を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ。
    - ai_scores テーブルへ idempotent（DELETE→INSERT）で書き込み。部分失敗時に既存スコアを保護。
    - テスト容易性のため api_key 注入と _call_openai_api のモック差替えを想定。
    - 公開関数: score_news(conn, target_date, api_key=None)、calc_news_window(target_date)。
  - regime_detector (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロ要因はニュースタイトルをマクロキーワードでフィルタして LLM（gpt-4o-mini）で評価。記事が無い場合は LLM 呼び出しをスキップ。
    - レジームスコアの合成式と閾値を実装（クリップ、ラベリング）。
    - market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時はロールバック。
    - API エラー時のフォールバック: macro_sentiment = 0.0（警告ログを出力して継続）。
    - 公開関数: score_regime(conn, target_date, api_key=None)。

- データモジュール (src/kabusys/data/)
  - calendar_management (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを用いた営業日判定ロジックを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB に登録がない日については曜日ベース（平日＝営業日）でのフォールバックを実装。
    - calendar_update_job により J-Quants API から差分取得・バックフィル（_BACKFILL_DAYS）・オンコンフリクト保存を行う。健全性チェックあり。
  - ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult dataclass を定義（target_date, fetched/saved counts, quality_issues, errors 等）。
    - 差分更新、backfill、品質チェック（quality モジュール）を想定した設計。
    - DuckDB を想定したテーブル存在チェック・最大日付取得ユーティリティを提供。
    - etl モジュールの ETLResult を data.etl から再エクスポート。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research (src/kabusys/research/factor_research.py)
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB SQL ベースで計算する関数を実装:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - 設計上、prices_daily / raw_financials のみ参照し、外部 API にはアクセスしない。
  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - IC はスピアマンの ρ をランクベースで算出。
    - pandas 等に依存せず純 Python / DuckDB で実装。

- 共通設計方針（全体にわたる注意点）
  - ルックアヘッドバイアス回避: 各処理は datetime.today() / date.today() を内部で参照せず、明示的な target_date を用いる。
  - DuckDB をメインの分析 DB として想定（接続オブジェクトを全関数で受け取る）。
  - OpenAI 呼び出しはモデル gpt-4o-mini を想定し、JSON Mode を利用して厳密な構造を期待。
  - API 呼び出しは適切なリトライ戦略（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を実装。
  - レスポンス検証、スコアのクリッピング、部分失敗時の DB 保護（コード絞り込み）等の堅牢性対策を実施。
  - テスト容易性のため API 呼び出し関数の差し替え（patch）を想定した実装。

### 変更 (Changed)

- 初版のため該当なし。

### 修正 (Fixed)

- 初版のため該当なし。

### 非推奨 (Deprecated)

- 初版のため該当なし。

### 削除 (Removed)

- 初版のため該当なし。

### セキュリティ (Security)

- 初版のため該当なし。ただし、必須の API キー／トークンは環境変数で管理する前提です。

## 互換性 / 注意事項

- 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings のプロパティ参照）。
- OpenAI API を利用する機能（news_nlp, regime_detector）は OPENAI_API_KEY の設定または関数呼び出し時に api_key を明示する必要があります。
- DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取る設計のため、呼び出し側で適切に接続を準備してください。
- news_nlp / regime_detector の OpenAI 呼び出しは外部ネットワークを行うため、テスト時は _call_openai_api をモックしての検証を推奨します。
- カレンダー更新ジョブは jquants_client（data.jquants_client）実装を必要とします。API 例外発生時はログ出力の上、処理は安全に 0 を返します。

--- 

(本 CHANGELOG はソースコードから推測して作成した初期の変更履歴です。実際のリリースノートは運用に合わせて適宜更新してください。)