# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システム "KabuSys" の基盤機能を実装しました。

### 追加（Added）
- パッケージ基本情報
  - pakage version を 0.1.0 として公開（src/kabusys/__init__.py）。
  - パッケージ公開 API に data / strategy / execution / monitoring を定義。

- 環境設定・自動 .env 読み込み（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。
  - export 付き行、シングル/ダブルクォート、エスケープ、インラインコメントなどに耐性のあるパーサを実装。
  - 読み込みの優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
  - Settings クラスを実装し、必要な設定 (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など) をプロパティ経由で取得・検証。
  - 環境 (development / paper_trading / live) とログレベルの検証ロジックを追加。
  - デフォルトのデータベースパス: DuckDB `data/kabusys.duckdb`, SQLite `data/monitoring.db`。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols から銘柄別にニュースを集約し、OpenAI (gpt-4o-mini) に JSON Mode で送信してセンチメント（-1.0〜1.0）を算出。
  - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算するユーティリティ calc_news_window を提供。
  - 1銘柄あたりのトークン肥大化対策（最大記事数・最大文字数トリム）を実装。
  - 銘柄を最大 20 件ずつバッチ処理（_BATCH_SIZE）。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ処理を実装。
  - レスポンス検証（JSON 抽出、"results" フォーマット検証、未知コードの無視、数値チェック）を実装し、結果を ai_scores テーブルに冪等的に書き込む（DELETE → INSERT）。
  - API 呼び出し箇所はテスト時に差し替え可能（_call_openai_api をパッチ可）。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF コード 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
  - マクロニュース抽出（キーワードリスト）・OpenAI 呼び出し（gpt-4o-mini）・リトライ・フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
  - 計算結果を market_regime テーブルへ冪等的に保存（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
  - LLM 呼出しは news_nlp と共有しない独立実装でモジュール結合を抑制。

- データ関連ユーティリティ（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定、next/prev/get_trading_days、is_sq_day を実装。
    - DB に値がない場合は曜日ベース（土日除外）のフォールバックを使用。
    - カレンダー更新ジョブ calendar_update_job を実装（J-Quants からの差分取得・バックフィル・健全性チェック・冪等保存）。
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを実装し、ETL の各段階（prices / financials / calendar）の取得・保存結果、品質検査結果、エラー集約を保持。
    - 差分更新のための最終取得日取得ユーティリティ、テーブル存在チェック、最大日付取得等を実装。
    - デフォルトのバックフィル日数・データ取得最小開始日等の定数を設定。
    - jquants_client と quality モジュールを連携する設計（実際の API 呼出しと保存処理は jquants_client 経由）。

- 研究（Research）用モジュール（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、流動性指標）、Value（PER, ROE）を DuckDB SQL ベースで実装。
    - データ不足時の None 返却、営業日スキャン用のバッファ等を考慮した設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズン）、IC（Spearman）計算 calc_ic、ランク変換 rank、ファクター統計 summary（factor_summary）を実装。
    - pandas 等外部依存を使わず標準ライブラリのみで実装。
  - zscore 正規化ユーティリティをデータモジュールから再利用できるように公開（research.__init__ で再エクスポート）。

### 変更（Changed）
- なし（初回リリースのため、新規実装のみ）。

### 修正（Fixed）
- なし（初回リリースのため、バグ修正履歴なし）。

### セキュリティ（Security）
- 環境変数の読み込みは OS 環境を保護するため .env の上書きを制御（protected set）しています。  
  自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。

### 備考（Notes）
- OpenAI API を使用する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）を必要とします。api_key 引数を各関数に渡すことで環境変数に依存せず動作させることができます。
- 多くの DB 書き込みは冪等化（DELETE→INSERT や ON CONFLICT 相当）とトランザクション（BEGIN/COMMIT/ROLLBACK）で保護されています。
- 研究用モジュールは外部の発注 API 等にはアクセスせず、DuckDB の prices_daily / raw_financials などの読み取りのみで完結します（本番口座への影響を与えません）。
- テスト容易性のため、OpenAI 呼び出し関数はモジュール内で明示的に分離され、unittest.mock.patch による差し替えがしやすく設計されています。

---

今後のリリースで以下を予定しています（例）:
- strategy / execution / monitoring の実装詳細公開
- jquants_client の具体実装と外部 API の差分取得処理の完成
- より詳細なエラーメトリクス・監視通知（Slack 連携強化）