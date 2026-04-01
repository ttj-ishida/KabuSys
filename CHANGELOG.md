# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このリポジトリの初期公開バージョンは 0.1.0 です。

---

## [Unreleased]
（未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-04-01

初期リリース。日本株自動売買 / データ基盤 / リサーチ / AI 補助機能の骨組みを実装しました。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" として公開。
  - パッケージの公開 API として data, strategy, execution, monitoring を __all__ に設定。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントなど多様な形式に対応。
  - 読み込み時に OS 環境変数を保護する（.env.local は上書き可能だが protected keys を尊重）。
  - Settings クラスを提供し、主要設定値をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - 監視用 PID ファイルパス / CPU・メモリ・ディスク閾値
    - KABUSYS_ENV（development / paper_trading / live の検証）と LOG_LEVEL（有効値チェック）
    - is_live / is_paper / is_dev のヘルパー

- AI: ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols から銘柄別に記事を集約して OpenAI（gpt-4o-mini、JSON Mode）でセンチメントを評価する score_news を実装。
  - JST 基準のニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を実装。
  - 1銘柄あたり最大記事数 (_MAX_ARTICLES_PER_STOCK)／最大文字数 (_MAX_CHARS_PER_STOCK) によるトリムをサポート。
  - バッチ処理（1回につき最大 _BATCH_SIZE 銘柄）・チャンクごとのリトライ（429・ネットワーク・タイムアウト・5xx は指数バックオフ）を実装。
  - レスポンスの厳格なバリデーション（JSON 抽出、results 配列、code の照合、数値チェック）とスコアの ±1.0 クリップ。
  - DuckDB への冪等書き込み（DELETE → INSERT）の処理を実装。部分失敗時に他銘柄データを残す設計。
  - テスト容易性のため、OpenAI 呼び出し箇所はパッチ可能（_call_openai_api をモック置換）。

- AI: 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で market_regime を算出する score_regime を実装。
  - news_nlp.calc_news_window を利用した期間フィルタ、LLM（gpt-4o-mini）呼び出し、リトライ、フェイルセーフ（API 失敗時に macro_sentiment=0.0）を実装。
  - レジーム合成ロジック（クリップ、閾値による bull/neutral/bear ラベリング）と market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - DuckDB クエリにおけるルックアヘッドバイアス回避（target_date 未満のみ参照）等の設計方針を明確化。

- リサーチ（factor / feature） (src/kabusys/research/)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を DuckDB SQL で計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務（EPS/ROE）を取得し PER/ROE を算出。
    - 全ての処理は prices_daily / raw_financials の参照のみで外部 API に依存しない。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を使って一括算出。
    - calc_ic: スピアマン相関（ランク相関）による IC 計算（同順位は平均ランクで処理）。
    - rank / factor_summary: ランク変換と基本統計量（count/mean/std/min/max/median）計算を実装。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB SQL で実装。

- データプラットフォーム (src/kabusys/data/)
  - calendar_management:
    - market_calendar に基づく営業日判定ロジック: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB にデータがない場合は曜日ベース（土日除外）のフォールバックを採用。
    - calendar_update_job: J-Quants API を使って差分取得 → market_calendar へ冪等保存。バックフィルと健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスで ETL 実行結果（取得数・保存数・品質問題・エラー）を集約。
    - ETL パイプライン設計方針（差分更新、バックフィル、品質チェックの収集と継続処理、id_token 注入でのテスト容易性）を実装。
  - data.etl は pipeline.ETLResult を再エクスポート。

- ロギング / フェイルセーフ設計
  - 多くのモジュールで詳細な logger 呼び出し（info/debug/warning/exception）を実装。
  - 外部 API 失敗時のフォールバック（例: macro_sentiment=0.0、空結果のスキップ）や ROLLBACK 保護を徹底。
  - ルックアヘッドバイアス対策: date.today()/datetime.today() の不適切使用を避け、API 呼び出しで target_date を明示する設計。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### 既知の注意点 / マイグレーション情報
- OpenAI API の使用:
  - score_news / score_regime は OPENAI_API_KEY 環境変数、または api_key 引数を必要とする。未設定時は ValueError を送出する。
  - 使用モデルは gpt-4o-mini。レスポンスは JSON Mode を想定しているが、前後ノイズ耐性もある程度実装済み。
- DuckDB テーブル期待:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等のスキーマが想定されている（ETL 側での保存処理を前提）。
- .env 自動ロード:
  - プロジェクトルート検出は __file__ の親ディレクトリを上向きに探索して .git または pyproject.toml を基準に行うため、配布後の挙動を考慮済み。
  - OS 環境変数を保護して .env の値が勝手に上書きされないようになっている。テスト等で自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- テストのしやすさ:
  - OpenAI 呼び出し関数（_call_openai_api）はテスト用に patch しやすい位置で実装されている（unittest.mock.patch 推奨）。

---

今後の予定（例）
- strategy / execution / monitoring の実装拡充（現状はモジュール参照のみ）
- DB スキーマ定義ファイル・初期化スクリプトの追加
- 単体テスト・統合テスト・CI 設定の追加
- メトリクス収集・アラート機能の強化

--- 

（注）この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートはリリース時の追加変更・ドキュメントに従って更新してください。