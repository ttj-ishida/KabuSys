KEEP A CHANGELOG
=================

すべての重要な変更をこのファイルに記録します。
このプロジェクトは「Keep a Changelog」規約に従い、セマンティックバージョニングを採用しています。

[Unreleased]
------------

（なし）

0.1.0 - 2026-03-29
------------------

初回リリース。日本株自動売買システムの基盤機能を実装・公開しました。

Added
- パッケージ化
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - 主要サブパッケージを公開: data, research, ai, monitoring, strategy, execution（__all__ による再エクスポート/公開方針）。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱いなどに対応）。
  - 環境変数読み込み時の上書き制御（override, protected）を実装し、OS 環境変数を保護。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを実装してアプリケーション設定をプロパティとして提供（J-Quants / kabu API / Slack / DB パス / 環境モード / ログレベル等）。
  - Settings は無効な KABUSYS_ENV / LOG_LEVEL に対して ValueError を発生させるバリデーションを実装。

- AI（自然言語処理・レジーム判定）
  - ニュースセンチメント分析（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）の JSON モードで一括スコアリング。
    - バッチ処理（最大 20 銘柄/リクエスト）、各銘柄で記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 再試行ロジック（429/ネットワーク断/タイムアウト/5xx を指数バックオフでリトライ）。
    - レスポンスの堅牢なバリデーション（JSON モードでも前後ノイズを切り出して解析、results フォーマット検証、未知コード無視、数値チェック）。
    - スコアを ±1.0 にクリップし、ai_scores テーブルへ冪等（DELETE → INSERT）で保存。部分失敗時に既存スコアを保護する実装。
    - calc_news_window（ニュース集計ウィンドウ計算）を提供（JST の前日 15:00 ～ 当日 08:30 を UTC naive datetime に変換）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull / neutral / bear）を判定。
    - ma200_ratio 計算はルックアヘッドを防ぐため target_date 未満のデータのみ使用。データ不足時は中立値 (1.0) を採用。
    - マクロニュース抽出（マクロキーワードによるタイトルフィルタリング）→ OpenAI 呼出し → スコア合成。
    - OpenAI 呼出しの再試行・エラー分類（RateLimit, 接続エラー, タイムアウト, APIError の 5xx 判定等）。API 失敗時は macro_sentiment=0.0 としてフォールバック。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - テストしやすいように内部の API 呼び出し関数は差し替え可能（patch によるモックを想定）。

- リサーチ（ファクター計算・特徴量探索）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を計算。データ不足は None。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。欠損取り扱いを明示。
    - calc_value: raw_financials から最新の財務データを取得して PER / ROE を計算（EPS が 0 または欠損のときは None）。
    - DuckDB を用いた SQL ベース実装（prices_daily / raw_financials のみ参照）。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを計算。ホライズン検査（正の整数かつ <=252）あり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（rank 関数を利用、欠損や ties を適切に扱う）。
    - rank: 同順位を平均ランクにする安定的なランク関数（丸めで ties 検出の安定化）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を標準ライブラリのみで計算。

- データ基盤（DuckDB を前提）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar がない場合でも曜日ベース（土日非営業）でのフォールバック処理を提供。
    - calendar_update_job: J-Quants クライアント経由で市場カレンダーを差分取得し、冪等保存（fetch/save をラップ）。バックフィル、健全性チェックを実装。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) による無限ループ防止、NULL 値発生時のログ出力など安全策を実装。

  - ETL パイプライン基盤（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを提供（取得件数・保存件数・品質チェック・エラー管理など）。
    - 差分取得、バックフィル、品質チェックのためのユーティリティと設計上の方針を実装。ETLResult は外部へ再エクスポート（etl.py）。

- テストしやすさ・運用上の工夫
  - OpenAI 呼び出しや内部ユーティリティ関数は unittest.mock.patch で差し替え可能として実装（テスト容易性を考慮）。
  - DuckDB の executemany に対する互換性考慮（空リストでの executemany を回避）。
  - すべての関数はデータベースアクセスのみで完結する設計（本番環境の発注 API へはアクセスしない保証）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 外部 API キー（OPENAI_API_KEY 等）未設定時は呼び出し側へ ValueError を発生させ明確に失敗する実装。環境変数の自動読み込みは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）でテスト/CI の安全性を確保。

Migration notes / 注意点
- Settings のプロパティは必須環境変数が未設定の場合 ValueError を送出します。導入時は .env.example を参考に必要な環境変数を設定してください（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
- OpenAI API 呼び出しを行う機能（news_nlp, regime_detector）は API キーが必要です。api_key 引数で明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- DuckDB を使用するため、テーブル構成（prices_daily / raw_news / news_symbols / ai_scores / market_calendar / raw_financials 等）を事前に準備する必要があります。
- calendar_update_job / ETL の実行は J-Quants クライアント（kabusys.data.jquants_client）に依存します。実運用にあたっては J-Quants の API 資格情報とクライアント実装を用意してください。

---- 
（以降のリリースでは、各変更点をカテゴリ別に追加していきます。）