Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。セマンティックバージョニングを採用しています。

Unreleased
----------

（現在なし）

0.1.0 - 2026-04-01
------------------

初回公開リリース。

Added
- パッケージ基礎
  - パッケージ名: kabusys、バージョン: 0.1.0
  - エントリポイント: src/kabusys/__init__.py（data / strategy / execution / monitoring を公開）
- 設定管理
  - 環境変数・設定読み込みユーティリティ（src/kabusys/config.py）を追加。
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサは export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live）などのプロパティを公開。
  - 必須項目未設定時は明示的に ValueError を発生させる（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
- データ（Data platform）
  - ETL 基盤
    - ETLResult データクラス（src/kabusys/data/pipeline.py）を追加。ETL の取得数・保存数・品質問題・エラーを集約して返却可能。
    - パイプライン設計方針を実装（差分更新・バックフィル・品質チェックの骨子）。
  - カレンダー管理
    - market_calendar を扱うユーティリティ群（src/kabusys/data/calendar_management.py）を追加:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
      - calendar_update_job：J-Quants から差分取得して冪等的に保存（バックフィル・健全性チェックあり）
    - DB 未取得時の曜日ベースフォールバック、最大探索日数制限など安全策を採用。
- 研究（Research）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日移動平均乖離）、Volatility（20日 ATR）、Value（PER/ROE）、Liquidity（20日平均売買代金・出来高比率）を計算する関数を実装。
    - DuckDB に対する SQL ウィンドウ関数を用いた実装。結果は (date, code) キーの辞書リストで返却。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank、factor_summary を実装。
    - スピアマン相関（ランク相関）実装、ties の平均ランク処理、統計サマリー機能を提供。
  - re-export: kabusys.research パッケージで主要関数を公開。
- AI 機能
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini、JSON Mode）で銘柄ごとのセンチメントを -1.0〜1.0 で評価して ai_scores テーブルへ書き込み。
    - 処理の特徴：
      - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）。
      - 1 チャンク最大 20 銘柄、1 銘柄あたり最大 10 記事・3000 文字でトリム。
      - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ（最大 retry 回）、その他はフォールバックでスキップ。
      - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト、code の照合、数値チェック、±1.0 クリップ）。
      - OpenAI 呼び出し点は _call_openai_api を定義しており、テスト時に差し替え可能（unittest.mock.patch 対応）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ日次判定結果を書き込み。
    - 設計上の注意:
      - ルックアヘッドバイアス防止（target_date を明示指定し datetime.today()/date.today() を参照しない）。
      - データ不足時や API 失敗時は安全にフォールバック（ma200_ratio=1.0、macro_sentiment=0.0）。
      - OpenAI API 呼び出しのリトライ・エラー分類を実装。
- その他
  - 複数モジュールで共通の設計方針（ルックアヘッドバイアス回避、DuckDB ベース、部分失敗時の冪等操作）を採用。
  - OpenAI クライアント（openai.OpenAI）を利用する実装の中で、API 呼び出しの再試行ロジックとログ出力を実装。
  - ロギング（logger）を各モジュールで使用し情報・警告・デバッグ出力を行う。

Notes / 注意事項
- 必須環境変数:
  - OPENAI_API_KEY: AI 機能（score_news / score_regime）の呼び出し時に必要（関数引数 api_key でも注入可）。
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など（Settings 参照）。未設定時は Settings の該当プロパティが ValueError を投げます。
- .env 自動ロード:
  - プロジェクトルート検出は __file__ からの親探索を行うため、作業ディレクトリに依存しません。テスト環境で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 依存:
  - 多くの関数は duckdb.DuckDBPyConnection を直接受け取り SQL クエリで処理します。呼び出し側で接続を用意してください。
- ルックアヘッド回避:
  - 全ての解析/スコアリング関数は target_date を引数に取り、内部で現在日時を直接参照しないように設計されています。これはバックテスト時のルックアヘッドバイアス防止のための意図的な設計です。
- テスト性:
  - OpenAI 呼び出し部分は内部関数（_call_openai_api）を通じているため、ユニットテスト時にモック差し替えが可能です。

Breaking Changes
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Contributing
- 貢献・バグ報告はリポジトリの Issue / PR を使用してください。コード内の docstring に設計方針や注意点を記載していますので参照してください。