Keep a Changelog
================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のフォーマットに準拠しています。

Unreleased
----------

（現在未リリースの変更はここに記載）

0.1.0 - 2026-03-28
-----------------

初回公開リリース。以下の主要機能・モジュールを追加しました。

Added
-----
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージ公開インターフェースを __all__ で整理（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイル / 環境変数から設定を自動読み込みするローダーを実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント等に対応する堅牢なパーサ実装。
    - override / protected キー概念による上書き制御（OS 環境変数の保護）。
  - Settings クラスを提供。プロパティ経由で以下の設定を取得:
    - J-Quants / kabu ステーション / Slack トークン・チャンネル
    - DB パス（デフォルト: DuckDB → data/kabusys.duckdb, SQLite → data/monitoring.db）
    - KABUSYS_ENV と LOG_LEVEL の検証・変換（許容値チェック）
    - is_live / is_paper / is_dev の便利プロパティ
  - 未設定の必須環境変数は ValueError を送出する明確な挙動。

- AI（自然言語処理）機能 (kabusys.ai)
  - ニュースセンチメントスコアリング (news_nlp.score_news)
    - raw_news, news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI (gpt-4o-mini, JSON mode) にバッチ送信して銘柄別スコアを生成。
    - チャンクサイズ、記事最大数・文字数トリム、リトライ（429/ネットワーク断/5xx）などの堅牢な実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、各要素の code/score 検証）。
    - スコアは ±1.0 にクリップ。
    - 書込みは部分失敗に備え、対象コードのみ DELETE → INSERT（冪等的保存）。DuckDB の executemany 空リスト制約に配慮。
    - テスト容易性: _call_openai_api を patch で差し替え可能。
    - API キー解決は引数または環境変数 OPENAI_API_KEY。未設定時は ValueError。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を公開。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次で market_regime を算出・保存。
    - ma200 計算は look-ahead バイアスを避けるため target_date 未満のデータのみ使用。データ不足時は中立値（1.0 / macro_sentiment=0.0）でフォールバック。
    - OpenAI 呼び出しは独立実装（news_nlp とプライベート関数を共有しない）で、リトライ・エラーハンドリング、JSON パースのフォールバックを実装。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理。失敗時は ROLLBACK して例外を再送出。
    - API キー解決は引数または環境変数 OPENAI_API_KEY。未設定時は ValueError。

- リサーチ / ファクター群 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials から直近財務情報を取得して PER / ROE を算出（EPS が 0/欠損のときは None）。
    - 各関数は prices_daily / raw_financials のみ参照し、外部 API に依存しない設計。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。入力検証（horizons の範囲）あり。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算。有効レコードが 3 未満なら None。
    - rank: 同順位は平均ランクを付与する堅牢なランク関数（丸めで ties 判定の安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計ユーティリティ。
  - research パッケージは data.stats の zscore_normalize を再公開。

- データ基盤 / ETL / カレンダー (kabusys.data)
  - calendar_management:
    - market_calendar を参照した営業日判定ユーティリティ群を実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB にデータがない場合は曜日ベースのフォールバック（土日を非営業日として扱う）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィル、健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを実装（target_date、取得/保存件数、品質問題、エラーなどを格納）。
    - pipeline は差分更新、backfill、品質チェックの設計方針に準拠。
    - data.etl モジュールで ETLResult を再エクスポート。
  - jquants_client との連携フックを想定（fetch / save 関数呼び出しを使用）。

- 実装上の設計方針・品質
  - ルックアヘッドバイアス防止のため、各処理は datetime.today()/date.today() を直接参照せず、target_date ベースで処理する方針を徹底。
  - DuckDB を主体に SQL と Python を組み合わせて処理。DuckDB の互換性問題（executemany 空リスト不可など）に配慮。
  - 外部 API 呼び出しは冗長性（リトライ、指数バックオフ）とフォールバックを想定し、致命的な障害にならない設計。
  - ロギングと警告によって異常・フォールバック事象を明確に記録。
  - テスト容易性: OpenAI 呼び出しやその他外部依存の抽象化（差し替え可能な内部関数）を実装。

Security, Requirements & Notes
-----------------------------
- 必須環境変数（いくつかの機能で必要）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI を利用する機能は OPENAI_API_KEY が必要（score_news / score_regime の引数で注入可）。
- デフォルトの DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
- OpenAI API 呼び出しは gpt-4o-mini を前提とした JSON mode を利用。プロンプト設計により厳密な JSON 応答を期待。
- 初期実装のため、PBR・配当利回りなど一部ファクタは未実装（calc_value の注記参照）。

Breaking Changes
----------------
- 初回リリースのため該当なし。

Acknowledgements / Implementation details
-----------------------------------------
- DuckDB を用いた SQL ウィンドウ関数や移動平均等を多用。
- LLM 連携部分はテスト用に差し替え可能な設計（unittest.mock.patch 想定）。
- 各モジュールの docstring に設計方針・処理フローを詳細に記載。

今後の予定（TODO / roadmap）
----------------------------
- 追加ファクター（PBR、配当利回り等）の実装
- strategy / execution / monitoring の具現化（現在パッケージ構成にエントリは存在）
- 品質チェックモジュール（quality）の拡充と UI/通知連携（Slack 等）強化
- 各種統合テスト・CI の充実

--- 

この CHANGELOG はコードベースから推測してまとめたものです。追加のコミット履歴やリポジトリの実際の変更ログがある場合、それに従って更新してください。