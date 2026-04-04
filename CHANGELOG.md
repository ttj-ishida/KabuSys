# CHANGELOG

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
このリポジトリは最初のパブリックリリースとしてバージョン 0.1.0 を公開します。

## [0.1.0] - 2026-04-04

### 追加 (Added)
- パッケージ基盤
  - 初期パッケージ公開。トップレベルパッケージ名は `kabusys`、バージョン `0.1.0` を設定。
  - パッケージの公開 API としてモジュール群を __all__ に定義（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートの自動検出機能を追加（.git または pyproject.toml を基準）。これにより CWD に依存せずパッケージ配布後も .env 自動ロードが機能。
  - .env パーサ実装（export プレフィックス対応、単/ダブルクォート処理、バックスラッシュエスケープ、行内コメントの取り扱い等）。
  - .env の読み込み優先順位: OS 環境変数 > .env.local > .env。既存 OS 環境変数を保護するため protected セットを使用して上書きを制御。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化できる機能を追加（テスト向け）。
  - 設定アクセス用 `Settings` クラスを提供。J-Quants / kabu / LINE / DB パス / 監視閾値 / 環境設定（env, log_level）などのプロパティを定義し、未設定時の検証やデフォルトを提供。
  - `Settings.env` と `Settings.log_level` に入力検証を実装（許容値チェック、無効値で ValueError を送出）。

- AI（自然言語処理）機能 (src/kabusys/ai)
  - ニュースセンチメントスコアリング: `score_news(conn, target_date, api_key=None)` を実装（src/kabusys/ai/news_nlp.py）。
    - タイムウィンドウ定義（前日 15:00 JST 〜 当日 08:30 JST）とその UTC 変換ユーティリティ `calc_news_window` を実装。
    - raw_news と news_symbols を結合して銘柄毎に記事を集約する `_fetch_articles`。
    - OpenAI（gpt-4o-mini）の JSON モードを用いたバッチ評価（1 API 呼び出しで最大 20 銘柄）。
    - チャンク単位のリトライ（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）、レスポンスの厳密なバリデーション（JSON 抽出、results 配列、コード照合、数値検証）、スコアの ±1.0 クリッピング。
    - DuckDB への冪等書き込み（対象コードのみ DELETE → INSERT）をサポートし、部分失敗時に他コードの既存スコアを保護。
    - API キー解決（引数優先、未指定時は環境変数 OPENAI_API_KEY を参照）、未設定時は ValueError を送出。
  - 市場レジーム判定: `score_regime(conn, target_date, api_key=None)` を実装（src/kabusys/ai/regime_detector.py）。
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを重み付け（MA 70% / マクロ 30%）してレジーム（bull / neutral / bear）を日次で判定。
    - MA 計算はルックアヘッドバイアスを防ぐため target_date 未満のデータのみ使用。データ不足時は中立値を採用。
    - マクロニュースは `news_nlp.calc_news_window` を用いて取得、LLM コールは最大リトライ、失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - レジームスコアの合成、閾値判定、DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）とロールバックの保護ログ。

- リサーチ（ファクター計算・特徴量探索） (src/kabusys/research)
  - ファクター計算群（src/kabusys/research/factor_research.py）を追加:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）計算。データ不足は None を返す。
    - calc_volatility(conn, target_date): 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0/欠損時は None）。
    - 各関数は DuckDB の SQL ウィンドウ関数を活用し、(date, code) ベースの辞書リストを返却。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py) を追加:
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズンの将来リターン（LEAD を利用）。horizons の検証あり。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）計算。必要な検証（有効レコード数 >= 3）。
    - rank(values): 同順位は平均ランクとするランク付けユーティリティ（丸めによる ties 検出対策あり）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリー。
  - research パッケージの __init__ で便利な関数を再エクスポート（zscore_normalize など外部ユーティリティを含む）。

- データプラットフォーム（DuckDB ベース ETL / カレンダー） (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py):
    - 営業日判定ユーティリティ群を実装: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバックする一貫した挙動を実装。
    - 最大探索日数で無限ループを防ぐ設計（_MAX_SEARCH_DAYS）。
    - calendar_update_job: J-Quants API からカレンダーを差分取得し冪等保存。バックフィル（日数）と健全性チェック（過度に未来の日付が見つかった場合はスキップ）を実装。
  - ETL パイプライン (src/kabusys/data/pipeline.py / etl.py):
    - ETLResult dataclass を追加して ETL 実行結果（取得件数・保存件数・品質問題・エラー）を構造化。
    - ETL モジュールの設計方針として差分更新、バックフィル、品質チェック収集（Fail-Fast ではなく全件収集）を採用。
    - _table_exists / _get_max_date などの内部ユーティリティを実装。
    - data.etl で `ETLResult` を再エクスポート。

- モジュールのエクスポート
  - ai モジュールの __init__ で `score_news` を公開。
  - research モジュールの __init__ で主要関数を公開。
  - data.etl で ETLResult を公開。

### 変更 (Changed)
- なし（初回リリース）。

### 修正 (Fixed)
- なし（初回リリース）。

### 内部仕様／設計上の重要ポイント（ドキュメント的注記）
- ルックアヘッドバイアス対策: AI/リサーチ/ETL の主要関数は datetime.today() / date.today() を内部参照しない設計。すべて明示的な target_date を受け取り、その日時以前のデータのみを参照するように実装。
- OpenAI 呼び出しに関する堅牢性: 429 / ネットワーク断 / タイムアウト / 5xx に対する再試行（指数バックオフ）と、サーバーエラー以外は即スキップするフェイルセーフ動作を採用。API レスポンスのパース失敗時は無害なデフォルト値（0.0）やスキップを行い、システム全体を停止させないようにしている。
- DuckDB への書き込みは可能な限り冪等に設計（DELETE → INSERT、ON CONFLICT を想定した保存関数の利用）。書き込み中の例外時は明示的に ROLLBACK を試み、失敗時は警告ログを出力。
- .env 読み込み時に OS 環境変数を保護（protected set）し、.env/.env.local の上書き制御を行うことでローカルファイルによる本番環境変数の誤上書きを防止。

### 既知の制約 / 注意点
- OpenAI API 依存: AI 機能は OpenAI（gpt-4o-mini）に依存しており、API キー（OPENAI_API_KEY）が必要。api_key を直接関数引数で渡すことも可能。
- DuckDB バージョン差異: 一部の executemany / リストバインドの挙動を回避するために明示的なループ / executemany の使い分けをしている。環境によっては DuckDB のバージョン互換性に注意。
- News NLP の出力は JSON モード前提だが、稀に余計なテキストが混ざるケースを考慮して最外の JSON オブジェクト抽出ロジックを備えている。

---

今後のリリース予定（例）
- strategy / execution / monitoring モジュールの実装拡充（現在はパッケージ構成のみ）。  
- ETL の実行スケジューラ、モニタリングのアラート連携（LINE 等）や実運用向けの監視強化。