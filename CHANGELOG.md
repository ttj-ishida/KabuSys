KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]

## [0.1.0] - 2026-04-03
初回リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能を実装しました。主な追加点と設計上の要点は以下の通りです。

追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加 (kabusys.__init__.__version__ = "0.1.0")。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を定義。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml 基準）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルのパース機能を実装（export プレフィックス対応、シングル/ダブルクォートとエスケープ、インラインコメント処理）。
  - 設定プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, 各種閾値やログレベル/環境判定ユーティリティ（is_live / is_paper / is_dev）を提供。
  - 設定値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と必須項目チェック（未設定時に ValueError）。

- データレイヤ / ETL (kabusys.data.pipeline, etl 再エクスポート)
  - ETLResult データクラスを実装（ETL 実行結果、品質問題、エラーの集約、辞書化ユーティリティ）。
  - ETL モジュール設計により、差分取得・バックフィル・品質チェック・Idempotent 保存を方針として実装（jquants_client と quality モジュールを利用する設計）。
  - DuckDB を用いたテーブル存在チェック、最大日付取得等のユーティリティを用意（ETL 実装の準備）。

- カレンダー管理 (kabusys.data.calendar_management)
  - JPX マーケットカレンダー管理機能を実装。
  - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days の営業日判定 API を用意。market_calendar テーブルがない場合は曜日ベースでフォールバック。
  - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得して market_calendar を冪等更新、バックフィルや健全性チェックを含む）。
  - DB の不整合（NULL 値など）に対するログ警告やフォールバックを実装。

- 研究用（Research）ユーティリティ (kabusys.research)
  - ファクター計算: calc_momentum, calc_value, calc_volatility を実装（prices_daily / raw_financials を用いる）。
  - 特徴量探索: calc_forward_returns（将来リターン計算）、calc_ic（Spearman IC）、factor_summary（統計サマリ）、rank（同順位は平均ランク）を実装。
  - 設計上の制約: DuckDB 接続を受け取り、外部 API を呼ばない、日付のルックアヘッドを防ぐ実装方針を徹底。

- AI（ニュース NLP / レジーム判定） (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp.score_news)
    - raw_news と news_symbols を集約して銘柄単位に記事をまとめ、OpenAI（gpt-4o-mini）の JSON Mode でスコアを取得して ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの最大記事数/文字数制限を実装してトークン肥大化対策。
    - レート制限 (429)、ネットワーク断、タイムアウト、5xx を対象に指数バックオフでリトライ。検証・パース不備は該当チャンクをスキップしフェイルセーフで継続。
    - API 呼び出し部分はテスト容易性のため差し替え可能（_call_openai_api に対してユニットテスト用の patch を想定）。
    - 出力バリデーション処理を実装（JSON 抽出、results リスト検証、未知コードの無視、スコア数値化と ±1.0 のクリップ）。
    - タイムウィンドウは JST ベース（前日 15:00 〜 当日 08:30）で、UTC 変換して DB クエリに使用。ルックアヘッドバイアス防止のため date.today()/datetime.today() を直接参照しない。

  - 市場レジーム判定 (kabusys.ai.regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で regime_score と regime_label(bull/neutral/bear) を算出し market_regime テーブルへ冪等書き込み。
    - マクロ記事抽出のためのキーワード群を定義。記事がない場合は LLM 呼び出しを回避して macro_sentiment=0.0。
    - API 呼び出しでのリトライ/フェイルセーフ（同様に 5xx 等でリトライ、最終的に 0.0 にフォールバック）。
    - OpenAI クライアントは明示的に生成し、外部依存を最小化（テストでの差し替えを想定）。

- その他ユーティリティ
  - data/etl から ETLResult をトップレベルに再エクスポート。
  - 複数モジュールで DuckDB を主要な分析用ローカル DB として想定。

変更 (Changed)
- （初回リリースのため該当なし）

修正 (Fixed)
- （初回リリースのため該当なし）

既知の制約・注意点 (Notable notes / Known issues)
- OpenAI API キーは必須（api_key 引数経由または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出する箇所あり。
- J-Quants / kabu ステーション連携用のトークンやパスワードは環境変数で提供する必要がある（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）。
- DuckDB を前提としている（DuckDB のバージョンに依存した挙動に注記あり、ex: executemany に空リストを渡せない点の回避実装）。
- LLM 呼び出しは gpt-4o-mini を想定。API レスポンスの形式に依存するため、将来の SDK/モデル変更で修正が必要になる可能性あり。
- 一部モジュール（strategy, execution, monitoring）はパッケージ公開インターフェースに含まれるが、ここに示したコードベースでは詳細実装が含まれていない（別途実装・追加を予定）。

マイグレーション / 利用開始のヒント
- .env.example を参考に必要な環境変数を設定し、プロジェクトルートに .env / .env.local を配置してください。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- ローカルデータベースの既定パスは data/kabusys.duckdb（DUCKDB_PATH）および data/monitoring.db（SQLITE_PATH）です。実運用前に適切な永続化先を設定してください。
- AI 関連機能は OpenAI の利用料が発生します。API キーと使用モデルの制約に注意してください。
- DuckDB にテーブルを作成し、prices_daily / raw_news / news_symbols / ai_scores / market_regime / raw_financials / market_calendar 等のスキーマ準備が必要です（ETL 経由で初期ロード可能）。

セキュリティ (Security)
- 機密情報（API キー等）は .env に保存する場合アクセス権に注意してください。設定読み込みでは既定で OS 環境変数が優先され、.env の上書き制御をサポートしています（protected セット機能）。

将来的な拡張案（開発ロードマップ）
- strategy / execution / monitoring モジュールの実装（リアルタイム発注・監視機能）。
- backtesting / simulation 機能、さらに詳細な品質チェックルールとデータ補正パイプライン。
- OpenAI 出力検証の強化（スキーマバリデータ導入）と別モデルサポート。

-----------------------------------------------------------------------------
この CHANGELOG は、ソースコードの実装とドキュメンテーション文字列から推測して作成しています。実際のリリースノート用途には、リリースごとのコミットや PR の粒度で追記・修正を行ってください。