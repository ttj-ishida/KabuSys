# Changelog

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

なお、この CHANGELOG はソースコード（src/kabusys 以下）から機能・動作を推測して作成しています。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-31

### 追加 (Added)
- パッケージ初期リリース: kabusys
  - パッケージメタ情報（src/kabusys/__init__.py）で __version__ = "0.1.0" を公開。
  - public API として data, strategy, execution, monitoring を想定したモジュール構成を宣言。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数の自動読み込みを実装（プロジェクトルート判定は .git / pyproject.toml）。
  - .env, .env.local の読み込み優先順位をサポート（OS 環境変数の保護および override 制御）。
  - export 形式、クォート・エスケープ、インラインコメントなどを考慮した .env パーサ実装。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
  - 必須環境変数取得ヘルパー _require を提供（未設定時は ValueError）。
  - 各種設定プロパティを持つ Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境・ログレベル判定など）。
  - DUCKDB_PATH / SQLITE_PATH のデフォルトパスを設定。

- データ関連モジュール (src/kabusys/data/)
  - ETL パイプラインインターフェース（ETLResult の公開 / pipeline モジュール）を実装。
    - ETLResult に ETL 実行メタ情報、品質チェック結果、エラー一覧を格納する dataclass を追加。
  - ETL 実装（src/kabusys/data/pipeline.py）
    - 差分取得、バックフィル、品質チェックとの連携を想定した設計。
    - DuckDB を用いた最終日付取得などユーティリティを実装。
    - J-Quants クライアント（jquants_client）と quality モジュールを呼び出す想定。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルに基づく営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - カレンダーの夜間差分更新ジョブ calendar_update_job を実装（J-Quants から差分取得 → 冪等保存）。
    - DB 未取得時の曜日ベースフォールバック、バックフィル、健全性チェック（未来日過大検出）など堅牢化ロジックを実装。

- 研究用モジュール (src/kabusys/research/)
  - factor_research モジュール: Momentum / Volatility / Value 等の定量ファクター計算機能を実装（calc_momentum, calc_volatility, calc_value）。
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離率を計算（データ不足時は None）。
    - Volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比などを計算。
    - Value: raw_financials から最新財務を取得して PER / ROE を計算。
  - feature_exploration モジュール:
    - 将来リターン計算 calc_forward_returns（任意ホライズン、バリデーションあり）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンの順位相関）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）。
    - ランク関数 rank（同順位は平均ランクで処理、丸めにより ties の検出を安定化）。
  - 研究ユーティリティを再エクスポートする __init__ を提供（zscore_normalize 等を含む）。

- AI / NLP モジュール (src/kabusys/ai/)
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して ai_scores テーブルへ書き込み。
    - チャンク処理（最大 20 銘柄 / チャンク）、1銘柄あたりの最大記事数と最大文字数でトリム。
    - レスポンスの厳密なバリデーション（JSON パース復元ロジック、results の構造検査、コード照合、数値検証）。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。非リトライエラーはスキップして継続（フェイルセーフ）。
    - DuckDB への書き込みは部分成功を考慮し、対象コードのみ DELETE → INSERT で置換（冪等）。
    - 時間ウィンドウ calc_news_window（前日 15:00 JST ～ 当日 08:30 JST を UTC 変換）を提供。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロキーワードによる raw_news 抽出、LLM（gpt-4o-mini）呼び出し、応答の JSON パース、リトライとフェイルセーフ（API 失敗時 macro_sentiment=0.0）。
    - レジームスコアのクリップ・閾値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - datetime.today()/date.today() の直接参照を避け、ルックアヘッドバイアス対策を実装。

- 外部依存・実行ランタイム
  - DuckDB を主要な組み込み DB として利用する設計。
  - OpenAI SDK（chat completions）の利用を想定（JSON mode を利用）。
  - J-Quants API / kabuステーション / Slack の設定項目を Settings で管理（必要な環境変数名を定義）。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### 破壊的変更 (Removed / Deprecated)
- 初期リリースのため該当なし。

### ドキュメント / 設定に関する注意
- OpenAI API キーは引数（api_key）で注入可能。引数未指定時は環境変数 OPENAI_API_KEY を参照する。未設定だと ValueError を送出。
- KABUSYS_ENV の許容値は development / paper_trading / live のみ。LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容。
- .env 自動読み込みはプロジェクトルートが特定できない場合はスキップされる。自動ロードを無効化する際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用。

---

この CHANGELOG はソースコードからの推測に基づいて作成しています。実際のリリースノート用途では、リリース日付や変更点の確定情報をプロジェクトのリリースプロセスに合わせて更新してください。