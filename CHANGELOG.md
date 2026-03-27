# Changelog

すべての重要な変更をここに記載します。フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-27

### Added
- 基本パッケージ初期リリースを追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動読み込みを実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
  - .env パーサを実装（export KEY=val 形式、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱い等に対応）。
  - 環境変数上書き時に OS 側の既存キーを保護する機構（protected set）。
  - Settings クラスを提供（プロパティで J-Quants / kabu API / Slack / DB パス / ログレベル / 環境モード を取得）。
  - 必須環境変数未設定時は明確なエラーメッセージで ValueError を送出。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - raw_news と news_symbols からニュースを銘柄別に集約し、OpenAI（gpt-4o-mini / JSON Mode）でセンチメントを評価して ai_scores テーブルへ保存。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部的に UTC に変換）。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、1 銘柄あたり最大記事数／文字数でトリム。
    - API エラー（429、ネットワーク断、タイムアウト、5xx）は指数バックオフでリトライ。非リトライ対象はスキップして継続。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code と score の整合性）。スコアは ±1.0 にクリップ。
    - テスト容易性のため OpenAI 呼び出し部分を差し替えられる設計（_call_openai_api の patch）。
    - DB 書き込みは部分置換（該当コードのみ DELETE → INSERT）で冪等性を確保し、部分失敗時に他銘柄の既存スコアを保護。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して、日次で market_regime テーブルへ書き込み。
    - マクロニュースは定義済みのキーワードでフィルタし、最大 20 件まで LLM に渡す。
    - OpenAI 呼び出しのリトライと 5xx ハンドリングを実装。API 失敗時は macro_sentiment=0.0 でフォールバック。
    - レジームスコアをクリップし、閾値に基づき "bull"/"neutral"/"bear" を判定。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実施。

- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン）、200 日移動平均乖離、ATR（20 日）、流動性指標、財務指標（PER、ROE）を DuckDB の prices_daily/raw_financials を用いて計算。
    - データ不足時の取り扱い（必要データが足りない場合は None を返す）。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman ランク相関）、ファクター統計サマリー、ランク変換ユーティリティを実装。
    - pandas など外部ライブラリに依存せず、標準ライブラリと DuckDB で実装。
  - zscore_normalize を含む data.stats の再エクスポートを実施。

- Data モジュール（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar テーブルがない場合は曜日ベース（週末の除外）でフォールバック。
    - カレンダー夜間バッチ（calendar_update_job）: J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存（jquants_client 経由）。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETL の差分更新、保存（idempotent）、品質チェック（quality モジュール）を統合するパイプライン実装。
    - ETLResult dataclass（target_date, fetched/saved counts, quality_issues, errors, helper プロパティ）を追加。
    - デフォルトの backfill、calendar lookahead、最小データ開始日などの定数を定義。
  - ETLResult を再エクスポート（kabusys.data.etl）。

- DuckDB を中心とした設計
  - すべての分析・ETL は DuckDB 接続を受け取って動作（prices_daily, raw_news, raw_financials, market_calendar, ai_scores, market_regime 等を参照/更新）。
  - DB 書き込みは冪等性を意識（DELETE→INSERT や ON CONFLICT 相当の扱い）。

- 設計原則（ドキュメントに明記）
  - datetime.today()/date.today() を直接参照しない設計（関数引数で日付を受け、ルックアヘッドバイアスを防止）。
  - 外部 API 失敗時はフェイルセーフ（例: LLM 失敗でスコア 0.0、部分的失敗なら他銘柄を保護）。
  - テスト容易性を考慮した差し替えポイント（_call_openai_api の patch、api_key 注入など）。
  - ログ出力と適切な warnings/exception ハンドリングを追加。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Removed
- 初期リリースのため該当なし。

### Security
- OpenAI API キーの扱い
  - OpenAI 呼び出し時に api_key を明示的に渡すことが可能。未指定の場合は環境変数 OPENAI_API_KEY を参照。
  - 環境変数の自動ロードは任意で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / Migration
- 本リリースは初期版のため後方互換性の破壊はありませんが、下記点に注意してください。
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）が未設定だと Settings のプロパティアクセスで ValueError が発生します。 .env.example を参考に .env を設定してください。
  - OpenAI 関連処理は gpt-4o-mini を想定しており、レスポンスは JSON Mode（厳密な JSON）を前提としています。レスポンス形式が異なる場合、パースに失敗して当該処理はスキップされます（フェイルセーフ挙動）。
  - DuckDB のバージョン依存性に注意（executablemany の空リストバインド等に関するコメントあり）。DuckDB の互換性によっては小さな調整が必要になる可能性があります。

### Third-party
- 本プロジェクトは以下の外部ライブラリ/サービスを利用します（明示的に参照）。
  - duckdb
  - openai（OpenAI Python SDK）
  - J-Quants API（jquants_client を通じて利用想定）

---
注: 本 CHANGELOG は提供されたソースコードからの推測に基づいて作成しています。実際のリリースノートでは、追加で API 変更点・既知の問題・実運用向けの設定例などを補足することを推奨します。