# CHANGELOG

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の様式に準拠しています。  
リリース日は YYYY-MM-DD 形式で記載しています。

## [Unreleased]
- 継続中の作業や次バージョンでの予定事項はここに記載します。

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買プラットフォームのコアライブラリを追加しました。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを作成し、バージョンを 0.1.0 に設定。
  - __all__ に data, strategy, execution, monitoring を定義（各サブパッケージの公開を意図）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env の行パーサーを実装:
    - コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - .env 読み込み時の上書き制御（override と protected キーの概念）。
  - Settings クラスを提供し、主要設定値をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV (development/paper_trading/live 検証)
    - LOG_LEVEL（検証あり）
    - is_live / is_paper / is_dev ヘルパー

- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約して銘柄ごとのニューステキストを作成。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で提供。
    - OpenAI（gpt-4o-mini）を使ったバッチセンチメント評価を実装（_BATCH_SIZE=20）。
    - レスポンスのバリデーションとスコアクリップ（±1.0）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
    - スコア取得後、ai_scores テーブルへ「DELETE → INSERT」の冪等書き込みを行う（部分失敗時に他コードの既存スコアを保護）。
    - テスト容易性のため、内部 OpenAI 呼び出し関数を差し替え可能。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で market_regime を決定。
    - OpenAI 呼び出しは retries を実装し、API 失敗時は macro_sentiment=0.0 としてフェイルセーフで継続。
    - データ不足時や異常系に対するログ出力と安全策（例: ma200_ratio の不足時には中立 1.0 を返す）。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar に基づく営業日判定およびユーティリティ関数を提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 未取得時は曜日ベース（平日のみ営業日）でフォールバックする堅牢な設計。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を更新（バックフィル、健全性チェック含む）。
    - 最大探索日数 (_MAX_SEARCH_DAYS) 等の安全ガードを実装。
  - ETL / パイプライン (kabusys.data.pipeline / etl)
    - ETLResult データクラスを追加（ETL 実行結果の集約・シリアライズ機能含む）。
    - 差分更新・バックフィル・品質チェックの設計方針を実装に反映（jquants_client を利用した取得 / 保存、quality モジュールによるチェック）。
    - _table_exists / _get_max_date 等のヘルパーを実装。
    - kabusys.data.etl で ETLResult を再エクスポート。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev を計算。データ不足時には None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を計算（EPS が 0/欠損時は None）。
    - すべて DuckDB SQL を駆使して高速に集計。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: Spearman ランク相関（IC）を実装。十分なデータがない場合は None。
    - rank: 同順位は平均ランクで処理（丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median といった基本統計量を算出。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- AI 機能を利用するためには OPENAI_API_KEY が必要。未設定時は明示的に ValueError を送出して使用者に通知。
- 環境変数の自動ロードはデフォルトで有効だが、明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### 既知の注意点 / 設計上の決定
- ルックアヘッドバイアス防止:
  - ai/news_nlp, ai/regime_detector, research.* では datetime.today()/date.today() を参照せず、すべて引数の target_date を基準に計算します。
- フェイルセーフ挙動:
  - OpenAI API 失敗時は例外を上位に上げず、0 や空スコアを使って処理を継続する設計の箇所が多くあります（サービスのロバスト性重視）。
- DuckDB 前提:
  - 多くの処理が DuckDB 接続を前提に SQL を実行します。DuckDB のバージョン差異（executemany の空リスト扱い等）を意識した防御実装あり。
- テスト支援:
  - OpenAI 呼び出しを容易にモックできる内部関数（_call_openai_api）を提供。

### 破壊的変更 (Breaking Changes)
- 初回リリースのため該当なし。

### マイグレーション / 移行ガイド
- 初回リリースのため該当なし。セットアップ時は .env（例: .env.example）を用意し、必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY など）を設定してください。

---
このCHANGELOGはコードの実装と設計コメントから推測して作成しています。実際のリリースノート作成時には、変更差分やコミットログに基づいて必要に応じて追記・修正してください。