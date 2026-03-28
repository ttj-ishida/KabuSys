CHANGELOG
=========

すべての日付は yyyy-mm-dd 形式で記載しています。

[Unreleased]
------------

- なし（初回リリースは 0.1.0）

[0.1.0] - 2026-03-28
--------------------

Added
- パッケージ初期リリース "kabusys"（バージョン 0.1.0）。
  - パッケージ基礎
    - src/kabusys/__init__.py によるパッケージ公開（data, strategy, execution, monitoring をエクスポート）。
  - 設定 / 環境変数管理（src/kabusys/config.py）
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを追加。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応（テスト用）。
    - .env パーサーは export KEY=val 形式・クォート・インラインコメントを適切に処理。
    - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / システム設定（env, log_level）を環境変数から取得。必須変数未設定時は ValueError を送出。
    - デフォルト DuckDB/SQLite パスを設定（data/kabusys.duckdb, data/monitoring.db）。
    - KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL のバリデーションを実装。
  - AI モジュール（src/kabusys/ai）
    - ニュース NLP（src/kabusys/ai/news_nlp.py）
      - raw_news / news_symbols を元に銘柄別ニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメントを評価して ai_scores テーブルへ書き込む機能を実装。
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を提供。
      - バッチ処理（最大 20 銘柄 / 回）、1 銘柄あたりの記事上限・文字数トリム、レスポンス検証、スコア ±1.0 のクリップを実装。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライ、API失敗時のフォールバック（該当チャンクをスキップ）を実装。
      - DuckDB への書き込みは冪等（DELETE → INSERT）で、部分失敗時に他銘柄の既存スコアを保護。
      - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api のモック化を想定）。
    - 市場レジーム検出（src/kabusys/ai/regime_detector.py）
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出・保存する score_regime を提供。
      - prices_daily / raw_news を参照し、計算はルックアヘッドバイアスを防ぐ設計（target_date 未満のみ使用）。
      - OpenAI 呼び出しはリトライ・フォールバック（失敗時は macro_sentiment = 0.0）を行う。レスポンス JSON のパース失敗や非致命的エラーも安全に扱う。
      - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理、失敗時は ROLLBACK を試行して例外を上位へ伝播。
  - Data モジュール（src/kabusys/data）
    - カレンダー管理（src/kabusys/data/calendar_management.py）
      - JPX マーケットカレンダーの管理ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供）。
      - market_calendar が未取得のときは曜日ベース（土日非取引）でフォールバックする堅牢な設計。
      - 夜間バッチ更新 job（calendar_update_job）で J-Quants から差分取得し保存（バックフィル、健全性チェックを含む）。
      - DuckDB 取り扱い時の型変換ユーティリティやテーブル存在チェックを実装。
    - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
      - ETLResult dataclass による ETL 結果集約（取得件数、保存件数、品質問題リスト、エラーメッセージ等）。
      - 差分更新・バックフィル・品質チェックの方針を定義。jquants_client および quality モジュールと連携する設計。
      - etl モジュールで ETLResult を公開（再エクスポート）。
  - Research モジュール（src/kabusys/research）
    - factor_research（src/kabusys/research/factor_research.py）
      - Momentum（1m/3m/6m リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）を prices_daily / raw_financials から計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
      - データ不足時の None 扱いや、DuckDB を使ったウィンドウ関数による実装。
    - feature_exploration（src/kabusys/research/feature_exploration.py）
      - 将来リターン計算（calc_forward_returns）: 任意のホライズン（デフォルト [1,5,21]）に対応。
      - IC（Spearman の ρ）計算（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
      - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。
    - research パッケージの __all__ を設定し主要 API を再公開。
  - ロギングと堅牢性
    - 各モジュールで詳細なログ（info/debug/warning）が追加されており、API エラー時に例外を無闇に投げずデグレード動作（フェイルセーフ）を行う設計。
    - DB 書き込みはトランザクションで保護（COMMIT / ROLLBACK の試行）。
    - テストを想定した差し替えポイント（OpenAI 呼び出し等）を用意。

Notes / Usage
- 必須環境変数（いずれも未設定時は Settings のプロパティで ValueError を送出）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- OpenAI 利用:
  - score_news / score_regime は OPENAI_API_KEY（環境変数）または api_key 引数で API キーを受け付ける。未設定時は ValueError。
  - API 呼び出しは gpt-4o-mini を想定し JSON mode での返却を期待。
- DuckDB を前提:
  - 各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取り、prices_daily / raw_news / market_calendar / raw_financials / ai_scores 等のテーブルを操作する。
- 日付の取り扱い:
  - すべてのスコア計算等で明示的に target_date を引数で受け取り、datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス防止）。
- 互換性 / 注意点:
  - DuckDB の executemany に空リストを渡すとエラーになる既知の挙動を考慮している（空チェックしてから executemany を呼ぶ）。
  - jquants_client / quality モジュールの存在を前提にしている（ETL の実行にはこれらの実装が必要）。

Breaking Changes
- 初回リリースのため破壊的変更は無し。

Security
- API キー・パスワード類は .env（又は環境変数）で管理する想定。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

Acknowledgements / Implementor Notes
- OpenAI 呼び出しや外部 API の失敗に対してフェイルセーフで継続する設計とし、部分失敗時に既存データを保護する戦略を採用。
- テスト容易性のため、外部との通信箇所は差し替え可能に実装。