# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

- 開発中・未リリースの変更点はここに記載します。

---

## [0.1.0] - 2026-03-31

初回公開リリース。

### 追加 (Added)
- パッケージ初期構成
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージの公開インターフェースに data, strategy, execution, monitoring を定義。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを追加。
    - プロジェクトルートは __file__ 起点で .git または pyproject.toml を探索して特定。
    - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き）。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサを実装（export 構文、クォート、エスケープ、行末コメント等に対応）。
  - Settings クラスを提供（プロパティ経由で設定値取得）。
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
    - 任意/デフォルト: KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）、DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）。
    - 環境 (KABUSYS_ENV) とログレベル (LOG_LEVEL) の入力検証（許容値をチェック）。
    - ヘルパープロパティ: is_live, is_paper, is_dev。

- データプラットフォーム関連 (src/kabusys/data/)
  - calendar_management モジュールを追加
    - JPX カレンダー管理（market_calendar）および営業日判定ロジックを提供。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB データがない場合は曜日ベースのフォールバック（週末を休場扱い）。
    - calendar_update_job を追加（J-Quants API から差分取得して冪等更新）。
    - バックフィル、先読み、健全性チェック（将来日付の異常検出）を実装。
  - pipeline / ETL モジュールを追加
    - ETLResult データクラスを公開（ターゲット日、取得/保存件数、品質問題リスト、エラーメッセージ等）。
    - 差分取得、バックフィル、品質チェックの設計方針を実装するためのユーティリティを含む（テーブル存在チェック、最大日付取得など）。
    - jquants_client および quality モジュールとの連携を想定。

- AI（NLP）モジュール (src/kabusys/ai/)
  - news_nlp モジュールを追加（score_news）
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメント評価。
    - 処理のポイント:
      - タイムウィンドウは JST ベースで定義（前日 15:00 ～ 当日 08:30 JST を UTC に変換して使用）。
      - 銘柄単位で記事を結合し文字数トリム（最大 _MAX_CHARS_PER_STOCK）。
      - バッチ処理（1 回の API 呼び出しで最大 _BATCH_SIZE 銘柄）。
      - レスポンスは JSON モードで受取る想定。レスポンスのバリデーションを厳格に行い、不正なレスポンスはスキップ。
      - 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。
      - スコアは ±1.0 でクリップ。
      - 書き込みは冪等（対象コードのみ DELETE → INSERT）で部分失敗時に既存データを保護。
      - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock.patch 想定）。
  - regime_detector モジュールを追加（score_regime）
    - ETF 1321（日経225 連動）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロニュースは news_nlp.calc_news_window を用いて取得し、OpenAI で JSON 応答から macro_sentiment を抽出。
    - LLM 呼び出しに対するリトライ・エラーハンドリングを実装。API 失敗時は macro_sentiment=0.0 でフォールバック。
    - DB への書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等化、失敗時は ROLLBACK を試行。
    - ルックアヘッドバイアス回避のため、datetime.today()／date.today() を参照しない設計（外部で target_date を渡す）。

- Research / 因子計算 (src/kabusys/research/)
  - factor_research モジュールを追加
    - calc_momentum, calc_volatility, calc_value を実装。
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ATR（20日）、20日平均売買代金・出来高比率、PER/ROE（raw_financials 参照）等を計算。
    - DuckDB のウィンドウ関数を活用した実装。
    - データ不足時には None を返す等、堅牢な挙動。
  - feature_exploration モジュールを追加
    - calc_forward_returns（複数ホライズンの将来リターン計算、horizons チェックあり）。
    - calc_ic（スピアマンランク相関による IC 計算、必要なレコード数チェック）。
    - rank（同順位は平均ランク処理）と factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず、標準ライブラリ＋DuckDB のみで実装。

- データユーティリティ
  - data.etl から ETLResult を再エクスポート。

### 変更 (Changed)
- （初回リリースのため「変更」はなし）

### 修正 (Fixed)
- （初回リリースのため「修正」はなし）

### 既知の設計上の注意点 / 動作仕様
- OpenAI API キーは関数引数（api_key）で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照し、未設定の場合は ValueError を送出する設計（明示的なエラー）。
- AI モジュールは外部 API の失敗に対してフェイルセーフを採用（多くのケースで 0.0 にフォールバックして処理継続）。
- .env の自動読み込みはプロジェクトルート検出に依存しており、パッケージ配布環境でも CWD に依存せず動作するよう配慮。
- DuckDB の executemany の空リストバインド（バージョン依存問題）を回避するため、空チェックを行ってから executemany を呼び出す実装になっている。
- テストのために _call_openai_api 等の内部関数を差し替え可能（mock を利用したテストを想定）。

### 破壊的変更 (Removed / Deprecated)
- 該当なし（初回リリース）

### セキュリティ (Security)
- 機密情報（API キー、パスワード等）は環境変数で管理する想定。Settings._require は未設定時に ValueError を送出して安全性を確保。
- .env 読み込み時に OS 環境変数を保護するため protected セットを使用して上書きを防止するロジックを実装。

---

変更やバグ修正、機能追加の提案や詳細なドキュメント化が必要であれば、どのモジュール／機能について深掘りすべきか指示してください。