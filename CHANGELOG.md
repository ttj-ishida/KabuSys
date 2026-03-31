# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

全般:
- このリポジトリは初回リリース v0.1.0 として公開されます。
- 主な目的は日本株向けのデータ基盤・リサーチ・AI支援・自動売買のユーティリティ群を提供することです。
- 依存: DuckDB、openai SDK（OpenAI クライアント）などが想定されています。

[0.1.0] - 2026-03-31

Added
- パッケージ基礎
  - kabusys パッケージの公開 API を定義（src/kabusys/__init__.py）。
  - バージョン: 0.1.0。

- 設定・環境変数管理
  - 環境変数/.env の自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートは .git または pyproject.toml を起点に探索して判定。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
    - export 形式やクォート、インラインコメント、バックスラッシュエスケープなどの .env パーシングに対応。
    - _require() による必須環境変数チェック（未設定時は ValueError）。
    - Settings クラスでアプリケーション設定をプロパティとして提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV、LOG_LEVEL 等）。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値以外は ValueError）。

- AI (Natural Language / LLM)
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成。
    - OpenAI（gpt-4o-mini）へバッチ（最大 20 銘柄）で JSON Mode により送信し、各銘柄のセンチメント（-1.0〜1.0）を ai_scores テーブルへ保存。
    - 再試行（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）とフェイルセーフ処理を実装。失敗したチャンクはスキップして継続。
    - レスポンス検証（JSON 抽出、results リスト、code と score の妥当性検証、スコアのクリップ）。
    - タイムウィンドウ計算ユーティリティ calc_news_window(target_date) を提供（JST ベースの指定ウィンドウを UTC naive datetime に変換）。
    - 公開 API: score_news(conn, target_date, api_key=None) — 書き込み銘柄数を返す。api_key 未指定時は環境変数 OPENAI_API_KEY を使用し、未設定だと ValueError。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - prices_daily から ma200_ratio を計算し、raw_news からマクロキーワードを使ってタイトルを抽出、OpenAI で macro_sentiment を算出して最終スコアを合成。
    - LLM 呼び出しに対してリトライ・フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。
    - 公開 API: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。api_key 未指定かつ OPENAI_API_KEY 未設定の場合は ValueError。

  - ai パッケージ __init__ を追加し、score_news を公開（src/kabusys/ai/__init__.py）。

- データ（Data Platform）
  - カレンダー管理モジュール（src/kabusys/data/calendar_management.py）
    - market_calendar を利用した営業日判定とユーティリティを提供:
      - is_trading_day(conn, d)、is_sq_day(conn, d)
      - next_trading_day(conn, d)、prev_trading_day(conn, d)
      - get_trading_days(conn, start, end)
    - DB にデータが無い場合は曜日ベース（土日除外）でフォールバック。
    - market_calendar が部分的にしか登録されていない場合でも一貫した振る舞いとなるよう設計。
    - 夜間バッチ更新 calendar_update_job(conn, lookahead_days=90) を実装し、J-Quants API（jquants_client）から差分取得して保存。
    - 健全性チェック、バックフィル、最大探索日数制限 (_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS)。

  - ETL パイプライン（src/kabusys/data/pipeline.py、src/kabusys/data/etl.py）
    - データ差分取得・保存・品質チェックのための ETLResult データクラスを実装（ETL の実行結果を集約・シリアライズ可能）。
    - データベース最終取得日の検出ヘルパー、テーブル存在チェック等のユーティリティ。
    - 設計として差分更新、バックフィル、品質チェック（quality モジュール）を想定。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

  - data パッケージ構造を整備（src/kabusys/data/__init__.py ほか）。

- リサーチ（Research）
  - research パッケージを追加（src/kabusys/research/__init__.py）:
    - 公開: calc_momentum、calc_volatility、calc_value、zscore_normalize（data.stats から）、calc_forward_returns、calc_ic、factor_summary、rank。
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）を計算する関数を提供:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - DuckDB の SQL ウィンドウ関数を活用し、データ不足時は None を返す等の堅牢な設計。
  - 特徴量解析（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)
    - ランキングユーティリティ: rank(values)
    - 統計サマリー: factor_summary(records, columns)

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーや各種トークンは環境変数で管理する設計。Settings._require により必須トークン未設定時は明示的にエラーを出します。
- .env 自動読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD を用いて無効化可能（テスト向け）。

Notes / 注意事項
- OpenAI 呼び出しは gpt-4o-mini を指定し JSON Mode（response_format={"type":"json_object"}）を想定しています。OpenAI SDK のバージョン差や API の挙動変化に備えてエラーハンドリングとフォールバック（0.0）を組み込んでいますが、実運用ではモデル・料金・レイテンシを考慮してください。
- AI 関連の public API (score_news, score_regime) は api_key を引数で注入可能です。テスト時は注入またはモックパッチを推奨します（各モジュール内で _call_openai_api を差し替え可能）。
- DuckDB を前提に SQL と Python を組み合わせた処理を行います。DuckDB バージョン差異による executemany の挙動（空リスト不可等）に注意しています。
- 日付／時間の扱いは「ルックアヘッドバイアス」を避けるため、内部で datetime.today()/date.today() を参照しない設計方針を採用しています（target_date を明示的に与えることを前提）。
- 初期リリースにつき、API の微調整や追加の品質チェック、ユニットテストの整備が今後の課題です。

今後の計画（例）
- テストカバレッジの充実、CI ワークフロー追加
- docs の拡充（使用例、DB スキーマ、運用手順）
- モデル切替やローカル LLM 対応の検討
- ETL の自動スケジューリング・監視統合（Slack 通知など）

もし特定の変更点（ファイル／関数ごとの詳細説明）を追記したい場合は対象を指定してください。