# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠し、セマンティックバージョニングを用います。  
このファイルはコードベースから推測して作成した初期リリースノートです。

## [Unreleased]
- 特になし

## [0.1.0] - 2026-03-28
初回公開リリース。日本株自動売買・データプラットフォームの基礎機能を提供します。主な追加点は以下のとおりです。

### 追加 (Added)
- パッケージ全体
  - パッケージ名: kabusys、バージョン 0.1.0 を導入。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ にてエクスポート。

- 設定管理 (kabusys.config)
  - Settings クラスを追加し、環境変数経由で各種設定（J-Quants / kabu API / Slack / DB パス / 環境モード / ログレベル）を取得可能に。
  - .env ファイルの自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を起点）。読み込み優先順位: OS 環境変数 > .env.local > .env。
  - .env パーサーを実装（export 文のサポート、クォート、エスケープ、インラインコメントの扱いに対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 必須環境変数未設定時は ValueError を投げる _require 関数を提供。
  - デフォルト値:
    - KABUSYS_ENV: development（有効値: development, paper_trading, live）
    - LOG_LEVEL: INFO
    - KABU_API_BASE_URL: http://localhost:18080/kabusapi
    - DUCKDB_PATH: data/kabusys.duckdb
    - SQLITE_PATH: data/monitoring.db
  - OS 環境変数の上書きを保護する protected キーセットを実装。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news: ニュース記事を集約して OpenAI（gpt-4o-mini）でセンチメントを算出し、ai_scores テーブルに書き込む ETL/スコアリング処理を実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（DB 比較は UTC naive datetime を使用）。
    - バッチ処理: 最大 20 銘柄/リクエスト、1 銘柄あたり最大 10 記事、最大 3000 文字でトリム。
    - OpenAI JSON Mode を利用し、レスポンスを厳密な JSON として期待。
    - リトライ/バックオフ: 429、ネットワーク断、タイムアウト、5xx に対して指数バックオフで再試行（デフォルト _MAX_RETRIES=3）。
    - レスポンス検証: results リスト・code・score の整合性チェック、スコアは ±1.0 にクリップ。
    - 部分失敗耐性: 成功した銘柄のみを DELETE → INSERT で置換し、他銘柄の既存スコアを保護。
    - テスト容易性のため、OpenAI 呼び出し箇所は _call_openai_api をパッチできる設計。
  - regime_detector.score_regime: マーケットレジーム判定（bull / neutral / bear）を実行して market_regime テーブルに冪等書き込み。
    - 入力: ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成。
    - マクロニュースは news_nlp.calc_news_window を用いて窓を計算し、raw_news からキーワードでフィルタ。
    - LLM モデル: gpt-4o-mini、JSON Mode を利用し {"macro_sentiment": float} を期待。
    - 乖離スケールや閾値、重みは定数で管理（_MA_SCALE, _MA_WEIGHT, _MACRO_WEIGHT, _BULL_THRESHOLD, _BEAR_THRESHOLD 等）。
    - API 呼び出し失敗時は macro_sentiment = 0.0 でフォールバックするフェイルセーフ。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT を使い冪等に実装。失敗時は ROLLBACK を試行して例外を上位へ伝播。

- データ (kabusys.data)
  - calendar_management: JPX マーケットカレンダー管理と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar がない場合は曜日ベースのフォールバック（土日を非営業日とする）。
    - next/prev は最大探索日数制限（_MAX_SEARCH_DAYS）を設けて無限ループを防止。健全性チェックやバックフィルも実装。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル日数・先読み日数・健全性チェックをサポート。
  - pipeline / ETL
    - ETLResult データクラスを提供（取得数・保存数・品質問題・エラーの集約）。
    - ETL 全体方針とユーティリティ関数（テーブル存在チェック、最大日付取得、ターゲット日調整など）を実装。
    - デフォルトのバックフィル・最小データ日時等の定数を含む。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- Research (kabusys.research)
  - factor_research: ファクター計算関数群を実装。
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離 (ma200_dev) を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。必要行数未満は None。
    - calc_value: raw_financials と prices_daily を組み合わせて PER、ROE を計算。EPS が 0/欠損の場合は PER を None。
    - DuckDB を用いた SQL ベースの実装で、外部 API にはアクセスしない。
  - feature_exploration: 研究向けユーティリティを実装。
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で計算。horizons のバリデーションあり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。有効レコード数が不足すると None を返す。
    - rank: 平均ランク（ties は平均）を返すユーティリティ。丸めによる ties 検出漏れを防ぐため round を利用。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリで計算するツール。
  - research パッケージは主要関数を再エクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize 等）。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### セキュリティ (Security)
- 環境変数の取り扱いに注意し、.env 自動読み込み時に OS 環境変数を保護（上書き防止）する仕組みを導入。
- OpenAI API キーや他の機密情報は Settings._require を通して必須化し、未設定時には早期エラーを出す。

### 設計上の重要な注意点 / 動作期待値
- ルックアヘッドバイアス防止: AI モジュールおよび研究モジュールは datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を渡す設計。
- OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）で行い、レスポンスパースやフォールバック処理を慎重に行う。
- DuckDB 特有の制約（executemany に空リストを渡せない等）を考慮した実装が含まれる。
- 部分失敗耐性: AI スコア書き込み・ETL 書き込みは部分的に成功した場合でも他データを消さないように設計（コード単位で DELETE → INSERT）。

### 既知の制限 / 未実装事項
- PBR・配当利回りなどのバリューファクターは現バージョンでは未実装（calc_value に注記あり）。
- いくつかの外部クライアント（jquants_client, kabu ステーションクライアントなど）はインターフェース呼び出しを想定しているが、この差分からは実装の詳細は推測に依存。
- strategy / execution / monitoring パッケージの詳細実装はこの差分からは確認できないため、別途実装・ドキュメント化が必要。

---

もし CHANGELOG に特定の追加・修正点（例えば実装担当者名や細かな挙動の補足）を含めたい場合は、その内容を教えてください。コードの差分や追加ファイルがあれば、それに合わせてエントリを更新します。