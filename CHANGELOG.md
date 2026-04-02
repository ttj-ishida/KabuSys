# Changelog

すべての注目すべき変更点を記録します。  
このファイルは「Keep a Changelog」フォーマットに準拠しています。セマンティックバージョニングを使用します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-02

初回リリース。本リリースでは日本株自動売買システムの基礎モジュール群を実装しています。主な機能、設計方針、注意点を以下に示します。

### 追加（Added）
- パッケージ基礎
  - パッケージ初期化: `kabusys.__init__` を追加し、バージョン `0.1.0` と公開サブパッケージ（data, strategy, execution, monitoring）を定義。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env 自動読み込み機能
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）に基づき `.env` と `.env.local` を読み込む。優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供（テスト用途）。
  - .env パーサの実装
    - 単一行パースでコメント、export 形式、シングル/ダブルクォート、エスケープ、インラインコメントを正しく処理。
  - Settings クラス
    - `settings` でアプリケーション設定を取得可能（J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境モードなど）。
    - 必須キー未定義時は `_require` が ValueError を送出。
    - `KABUSYS_ENV`（development, paper_trading, live）と `LOG_LEVEL`（DEBUG/INFO/...）の検証を実施。
    - デフォルトの DB パス等（例: `DUCKDB_PATH="data/kabusys.duckdb"`）を提供。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - ニュースセンチメント解析機能 `score_news(conn, target_date, api_key=None)` を追加。
    - 対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive に変換）。
    - raw_news と news_symbols を集約し、1 銘柄あたり最新記事を最大 N 件・最大文字数でトリム。
    - OpenAI（モデル: gpt-4o-mini, JSON Mode）へ最大 20 銘柄のチャンクで送信（_BATCH_SIZE=20）。
    - 再試行戦略: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ（最大リトライ回数指定）。
    - レスポンス検証: JSON パース、"results" リスト、各要素の "code" と "score"、コード整合性チェック、スコアの数値化・有限値判定。スコアは ±1.0 にクリップ。
    - DB 書き込みは部分失敗を考慮した冪等的な処理（対象コードのみ DELETE → INSERT）。DuckDB の executemany の制約に配慮。
    - API キーは引数優先、未設定時は環境変数 `OPENAI_API_KEY` を参照。未設定なら ValueError を送出。
    - テストフック: OpenAI への呼び出し関数 `_call_openai_api` をモック差し替え可能。

- AI 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - 市場レジーム算出 `score_regime(conn, target_date, api_key=None)` を追加。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成。
    - マクロニュースは `news_nlp.calc_news_window` で得られるウィンドウからマクロキーワードで抽出（最大 20 記事）。
    - LLM 呼び出しは gpt-4o-mini（JSON Mode）を利用。API エラー時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - レジームスコアは clip(-1..1)、閾値で 'bull' / 'neutral' / 'bear' ラベル判定。
    - 結果は `market_regime` テーブルに冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB エラー時に ROLLBACK を行い例外を伝播。

- データプラットフォーム：カレンダー管理（src/kabusys/data/calendar_management.py）
  - JPX カレンダー管理ユーティリティを提供。
    - 営業日判定 API: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`。
    - DB に calendar が存在しない場合は曜日ベース（土日除外）のフォールバック。
    - カレンダー更新バッチ `calendar_update_job(conn, lookahead_days=90)` を実装（J-Quants クライアント経由で差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索範囲やバックフィル / サニティチェック等の安全策を実装。

- ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
  - ETL の設計・ユーティリティを実装。
    - `ETLResult` データクラスを定義（取得件数、保存件数、品質問題、エラー一覧などを含む）。`to_dict()`、`has_errors`、`has_quality_errors` を提供。
    - 差分更新・バックフィル・品質チェックの方針を実装（jquants_client と quality モジュールを利用する想定）。
  - `kabusys.data.etl` で ETLResult を再エクスポート。

- 研究用ユーティリティ（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - `calc_momentum(conn, target_date)`：mom_1m / mom_3m / mom_6m / ma200_dev を計算。データ不足時は None を返す。
    - `calc_volatility(conn, target_date)`：20 日 ATR、相対 ATR、20 日平均売買代金、volume_ratio を計算。真の True Range 計算で NULL 伝播を制御。
    - `calc_value(conn, target_date)`：raw_financials から直近財務データを取得し PER / ROE を算出（EPS が 0/NULL の場合は None）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - `calc_forward_returns(conn, target_date, horizons=None)`：複数ホライズンの将来リターンを効率的に1クエリで取得。horizons のバリデーションあり。
    - `calc_ic(factor_records, forward_records, factor_col, return_col)`：Spearman のランク相関（IC）を計算。有効レコード数が不足すると None を返す。
    - `rank(values)`：同順位は平均ランクで処理（丸めによる tie 対策あり）。
    - `factor_summary(records, columns)`：count/mean/std/min/max/median を計算。
  - `research.__init__` で代表的関数を再エクスポート。

### 設計上の注記 / フェイルセーフ（主な設計方針）
- ルックアヘッドバイアス対策
  - どの AI / ETL / 研究処理も内部で `datetime.today()` や `date.today()` を直接参照しない設計。全て `target_date` を受け取り、DB クエリは排他的条件（date < target_date / date BETWEEN など）でルックアヘッドを防止。
- LLM 呼び出しの堅牢化
  - ネットワークエラーやレート制限、5xx に対する再試行（指数バックオフ）を実装。再試行後も失敗した場合は処理を継続（スコアは 0.0 または当該チャンクはスキップ）し、例外を極力上位に伝播させない。
  - OpenAI への呼び出しロジックはモジュール間で共有しない（各モジュールで別実装） → テスト時に個別モック可能。
- DB 書き込みの冪等性
  - `market_regime`, `ai_scores` などへの書き込みは DELETE → INSERT または ON CONFLICT 相当で上書きし、部分失敗時に他データを消さない工夫を実装。
- テスト容易性
  - OpenAI 呼び出しやファイル I/O 等は差し替え可能（内部関数をモック）でユニットテストを容易にする設計。
- DuckDB 前提
  - 多くの処理は DuckDB 接続と特定のテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など）を前提とする。

### 必要な環境変数（主なもの）
- OPENAI_API_KEY（AI 機能を使う場合）
- JQUANTS_REFRESH_TOKEN（J-Quants API 利用）
- KABU_API_PASSWORD, KABU_API_BASE_URL（kabuステーション API）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知）
- DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH（デフォルトパスは Settings に定義）
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

### 既知の制約 / 注意点
- OpenAI 呼び出しは gpt-4o-mini の JSON Mode を想定しているため、実行環境に応じた API バージョン互換性に注意。
- DuckDB のバージョン差分により一部プレースホルダの扱いが異なるため、executemany に空リストを渡さない等の回避策を講じている。
- 一部処理（calendar_update_job 等）は jquants_client の実装に依存する。J-Quants クライアント実装が必要。
- 一部 API キーが未設定だと ValueError を送出する箇所があり、呼び出し側でのハンドリングが必要。

### 変更（Changed）
- 初回リリースのため該当なし。

### 修正（Fixed）
- 初回リリースのため該当なし。

### セキュリティ（Security）
- 環境変数で機密情報（API キー等）を管理する設計。`.env` をリポジトリに含めない運用を推奨。
- 自動ロード機能は `KABUSYS_DISABLE_AUTO_ENV_LOAD` によりオフ可能。

---

以上が v0.1.0 の主要な変更点と設計上のポイントです。今後のリリースでは、戦略（strategy）や実運用の execution / monitoring 周りの実装、テストカバレッジ拡充、ドキュメント追記を予定しています。