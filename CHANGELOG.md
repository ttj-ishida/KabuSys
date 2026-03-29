# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-29

初回公開リリース。

### 追加 (Added)
- 全体
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = 0.1.0）。
  - パッケージ公開モジュールを __all__ で定義（data, strategy, execution, monitoring）。

- 設定 / 環境変数
  - 環境変数・設定管理モジュールを実装（kabusys.config.Settings）。
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出は .git または pyproject.toml を基準）。
    - .env パーサの強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いを考慮。
    - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - OS 環境変数は保護（.env の上書きを制御）する仕組みを導入。
    - 必須環境変数取得ヘルパー _require を追加（未設定時は ValueError）。
    - 利用可能な環境値チェック（KABUSYS_ENV, LOG_LEVEL）とユーティリティプロパティ（is_live / is_paper / is_dev）を提供。
    - デフォルト値やパス解決（duckdb / sqlite パスの展開）を実装。

- AI（自然言語処理）
  - ニュースセンチメント分析モジュールを追加（kabusys.ai.news_nlp）。
    - raw_news と news_symbols を集約して銘柄ごとにニュースを整形し、OpenAI（gpt-4o-mini）の JSON Mode にバッチ送信してスコアを取得。
    - 時間ウィンドウ（JSTベース）計算ユーティリティ calc_news_window を実装（前日15:00〜当日08:30 JST を対象）。
    - バッチ処理（最大 20 銘柄 / チャンク）、トークン肥大対策（記事数・文字数トリム）を導入。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライを実装。
    - レスポンス検証ロジック（JSON 抽出、results 構造検査、コード整合、スコア数値化、クリップ）を実装。
    - 書き込みの冪等性を配慮した ai_scores テーブルの置換ロジック（DELETE → INSERT）を実装。
    - score_news(conn, target_date, api_key=None) API を公開。OPENAI_API_KEY の利用も可能。

  - 市場レジーム判定モジュールを追加（kabusys.ai.regime_detector）。
    - ETF（コード 1321）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出ロジック（マクロキーワードフィルタ）と OpenAI 呼び出しを独立実装。
    - API エラー耐性（リトライ、5xx の扱い、フェイルセーフで macro_sentiment=0.0）を備える。
    - レジームスコア合成、閾値によるラベリング、market_regime への冪等書き込みを実装。
    - score_regime(conn, target_date, api_key=None) API を公開。OPENAI_API_KEY の利用も可能。

- リサーチ / ファクター
  - research パッケージを追加（kabusys.research）。
    - factor_research モジュールを実装:
      - calc_momentum: 1M/3M/6M リターン、200日MA乖離（ma200_dev）を計算。
      - calc_volatility: 20日ATR、相対ATR、20日平均売買代金、出来高比率を計算。
      - calc_value: raw_financials から EPS/ROE を使用し PER / ROE を計算。
    - feature_exploration モジュールを実装:
      - calc_forward_returns: 任意ホライズンの将来リターンを計算（デフォルト [1,5,21]）。
      - calc_ic: スピアマンランク相関（IC）を実装（欠損/分散ゼロのハンドリング）。
      - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
      - rank: 同順位の平均ランク付けを実装（丸めて ties を安定化）。
    - zscore_normalize は kabusys.data.stats から再エクスポート。

- データプラットフォーム
  - data パッケージを追加（kabusys.data）。
  - マーケットカレンダー管理（kabusys.data.calendar_management）を実装:
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定ユーティリティを提供。
    - market_calendar が未取得の場合は曜日ベースでフォールバックするロジックを実装。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新する夜間バッチ処理を実装（バックフィル・健全性チェックを含む）。
  - ETL パイプライン（kabusys.data.pipeline）を実装:
    - 差分取得、idempotent 保存、品質チェック連携を行う設計（jquants_client と quality モジュールを使用）。
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - ETLResult は品質問題とエラー概要を保持し、has_errors / has_quality_errors / to_dict を提供。
    - DuckDB テーブルチェックや最大日付取得などのユーティリティを実装。

- テスト補助 / その他実装
  - OpenAI 呼び出しを行う内部関数（各モジュール）を分離しており、ユニットテスト時に差し替え（patch）可能。
  - DuckDB を前提とした SQL 実装を多数導入（prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar, market_regime 等へのクエリ）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 破壊的変更 (Breaking Changes)
- 初回リリースのため該当なし。

### セキュリティ / 設定に関する重要な注意点
- OpenAI API を利用する機能（score_news, score_regime）は API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError が発生します。
- .env 自動ロードはデフォルトで有効。テストや明示的制御が必要な場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env の自動ロードは OS 環境変数を保護する仕組み（既存の環境変数は上書きされない、.env.local は override=True だが protected set に含まれる既存キーは上書きされない）を備えています。

### 既知の制約 / 注意事項
- ニュース / レジーム系は外部 OpenAI API に依存しており、API 料金やレートリミット・レスポンス変化に影響を受けます。レスポンスのパース失敗や API エラーはフェイルセーフ（スコアを 0.0 とする等）で処理を継続しますが、結果の品質に注意してください。
- DuckDB のバージョン依存（executemany の空リスト扱い等）を考慮した実装が行われています。特に executemany に空リストを渡さない保護があるため、DB 周りの互換性に留意してください。
- 時刻はモジュールごとに意図的に timezone-naive な UTC / JST 変換ロジックを使っています。target_date を基準にウィンドウを計算する設計で、datetime.today() の直接参照を避けルックアヘッドバイアスを防止しています。
- market_calendar がまばら（部分的）に登録されている場合でも一貫した判定となるよう設計していますが、完全なカレンダーデータがあることが望ましいです。

---

今後のリリース予定（例）
- 改善: スコアリングのモデル選択やプロンプト調整、OpenAI 回数削減のためのキャッシュ。
- 機能追加: strategy / execution / monitoring モジュールの実装（現状パッケージ構成としてエクスポートのみ）。