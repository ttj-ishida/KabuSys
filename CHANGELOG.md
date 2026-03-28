KEEP A CHANGELOG
=================

すべての notable な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-28
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - src/kabusys/__init__.py にバージョン情報と公開サブパッケージを定義。
- 環境設定管理 (kabusys.config)
  - .env/.env.local 自動ロード機能（プロジェクトルートは .git または pyproject.toml から探索）。
  - export 構文やクォート・インラインコメントの取り扱いに対応した .env パーサ実装。
  - OS 環境変数を保護する protected モードと override フラグ。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスで主要設定をプロパティで公開（J-Quants / kabu API / Slack / DB パス / 実行環境 / ログレベル 等）。
  - 必須環境変数未設定時に明瞭な ValueError を送出する _require 実装。
  - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
- AI モジュール (kabusys.ai)
  - news_nlp モジュール (score_news)
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメント評価。
    - バッチ処理（最大 20 銘柄）およびチャンクごとのリトライ（429/ネットワーク/タイムアウト/5xx を指数バックオフで再試行）。
    - レスポンスの厳密な JSON 検証とスコアのクリップ（±1.0）。
    - DuckDB への冪等書き込み（DELETE → INSERT）。DuckDB executemany の空リスト制約へ対処。
    - calc_news_window ユーティリティ（ニュース集計ウィンドウの UTC 時刻計算）。
    - テスト容易性のため _call_openai_api を patch 可能な設計。
  - regime_detector モジュール (score_regime)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と
      ニュース NLP（重み 30%）の合成で市場レジーム（bull/neutral/bear）を日次判定。
    - マクロキーワードで raw_news をフィルタし、LLM でマクロセンチメント評価（gpt-4o-mini）。
    - API 障害時は macro_sentiment=0.0 のフェイルセーフ、リトライ・エラーハンドリングを実装。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理。
    - テスト容易性のため _call_openai_api を patch 可能な設計。
- Research モジュール (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日ATR）、流動性（平均売買代金・出来高比）、バリュー（PER, ROE）などの計算関数提供（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL ベース実装で外部 API にはアクセスしない設計。
  - feature_exploration
    - 将来リターン calc_forward_returns（複数ホライズン対応、入力バリデーションあり）。
    - IC（Spearman ρ）計算 calc_ic、rank ユーティリティ、factor_summary（count/mean/std/min/max/median）を提供。
  - zscore_normalize をデータユーティリティから再公開。
- Data モジュール (kabusys.data)
  - calendar_management
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar がない場合は曜日ベースのフォールバックを行う堅牢な設計。
    - J-Quants クライアント呼び出し（差分取得・バックフィル・異常検知ロジック）。
  - ETL / pipeline
    - ETLResult データクラス（ETL 実行結果の集約、品質チェック結果・エラー収集）。
    - パイプラインユーティリティ（差分取得・保存・品質チェックの設計方針を実装するための基盤）。
  - etl モジュールで ETLResult を再エクスポート。
  - jquants_client / quality との連携を想定した設計。
- 汎用設計方針・品質
  - いずれの分析処理でも datetime.today()/date.today() を直接参照せず、外部から target_date を受け取る設計（ルックアヘッドバイアス防止）。
  - API 呼び出しに対する堅牢なエラーハンドリングとリトライ・バックオフ実装。
  - DuckDB の挙動（executemany の空リスト制約など）へのワークアラウンドを実装。
  - ロギングと警告を通じた失敗時のフォールバック（例: データ不足時の中立値使用、API 失敗時のスコア 0.0）。

Fixed
- 初期実装で考慮した安定性向上点:
  - OpenAI/API の各種例外（429, 接続エラー, タイムアウト, 5xx）を個別に扱い、リトライとフォールバックを実装。
  - DuckDB への書き込みでトランザクション保護（ROLLBACK の失敗ログもキャッチ）。
  - JSON モードの結果に余分な前後テキストが混入するケースを復元してパースする耐性を追加。

Security
- 環境変数の取り扱いに注意:
  - OS 環境変数は .env の上書きから保護（protected set を利用）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により .env の自動読み込みを無効化可能（テスト向け）。
  - OpenAI API キーや各種トークンは必須の環境変数として明示し、未設定時は例外を投げる。

Known issues / Notes
- 本リリースは「初期実装」であり、以下の点が既知制約・今後の検討事項です:
  - 一部の外部依存（jquants_client, kabusys.data.jquants_client 等）は仮想的なクライアント実装を前提としているため、実行環境側で具体的実装が必要。
  - OpenAI の API レスポンス形式や SDK の変更に備え、例外処理は広めに取っているが、将来的な SDK 変更時に追加対応が必要になる可能性あり。
  - 現フェーズでは sentiment_score と ai_score を同値で保存しているが、将来の拡張で異なる扱いに変更する余地あり。
  - calendar_update_job は J-Quants API の応答に依存するため、API スキーマ変更時に修正が必要。

Migration notes / 環境変数一覧（主な必須項目）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
  - OPENAI_API_KEY（AI 関連機能を利用する場合）
- 任意 / デフォルト:
  - KABUSYS_ENV (development|paper_trading|live) - デフォルト: development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) - デフォルト: INFO
  - DUCKDB_PATH - デフォルト: data/kabusys.duckdb
  - SQLITE_PATH - デフォルト: data/monitoring.db
  - KABUSYS_DISABLE_AUTO_ENV_LOAD - 自動 .env ロード無効化フラグ

Contact / Contributing
- バグ報告・機能要望はリポジトリの issue へ。
- テストしやすい設計（_call_openai_api の patch など）を意識して実装しています。ユニットテストの追加歓迎。

-----