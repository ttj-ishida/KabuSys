CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
Semantic Versioning.

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-04
-------------------

Added
-----
- 初回リリース: KabuSys — 日本株自動売買／データ分析ライブラリを追加。
  - パッケージエントリポイント:
    - src/kabusys/__init__.py にて __version__ = "0.1.0"、主要サブパッケージ（data, research, ai, ...）を公開。

- 設定管理:
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込む自動ロード実装。
      - プロジェクトルート検出: .git または pyproject.toml を探索してルートを特定（CWD 非依存）。
      - ロード順序: OS 環境 > .env.local（override=True） > .env（override=False）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードの無効化が可能（テスト用）。
    - .env 文法パーサ実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
    - Settings クラスを提供（settings インスタンスを公開）。主なプロパティ:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（オプション）
      - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを提供）
      - 監視用ファイルパス（PID_FILE_PATH, KILL_FLAG_PATH 等）
      - リソース閾値（CPU/MEM/DISK）
      - KABUSYS_ENV 検証（development/paper_trading/live）
      - LOG_LEVEL 検証（DEBUG/INFO/...）
      - ヘルパー: is_live / is_paper / is_dev

- データ基盤モジュール:
  - src/kabusys/data/pipeline.py
    - ETLResult データクラスを実装（ETL の取得件数、保存件数、品質問題、エラー収集などを格納）。
    - 差分更新・バックフィル・品質チェックを想定した設計（J-Quants クライアント経由での取得と idempotent 保存を前提）。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult の再エクスポート（public API）。
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー管理機能を実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
      - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバック。
      - カレンダー更新ジョブ calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存を想定）。
    - DuckDB を前提とした日付変換・テーブル存在チェックユーティリティを実装。

- AI（ニュース NLP / レジーム判定）:
  - src/kabusys/ai/news_nlp.py
    - score_news(conn, target_date, api_key=None)
      - raw_news + news_symbols から target_date に対応するニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を集約し、
        銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを取得、ai_scores テーブルへ書き込む。
      - バッチ処理（デフォルト 20 銘柄/回）、1 銘柄あたり最大記事数・文字数トリム、JSON Mode レスポンスのバリデーション、
        429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装。
      - レスポンスの堅牢なパースと検証（未知コードは無視、スコアを ±1.0 にクリップ）。
      - API キー未指定時は例外を送出。
      - 単体テスト向けに _call_openai_api をパッチ可能に設計。
  - src/kabusys/ai/regime_detector.py
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して
        market_regime テーブルへ日次レジーム（bull/neutral/bear）を冪等書き込み。
      - マクロニュース抽出（マクロキーワードでフィルタ）→ OpenAI で JSON レスポンス取得 → スコア合成。
      - API 障害時は macro_sentiment=0.0 として継続（フェイルセーフ）。
      - リトライ/5xx ハンドリング、JSON パース保護、BEGIN/DELETE/INSERT/COMMIT のトランザクション処理。
      - 単体テスト向けに _call_openai_api をパッチ可能に設計。
    - 共通設計方針として、datetime.today()/date.today() を直接参照せず、target_date ベースで動作（ルックアヘッドバイアス防止）。

- リサーチ（ファクター・特徴量探索）:
  - src/kabusys/research/factor_research.py
    - calc_momentum(conn, target_date): mom_1m/3m/6m、ma200_dev を計算（200 行未満は None）。
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。
    - calc_value(conn, target_date): raw_financials から最新の財務データを取得し PER/ROE を計算。
    - DuckDB による SQL とウィンドウ関数利用で効率的に計算。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（デフォルト [1,5,21]）を計算。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン（ランク）相関（IC）を計算。
    - rank(values): 同順位は平均ランクで処理（丸めにより ties を安定検出）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算。
  - src/kabusys/research/__init__.py で主要関数を公開（zscore_normalize を data.stats から再利用）。

- ロバストネス / トランザクション / ロギング:
  - DuckDB への書き込みは可能な限り冪等に設計（DELETE → INSERT、ON CONFLICT を用いる想定）。
  - トランザクション境界（BEGIN/COMMIT/ROLLBACK）を適切に利用。ROLLBACK に失敗した場合は警告ログを出力。
  - API エラーやレスポンスパースエラーは例外直上げではなくフェイルセーフ（ロギングしてデフォルト値を利用）する箇所が多く、部分失敗時にも他データを保護する設計。

- テスト支援:
  - OpenAI 呼び出しを行う内部関数（_call_openai_api）を unittest.mock.patch 等で差し替え可能に設計し、ユニットテストが容易。

Changed
-------
- 初回公開のため該当なし。

Fixed
-----
- 初回公開のため該当なし。

Security
--------
- 初回公開のため該当なし。

Notes / Migration
-----------------
- 本バージョンは初回リリースです。アップグレード手順はありませんが、次点での注意点:
  - OpenAI API キーが必須の機能（score_news, score_regime）は api_key 引数または環境変数 OPENAI_API_KEY のいずれかを設定する必要があります。未設定時は ValueError を送出します。
  - 自動 .env ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで便利）。
  - DuckDB を用いるコードは DuckDB のバージョン差異に影響を受ける箇所（executemany の空リストバインド等）に配慮した実装になっていますが、実環境での互換性確認を推奨します。

Acknowledgments
---------------
- この CHANGELOG はソースコードのドキュメントと docstring から推測して作成されています。動作や API の詳細は各モジュールの docstring / 関数定義を参照してください。