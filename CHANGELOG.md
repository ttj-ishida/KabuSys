CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。
全ての注記はコードベース（src/kabusys 以下）の現状から推測して作成しています。

なお、本リリースはパッケージの __version__ に基づく初期バージョン v0.1.0 として記載します。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-29
-------------------

Added
- 基本パッケージ
  - パッケージ初期化: kabusys パッケージを作成。__version__ = "0.1.0"、主要サブパッケージを __all__ で公開（data, research, ai, ...）。
- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダー実装。
    - プロジェクトルート検出：__file__ から上位ディレクトリを探索し .git または pyproject.toml を検出。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーは export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得可能。
    - 必須環境変数取得時の検証（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - デフォルト値・パス展開（DUCKDB_PATH, SQLITE_PATH 等）。
    - KABUSYS_ENV / LOG_LEVEL の検証と is_live/is_paper/is_dev のユーティリティプロパティ。
- AI モジュール（kabusys.ai）
  - ニュースセンチメント（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - バッチサイズや記事数・文字数上限（トークン肥大化対策）を定義（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK 等）。
    - OpenAI 呼び出しは JSON Mode（response_format）を利用し、結果の厳密な JSON 検証を実施。
    - 再試行（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実装。非リトライ対象はスキップしてフェイルセーフに継続。
    - レスポンス検証を行い、未知コードの無視、スコアの ±1.0 クリップ等を実施。
    - score_news(conn, target_date, api_key=None) を公開。書き込みは部分置換（DELETE→INSERT）で冪等性と部分失敗耐性を確保。
    - 単体テスト容易化のため、内部の OpenAI 呼び出し関数を patch で差し替え可能な設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して
      日次で market_regime テーブルへ書き込み（score_regime）。
    - マクロニュース抽出のためのキーワード群を定義し、最大記事数や閾値を設定。
    - OpenAI 呼び出しに対するリトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0 として継続）。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等操作で実装し、失敗時は ROLLBACK を行う。
    - lookahead バイアスを避ける設計（date 引数ベース、datetime.today() を参照しない）。
- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX マーケットカレンダーを扱うユーティリティ群を提供。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定 API。
    - market_calendar が未取得の場合は曜日ベース（平日のみ営業日）でフォールバック。
    - 最大探索範囲や健全性チェック、バックフィル（_BACKFILL_DAYS）などを実装。
    - calendar_update_job(conn, lookahead_days=...) を実装し、J-Quants から差分取得して保存（fetch_market_calendar / save_market_calendar を利用、冪等保存）。
  - ETL パイプライン（kabusys.data.pipeline, etl）
    - ETL の結果を表す ETLResult dataclass を実装（取得数、保存数、品質問題、エラー一覧等を格納）。
    - 差分取得、backfill、品質チェック（quality モジュールとの連携）を行う設計。
    - 内部ユーティリティ: テーブル存在確認、最大日付取得など。
    - kabusys.data.etl から ETLResult を再エクスポート。
- リサーチ / ファクター（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、ma200 乖離（ma200_dev）を計算（prices_daily を利用）。
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金等を計算。
    - calc_value(conn, target_date): raw_financials と prices_daily を組み合わせ PER / ROE を計算（最新財務レコードを target_date 以前から取得）。
    - 全関数は不足データに対して None を返す方針。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns(conn, target_date, horizons): 将来リターンを複数ホライズンで一度に計算。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）計算。
    - rank(values): 同順位は平均ランクにするランク付け（小数丸めで ties の誤差対策）。
    - factor_summary(records, columns): count/mean/std/min/max/median を算出する統計サマリー。
- 実装上の共通設計方針（全体）
  - ルックアヘッドバイアス防止：日付参照は外部からの target_date パラメータに依存し、datetime.today()/date.today() の参照を最小化（一部バッチで今日参照あり）。
  - DuckDB を主要な組み込み DB として扱う SQL ベース実装。
  - DB 書き込みは冪等性を意識（DELETE→INSERT、ON CONFLICT 方針、バックアップのための部分書き換え等）。
  - OpenAI 呼び出しは JSON Mode を使い、レスポンスの厳密なバリデーションを行う。
  - API 呼び出しはリトライ・バックオフ・フェイルセーフの設計で運用耐性を確保。
  - テスト容易性: API キー注入や内部 _call_openai_api の patch による差し替えポイントを用意。

Changed
- 初リリースのため該当なし。

Fixed
- 初リリースのため該当なし。

Security
- 環境変数の取り扱いにおいて、OS の既存環境変数を保護するため protected set を導入して .env の上書きを制御。
- .env ファイル読み込み時にファイル読み取り失敗で警告を出す実装。

Notes / 注意点
- OpenAI の API キーは api_key 引数で注入可能。指定がない場合は環境変数 OPENAI_API_KEY を参照する仕様で、未設定時は ValueError を送出して利用者へ明示する。
- DuckDB の executemany に空リストを渡せないバージョン互換性に配慮した実装（空チェックを行ってから executemany を実行）。
- 日時は基本的に timezone-naive な datetime / date を使用（UTC 側での保存や JST→UTC 変換の記述あり）。運用時は取り扱いに注意。
- 一部のバッチ処理（calendar_update_job 等）は date.today() を参照するため、完全な再現性を得るには実行時の環境日付に依存する。

参考（公開された主要パブリック関数 / クラス）
- settings: kabusys.config.settings
- AI:
  - score_news(conn, target_date, api_key=None)
  - score_regime(conn, target_date, api_key=None)
- Data:
  - calendar_update_job(conn, lookahead_days=...)
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - ETLResult（kabusys.data.pipeline.ETLResult）
- Research:
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / rank / factor_summary

今後の予定（推測）
- 監視・実行（execution / monitoring）モジュールの実装・公開
- デプロイ時の設定・ドキュメント整備、CI テストの充実
- PBR・配当利回りなどバリューファクターの追加実装
- OpenAI レスポンスのより強固な検証とエラー集計の強化

以上。