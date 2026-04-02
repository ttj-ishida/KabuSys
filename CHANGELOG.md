CHANGELOG
=========

すべての重要な変更点をここに記録します。フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-02
--------------------

Added
- 基本パッケージ初回リリース: kabusys v0.1.0
  - パッケージ公開情報
    - パッケージトップで __version__ = "0.1.0" を定義。パッケージの公開 API は data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは実行環境の環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み（OS 環境変数を保護）。
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
    - .env のパースは export KEY=val、引用符・バックスラッシュエスケープ、行内コメント等に対応。
  - 必須設定取得用の _require と、各種プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などを必須に設定。
    - KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、PID_FILE_PATH、閾値（CPU/MEM/DISK）、LOG_LEVEL、KABUSYS_ENV（development / paper_trading / live） などの既定値とバリデーションを提供。
  - 開発・ペーパー・本番フラグ（is_dev / is_paper / is_live）を提供。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini、JSON mode）で銘柄ごとのセンチメント ai_score を算出して ai_scores テーブルに保存する機能を実装（score_news）。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）の計算機能 (calc_news_window) と記事集約処理 (_fetch_articles) を提供。
    - バッチサイズ制御（最大 20 銘柄 / チャンク）、記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を実装。
    - API 呼び出しの堅牢化: レート制限（429）・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ、自動スキップ（フェイルセーフ）。
    - レスポンスの厳格なバリデーションとスコアの ±1.0 クリップ。
    - テスト容易性: _call_openai_api をパッチしてモック可能な設計。
    - DuckDB に対する冪等書き込み（DELETE→INSERT）を採用し、部分失敗時に既存スコアを保護。DuckDB 0.10 の executemany 空リスト制約に配慮。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - prices_daily からの ma200_ratio 計算、raw_news からマクロキーワード抽出、OpenAI（gpt-4o-mini）でのセンチメント評価を統合。
    - レジームスコア合成式、閾値（BULL_THRESHOLD / BEAR_THRESHOLD）によるラベル付け。
    - API 呼び出し失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等パターン。失敗時は ROLLBACK を試行して上位へ例外を伝播。
    - テスト容易性: news_nlp とは独立した _call_openai_api 実装でモジュール結合を抑制。

- データプラットフォーム機能 (kabusys.data)
  - ETL パイプライン基盤 (kabusys.data.pipeline / ETLResult)
    - ETL 実行結果を表す dataclass ETLResult を追加。
    - 差分更新、バックフィル、品質チェック（quality モジュールと連携）等の設計を実装するための基盤を整備。
    - DuckDB に対するテーブル存在確認・最大日付取得等のユーティリティを用意。
  - ETL の公開インターフェース (kabusys.data.etl)
    - pipeline.ETLResult を再エクスポート。
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを用いた営業日判定ロジックと夜間バッチ更新 job（calendar_update_job）を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar 未取得時の曜日ベースのフォールバック、DB 値優先の一貫性、検索範囲上限 (_MAX_SEARCH_DAYS) を実装。
    - J-Quants クライアント経由で差分取得・保存（fetch_market_calendar / save_market_calendar を想定）を行う calendar_update_job を提供。
    - バックフィルと健全性チェック（先方の日付が過剰に未来の場合スキップ）を実装。

- リサーチ／ファクター計算 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1m/3m/6m リターン、ma200 乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials に基づく PER / ROE を計算（target_date 以前の最新財務データを使用）。
    - DuckDB を用いた SQL 中心の実装で、欠損やデータ不足時に None を返す仕様。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons 入力検証あり。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足（<3 件）では None を返す。
    - rank: 平均ランク方式（同順位は平均ランク）を正確に計算するユーティリティ。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算する統計サマリー。

- その他
  - モジュール境界・テストフレンドリ設計:
    - OpenAI 呼び出し箇所（_call_openai_api 等）を明示的に分離してモックしやすい設計。
  - DuckDB を主要なストレージ層として想定し、SQL と Python を組み合わせて計算・集計を実行する設計方針を明示。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 環境変数ベースで API キー等を管理する設計。必須トークンが未設定の場合は ValueError を返して明示的に失敗する（例: OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、SLACK_BOT_TOKEN 等）。

Notes / Implementation details
- OpenAI API を利用する機能は gpt-4o-mini と JSON mode を前提としており、API レスポンスの不確実性に対して堅牢なバリデーションとフォールバック（0.0）の取り扱いを採用。
- DuckDB のバージョン差異（executemany の空配列バインド問題など）に実運用を考慮して実装している。
- 日付処理はルックアヘッドバイアスを避けるため、datetime.today() / date.today() を直接参照しない方針（target_date を明示的に受け取る API が中心）。
- さらに詳細な設計・仕様は各モジュールの docstring（ソース内コメント）に記載。

今後の予定（例）
- strategy / execution / monitoring モジュールの具体的な実装と統合テストの追加。
- 監視・アラート（Slack）連携の実運用調整。
- ETL の品質チェック（quality モジュール）の実装拡充と自動テスト。

--- 

この CHANGELOG はソースコード内の docstring・実装から推測して作成しています。より正確な履歴はコミットログ・リリースノートと合わせて更新してください。