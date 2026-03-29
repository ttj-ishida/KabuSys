CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and uses Semantic Versioning.

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージルートでの公開 API を定義（src/kabusys/__init__.py: __version__ = "0.1.0", __all__ に主要サブパッケージ名を指定）。
- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local を自動読み込み（OS 環境変数を優先、.env.local は .env をオーバーライド）。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグ対応。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント（スペース/タブ前の # をコメントと認識）をサポート。
  - ファイル読み込み失敗時は警告を出力して継続。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の設定をプロパティで取得。必須項目未設定時は ValueError を発生。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）とユーティリティプロパティ（is_live / is_paper / is_dev）。
- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）の JSON mode を使って銘柄ごとのセンチメント（-1.0〜1.0）を計算して ai_scores テーブルへ書き込む。
    - バッチ処理（1回あたり最大 20 銘柄）、記事数・文字数のトリム（最大記事数/最大文字数）、レスポンスバリデーション、スコアのクリップ（±1.0）を実装。
    - 429・ネットワーク切断・タイムアウト・5xx に対する指数バックオフリトライ、非リトライエラーではスキップ（フェイルセーフ）する設計。
    - ルックアヘッドバイアスを避けるため、内部で datetime.today()/date.today() を直接参照しないタイムウィンドウ計算を採用（calc_news_window）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（LLM、重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込みする。
    - マクロニュースは raw_news からキーワード（日本／米国・グローバルの主要語）でフィルタして取得、記事がない場合は LLM を呼ばず macro_sentiment=0.0。
    - OpenAI 呼び出しは JSON パースや API エラーに対して堅牢なフォールバック（マクロ評価失敗時は 0.0 を採用）を実装。
    - LLM クライアント呼び出しはモジュール内プライベート実装として分離（テストの差し替え容易化）。
- データ基盤（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar）を前提とした営業日判定ユーティリティを提供: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - DB 登録がない日については曜日ベース（土日非営業日）でフォールバック。DB 登録ありの場合は DB 値を優先。
    - 夜間バッチ calendar_update_job を実装（J-Quants クライアント経由で差分取得・バックフィル・健全性チェック・冪等保存の呼出し）。
    - 探索範囲上限（_MAX_SEARCH_DAYS）など無限ループ回避の安全策を導入。
  - ETL パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラーの集約、to_dict の提供）。
    - 差分取得・バックフィル方針、品質チェック（quality モジュール）との連携設計を記載。
    - DuckDB を用いたテーブル存在チェック・最大日付取得ユーティリティを実装。
    - data/etl.py で ETLResult を再エクスポート。
  - jquants_client を利用する想定で API 取得・保存の呼び出しを分離（実装は外部モジュール想定）。
- Research（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）を DuckDB の prices_daily / raw_financials から計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時は None を返す等の安全な取り扱い。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応・入力バリデーション）。
    - IC（Information Coefficient）計算（calc_ic、スピアマンランク相関）、ランク付けユーティリティ（rank）。
    - 統計サマリー（factor_summary）を実装。
  - research パッケージ __init__ で主要関数を公開し、data.stats の zscore_normalize を再エクスポート。
- その他
  - 各所で DuckDB を想定した SQL とトランザクション（BEGIN / DELETE / INSERT / COMMIT / ROLLBACK）による冪等書き込みパターンを採用。
  - 多くの処理で「ルックアヘッドバイアス回避」の方針が明記され、日付取り扱いが慎重に設計されている。
  - OpenAI 呼び出しは gpt-4o-mini を想定し、JSON Mode を利用する設計。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Security
- OpenAI API キー、J-Quants トークン、Kabu API パスワード、Slack トークン等の機密情報は環境変数で取得する設計。Settings クラスは必須値未設定時に早期にエラーを出すため、運用上の秘密管理が必要。

Notes / Migration
- 本リリースは初期実装のため、将来的な API 名変更やテーブルスキーマの変更が発生する可能性があります。ETLResult や DB 書き込みロジックは部分失敗時に既存データの保護を意識した実装になっていますが、DB スキーマの変更時は該当処理の更新が必要です。
- OpenAI 呼び出しをモック化するための _call_openai_api の差し替えポイントが用意されています（テスト容易化）。

Acknowledgements
- 本リリースは DuckDB と OpenAI API（gpt-4o-mini）を前提に設計されています。