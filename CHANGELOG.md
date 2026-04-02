CHANGELOG
=========

すべての重要な変更履歴はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。
リリースごとにユーザ向けに分かりやすく要点をまとめています。

[Unreleased]
------------

（現在未リリースの変更はありません）

0.1.0 - 2026-04-02
-----------------

初回公開リリース。

Added
- コアパッケージ初期実装を追加
  - パッケージメタ情報: kabusys/__init__.py にバージョン "0.1.0"、主要サブパッケージの公開（data, strategy, execution, monitoring）。
- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env と .env.local の優先順位の扱い（OS 環境変数を保護する protected 機構を含む）。
  - export KEY=val 形式、クォート・エスケープ、コメント処理などを考慮した .env パーサー実装。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / 監視閾値 / 実行環境（development / paper_trading / live）などをプロパティで取得。必須項目未設定時は ValueError を送出。
- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols を集約して銘柄ごとの記事を作成し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 20 銘柄/コール）、入力トリミング（記事件数上限・文字数上限）、JSON Mode を使った堅牢なレスポンス処理。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）を指数バックオフで実施。API 失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - DuckDB へ idempotent に書き込む（該当コードだけを DELETE→INSERT）ことで部分失敗から既存データを保護。
    - ユーティリティ：calc_news_window（JST ベースのニュース集計ウィンドウ計算）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。
  - regime_detector.score_regime
    - ETF（コード 1321）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - prices_daily と raw_news を参照、ma200 の不足時や API 失敗時は中立フェイルセーフ（ma200_ratio=1.0 / macro_sentiment=0.0）。
    - OpenAI 呼び出しに対するリトライ・エラーハンドリングを実装。
- データプラットフォーム関連（kabusys.data）
  - calendar_management
    - JPX カレンダー管理（market_calendar）機能。営業日判定（is_trading_day）、前後営業日取得（next_trading_day / prev_trading_day）、期間の営業日リスト取得（get_trading_days）、SQ 判定（is_sq_day）、および夜間バッチ更新 job（calendar_update_job）。
    - DB 登録がない日や NULL 値は曜日ベースのフォールバック（週末は非営業日）で扱い、一貫性を維持する設計。
    - 最大探索日数の制限や健全性チェック（未来日付の異常検出）、バックフィルの実装。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを公開（etl モジュール経由で再エクスポート）。
    - 差分取得・idempotent 保存（jquants_client の save_* を想定）・品質チェック（quality モジュール）を想定した設計。バックフィルやエラー・品質検出の扱い方を明示。
    - 内部ユーティリティ関数（テーブル存在チェック、最大日付取得等）。
- リサーチ（kabusys.research）
  - factor_research
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20 日 ATR など）、Value（PER、ROE）を DuckDB の prices_daily / raw_financials を用いて計算する関数を提供（calc_momentum, calc_volatility, calc_value）。
    - 設計方針：外部 API にアクセスせず、結果は (date, code) をキーとする dict リストで返す。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - スピアマン（ランク）相関計算、ties の扱い、データ不足時の挙動（None 戻し）等を明記。
- パッケージのエクスポート整理
  - research/__init__.py で主要関数を再公開（calc_momentum, calc_volatility, calc_value, zscore_normalize 他）。

Notes / 注意事項
- OpenAI API
  - news_nlp.score_news / regime_detector.score_regime は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を送出。
  - gpt-4o-mini と JSON Mode を前提にプロンプト設計している（出力を厳密な JSON と期待）。
- 環境変数必須項目
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等は Settings 経由で必須になっている。未設定時は ValueError。
- データベース
  - DuckDB を主要なデータ層として利用。ai / research / data で DuckDB の接続オブジェクト（DuckDBPyConnection）を受け取る API が多い。
- ルックアヘッドバイアス対策
  - 主要な日付関数は内部で datetime.today()/date.today() を参照しない（target_date を明示的に受け取る）設計。将来データ参照の防止に留意。
- テスト支援
  - OpenAI 呼び出し等を個別にモックしやすい実装（内部関数を切り出し）を行っている。
- フェイルセーフ設計
  - API エラー・パース失敗時は基本的に例外で落とさずフォールバック値を用いる（ログ出力）。ただし DB 書き込み失敗時は ROLLBACK 後に例外伝播。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

アップグレード / 移行メモ
- 既存の環境に導入する際は .env.example を参考に必須の環境変数を設定してください。
- 自動で .env を読み込ませたくない CI/テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ（prices_daily, raw_news, raw_financials, market_calendar, ai_scores, market_regime 等）が必要です。サンプルスキーマは別途ドキュメントを参照してください。

既知の制限
- 現バージョンでは PBR・配当利回り等の一部バリューファクターは未実装（calc_value の注記参照）。
- news_nlp は提示した銘柄コードのみを返すことを期待するプロンプト設計だが、LLM の挙動次第で未知コードやパースエラーが発生する可能性あり。その場合は該当チャンクをスキップして処理を継続する。

貢献・バグ報告
- 不具合報告や機能要望は issue を立ててください。報告の際は再現手順、使用する DB スキーマの例、ログ抜粋を添えていただけると助かります。