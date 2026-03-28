CHANGELOG
=========

すべての重要な変更点を時系列で記載します。本プロジェクトは Keep a Changelog の形式に準拠しています。

[Unreleased]
------------

- なし

0.1.0 - 2026-03-28
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
    - 公開モジュール候補として data, strategy, execution, monitoring を __all__ に登録。

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env / .env.local 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env パーサを実装（コメント、export プレフィックス、シングル・ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等に対応）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを導入しアプリケーション設定を型付きプロパティで提供（必須項目は _require により ValueError を送出）。
  - 設定例:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV 検証（development / paper_trading / live のみ許容）
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容）

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini、JSON Mode）でセンチメント評価を行い ai_scores テーブルへ書き込む処理を実装。
    - 主な特徴:
      - ニュースウィンドウ: JST 前日 15:00 ～ 当日 08:30（内部は UTC naive で扱う）。
      - 1銘柄あたり最大記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトークン膨張を抑制。
      - 1回の API 呼び出しで最大 20 銘柄をバッチ処理（チャンク単位）。
      - 429・ネットワーク・タイムアウト・5xx に対する指数バックオフ/リトライ。
      - JSON レスポンスの厳密バリデーションと部分成功の取り扱い（有効なコードのみ書き換え、部分失敗時に他銘柄の既存スコアを保護）。
      - テスト用に _call_openai_api をモック可能。
      - フェイルセーフ: API 失敗時は該当チャンクをスキップして処理継続。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出し market_regime テーブルへ冪等書き込みする機能を実装。
    - 主な特徴:
      - MA200 の算出は target_date 未満のデータのみを使用（ルックアヘッドバイアス回避）。
      - マクロニュースは news_nlp.calc_news_window で算出されるウィンドウから取得。
      - OpenAI（gpt-4o-mini）を使用、429/ネットワーク/タイムアウト/5xx に対するリトライ・フォールバック（API失敗時 macro_sentiment=0.0）。
      - 計算結果は regime_score を -1.0〜1.0 でクリップし、閾値に基づきラベル付与。
      - DB 書込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理、失敗時は ROLLBACK。

- Data モジュール (src/kabusys/data)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを利用した営業日判定ユーティリティを実装。
    - 提供する関数:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - 設計上の挙動:
      - market_calendar 未取得時は曜日ベース（土日休場）でフォールバック。
      - DB 登録値優先、未登録日は曜日ベースで補完し next/prev_trading_day 等と一貫性を確保。
      - calendar_update_job: J-Quants API から差分取得→保存（バックフィル、健全性チェック含む）。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（src/kabusys/data/etl.py で再エクスポート）。
    - ETL の設計/ユーティリティを実装:
      - 差分更新ロジック、バックフィル、品質チェック（quality モジュールとの連携想定）、DB 存入用ヘルパーなど。
      - DuckDB 互換性考慮（_table_exists、_get_max_date など）。
    - ETLResult: 実行結果の構造化（品質問題やエラーメッセージの収集／辞書化機能を含む）。

- Research モジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER、ROE）を prices_daily / raw_financials を用いて計算する関数群を実装:
      - calc_momentum, calc_volatility, calc_value
    - DuckDB を用いた SQL ベース計算で、データ不足時の None 処理やログ出力を行う設計。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、統計サマリー（factor_summary）、rank ユーティリティを実装。
    - 外部依存を持たず標準ライブラリのみで実装（pandas 等に依存しない）。

- パッケージ API の調整
  - ai パッケージの公開関数 score_news を __all__ に追加（src/kabusys/ai/__init__.py）。
  - research パッケージでの主要関数を __all__ で再エクスポート（計算ユーティリティの公開）。

Changed
- 設計方針を強調
  - 多くのモジュールで「datetime.today()/date.today() を直接参照しない」方針を採用し、ルックアヘッドバイアスを回避する設計に統一。
  - API 呼び出し失敗時のフェイルセーフ（スコアの 0.0 フォールバックやチャンクスキップ）を徹底。

Fixed
- 初回リリースのため特別なバグ修正の履歴はなし（実装時点での注意点や互換性注記をコード内に記載）。

Security
- 特になし

Notes（開発者向け）
- OpenAI API を利用する機能（ai.news_nlp.score_news, ai.regime_detector.score_regime）は OPENAI_API_KEY の設定が必須（api_key 引数で注入も可能）。
- .env 自動ロードはパッケージ初期化時に行われるため、テストや一時的に無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB 関連の executemany は空リスト渡しが禁止のバージョンがあるため、空チェックを行ってから実行する実装になっている点に注意。
- テスト容易性のため、AI 呼び出し部分はモック差替えが可能（各モジュールの _call_openai_api を patch 可能）。

Breaking Changes
- なし（初回リリース）

--- 

この CHANGELOG はソースコードからの機能・設計意図を基に推測して作成しています。実際のリリースノートはプロジェクトのリリース方針に合わせて適宜編集してください。