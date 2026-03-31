# Keep a Changelog — CHANGELOG

すべての重要なリリースノートをこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

最新リリース
------------

### [0.1.0] - 2026-03-31

初回リリース — 日本株自動売買およびデータ基盤のコア機能を提供します。

Added
- パッケージ基盤
  - パッケージ初期化: kabusys パッケージとバージョン定義（__version__ = "0.1.0"）。
  - 公開モジュールの __all__ 設定（data, strategy, execution, monitoring）。

- 設定管理
  - 環境変数/.env 読み込みユーティリティ（kabusys.config）。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）。
    - .env / .env.local を自動読み込み（優先順位: OS 環境 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - export KEY=val、引用、インラインコメント等の .env パースに対応。
    - protected パラメータにより OS 環境変数の上書きを保護。
  - Settings クラスによるアプリケーション設定抽象化（必須キーチェック、デフォルト値、値検証）。
    - 必須環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
    - データベースのデフォルトパス: DUCKDB_PATH= data/kabusys.duckdb, SQLITE_PATH= data/monitoring.db。
    - 環境種別（KABUSYS_ENV）およびログレベル（LOG_LEVEL）の検証ユーティリティ。

- AI（自然言語処理）関連
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini / JSON mode）でセンチメントを評価。
    - バッチ処理（最大 20 銘柄/コール）、1銘柄あたり最大記事数・文字数のトリミング実装。
    - 再試行（429、ネットワーク断、タイムアウト、5xx）を指数バックオフで実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、コード整合性、数値チェック）。
    - 結果は ai_scores テーブルに冪等的に書き込む（DELETE → INSERT、部分失敗に対する保護）。
    - テスト用フック: _call_openai_api を patch して差し替え可能。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive で扱う）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - OpenAI（gpt-4o-mini）を用いてマクロ記事群からセンチメントを評価。記事が無ければ LLM 呼び出しをスキップしマクロセンチメント=0.0。
    - API エラー時はフェイルセーフで macro_sentiment=0.0 にフォールバック。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - テスト容易性のため _call_openai_api を独立実装（news_nlp から共有しない設計）。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - ETLResult データクラスを提供（取得件数、保存件数、品質問題、エラー概要など）。
    - 差分更新、バックフィル、品質チェックを想定した設計。
  - ETL エクスポート（kabusys.data.etl）：ETLResult の再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを参照して営業日判定 / 次・前営業日取得 / 期間内営業日取得 / SQ 判定を提供。
    - DB 登録情報優先、未登録日は曜日ベースのフォールバック（週末は非営業日）。
    - JPX カレンダーを J-Quants から差分取得して更新する夜間バッチ job（calendar_update_job）。バックフィルと健全性チェックを実装。
    - 最大探索日数の上限設定により無限ループを防止。

- リサーチ（kabusys.research）
  - factor_research
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）といった定量ファクター計算関数を実装。
    - DuckDB を用いた SQL ベースの計算。結果は (date, code) ベースの dict リストで返却。
    - データ不足時は None を返却する挙動で堅牢化。
  - feature_exploration
    - 将来リターン計算（複数ホライズン対応。デフォルト [1,5,21]）、IC（Spearman ρ）計算、ファクター統計サマリー、ランク変換等の統計ユーティリティを実装。
    - pandas 等に依存せず標準ライブラリで実装。

- その他設計上の注意点（ドキュメント・実装に明示）
  - 全 AI / スコアリング処理はルックアヘッドバイアス回避のため datetime.today() 等を参照しない（呼び出し側で target_date を渡す）。
  - DuckDB を中心としたデータ参照・保存設計。DuckDB バージョン差異（executemany の空リスト等）に対応した実装。
  - DB 書き込みは可能な限り冪等性を確保（DELETE→INSERT 等）。
  - OpenAI クライアント生成は引数で API キーを注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- API キーやトークンは Settings で必須チェックを行い、環境変数に依存する設計。.env 自動ロード時に既存 OS 環境を保護する仕組みあり（protected keys）。

Notes / 使用上の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（API 呼び出しを行う機能を利用する場合）。
- .env 自動読み込みはプロジェクトルートの特定に依存する。パッケージ配布後に自動読み込みが不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは gpt-4o-mini + JSON mode を想定。API レスポンスの形式やステータス挙動に依存するため、SDK バージョン差異に注意してください。
- DuckDB のバージョン差により一部のバインド（リスト型のバインドなど）が不安定なため、実装上の回避策を取っています。

Breaking Changes
- （初回リリースのため該当なし）

Unreleased
- 今後、発注（execution）やモニタリング（monitoring）の実装拡張、モデル改善、外部 API のリトライ/監視強化、テストカバレッジ拡張等を計画しています。