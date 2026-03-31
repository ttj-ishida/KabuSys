Keep a Changelog
=================

すべての重大な変更はこのファイルに記載します。  
このプロジェクトは "Keep a Changelog" の慣習に従います。  

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-31
-------------------

初回リリース — 基本機能の実装

Added
- パッケージ初期公開: kabusys v0.1.0
  - パッケージエントリポイント: src/kabusys/__init__.py（__version__ = 0.1.0、主要サブパッケージを __all__ で公開）
- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動読み込み
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応（テスト用）
  - export 形式、クォート文字列、インラインコメントの正しいパース処理
  - 既存 OS 環境変数の保護（protected set）の仕組み
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 実行環境ログレベル等のプロパティを取得
  - env / log_level のバリデーション（許容値チェック）と is_live / is_paper / is_dev の簡易判定
- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄毎のニュースを OpenAI（gpt-4o-mini）に渡しセンチメントを算出
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、記事数/文字数トリム、JSON mode を使用
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ付きリトライ実装
    - レスポンスの厳密バリデーション（JSON抽出、results フォーマット検証、コード照合、数値検査）
    - スコアは ±1.0 にクリップ、ai_scores テーブルへ冪等的に書き込み（対象コードのみ DELETE → INSERT）
    - calc_news_window ユーティリティ（JST ウィンドウを UTC naive datetime に変換）
  - レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して
      日次で市場レジーム（bull / neutral / bear）を判定
    - prices_daily から ma200_ratio を算出（ルックアヘッド防止のため target_date 未満のみ使用）
    - マクロニュースを抽出して LLM（gpt-4o-mini）に渡し macro_sentiment を取得。API 失敗時は 0.0 にフォールバック
    - レジームスコアを合成して market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - OpenAI 呼び出しに対するリトライ、5xx と非5xx の扱い分離、レスポンスパース失敗は警告ログで継続
- データモジュール（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを参照した営業日判定 API を提供
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - market_calendar が無い場合の曜日ベースフォールバック（週末を非営業日扱い）
    - DB に一部データしかない場合でも一貫性を保つ設計（DB 値優先、未登録はフォールバック）
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存、バックフィル／健全性チェック実装
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを提供（取得件数・保存件数・品質問題・エラーの集約）
    - 差分取得、バックフィル、品質チェックの骨子設計（jquants_client と quality モジュールを利用）
    - DuckDB を前提としたテーブル存在チェック、最大日付取得ユーティリティ実装
- リサーチ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を算出
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を算出
    - calc_value: raw_financials から最新財務データを結び付けて PER / ROE を算出
    - DuckDB 上の SQL を用いた実装、外部 API に依存しない設計
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 任意ホライズンの将来リターン計算（デフォルト [1,5,21]）
    - calc_ic: スピアマンランク相関（IC）計算（欠損・同値処理・最小件数チェックあり）
    - rank: 同順位は平均ランクにするランク関数（丸めで ties 検出精度向上）
    - factor_summary: count/mean/std/min/max/median の統計要約を標準ライブラリのみで実装
  - research パッケージ __init__ で zscore_normalize を re-export
- 共通設計・実装上の配慮
  - ルックアヘッドバイアス回避: datetime.today()/date.today() を直接利用しない設計（target_date を明示的に渡す）
  - DuckDB を主要なローカル分析 DB として利用（型変換ユーティリティ等を実装）
  - OpenAI 呼び出しに対して堅牢なリトライ/フォールバックを実装（API 失敗時は例外で停止させずスキップや 0.0 を返す等のフェイルセーフ）
  - DB 書き込みは冪等性を考慮（該当日・該当コードのみ DELETE → INSERT する等）し、部分失敗時に他データを保護
  - DuckDB バージョン固有の挙動（executemany の空パラメータ制限等）への対応を明記

Changed
- （該当なし、初回提供）

Fixed
- （該当なし、初回提供）

Security
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を利用する形で外部に依存。
  - 設定管理 (Settings) により必須キー未設定時は ValueError を送出し注意喚起する実装。

Notes / Requirements
- 依存:
  - duckdb
  - openai（OpenAI Python SDK）
  - jquants_client 相当のラッパー（data.jquants_client から呼び出す想定）
- テスト向け設計:
  - OpenAI 呼び出し部分はモジュール内部関数を patch して差し替え可能（unittest.mock 等）
  - 環境変数自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能

Contributing
- バグ報告・機能要望は issue を立ててください。将来的に CHANGELOG の Unreleased セクションを活用して変更のトラッキングを行います。