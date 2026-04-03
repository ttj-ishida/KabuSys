CHANGELOG
=========

すべての変更は Keep a Changelog の方針に従って記載しています。
フォーマット: https://keepachangelog.com/ja/

Unreleased
----------

- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-03
-------------------

Added
- 初回リリース。パッケージ名: kabusys（日本株自動売買支援ライブラリ）。
  - パッケージ公開情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py に定義)
    - エクスポート済みサブパッケージ: data, strategy, execution, monitoring（__all__ に記載。各サブパッケージは機能ごとに分離）
- 環境設定管理モジュール (kabusys.config)
  - .env ファイルおよび OS 環境変数の自動読み込み:
    - プロジェクトルートを .git または pyproject.toml から探索して .env, .env.local を読み込む。
    - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は既存の OS 環境変数を上書き可能）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動読み込み無効化対応（テスト用途）。
  - .env パーサ実装:
    - export KEY=val 形式に対応、クォート内のエスケープ処理、インラインコメントの扱い等を考慮した堅牢なパース。
  - Settings クラスを提供（settings インスタンスを公開）。主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須環境変数取得（未設定時は ValueError を送出）
    - DB パス (DUCKDB_PATH / SQLITE_PATH)、監視用ファイルパス、閾値（CPU/MEM/DISK）などのデフォルト取得
    - KABUSYS_ENV の検証（development/paper_trading/live）と便利な is_live / is_paper / is_dev 判定
    - LOG_LEVEL の検証（DEBUG/INFO/...）
- AI モジュール (kabusys.ai)
  - news_nlp: ニュース記事に対するセンチメントスコアリング機能
    - raw_news と news_symbols を集約して銘柄ごとのテキストを作成し、OpenAI（gpt-4o-mini、JSON mode）にバッチ送信してスコアを取得。
    - チャンク処理（デフォルト 20 銘柄/チャンク）、1 銘柄あたりの記事数と文字数上限でトークン肥大化を抑制。
    - 再試行（429/ネットワーク/タイムアウト/5xx）を指数バックオフで行う。
    - レスポンスの厳密なバリデーションと ±1.0 クリップ、JSON 前後ノイズの復元処理を実装。
    - DuckDB 互換性への対応（executemany に空リストを渡さない等）。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
    - calc_news_window(target_date) により JST の指定ウィンドウ（前日 15:00 ～ 当日 08:30 JST）を UTC naive datetime で計算（ルックアヘッド防止）。
    - OpenAI API キー未設定時は ValueError を送出。
  - regime_detector: 市場レジーム判定（bull / neutral / bear）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成。
    - マクロ抽出キーワードを定義し、raw_news から該当タイトルを抽出して LLM に渡す。
    - API の冗長処理（リトライ、5xx 判定、フェイルセーフで macro_sentiment=0.0）や JSON パースの保護を実装。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 1 を返す（成功時）。
    - 設計上、datetime.today()/date.today() を参照せず、target_date ベースで処理（ルックアヘッドバイアス防止）。
  - 両モジュールとも OpenAI 呼び出し部分はテスト容易性のため差替え可能（内部 _call_openai_api を patch で差し替えられる形）。
- Research モジュール (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比）、バリュー（PER/ROE）を DuckDB の prices_daily / raw_financials から計算する関数群を実装。
    - calc_momentum / calc_volatility / calc_value が公開 API。データ不足時は None を返す挙動を明示。
    - SQL ウィンドウ関数を活用した効率的実装。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（指定ホライズン）を一括クエリで取得、ホライズン検証（正の整数かつ <=252）を実施。
    - calc_ic: ファクター値と将来リターンの Spearman（ランク）相関を計算。サンプル数が少ない場合は None。
    - rank / factor_summary: 順位付けと統計サマリー（count/mean/std/min/max/median）を標準ライブラリのみで実装。
    - これらは pandas 等の外部依存を持たない実装。
- Data モジュール (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブル利用）と営業日判定ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベース（土日を非営業日）でフォールバックする設計。
    - calendar_update_job: J-Quants API (jquants_client) から差分取得・バックフィル・健全性チェックを行い、冪等に保存する処理を実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を kabusys.data.etl で再エクスポート）。
    - ETLResult は取得数 / 保存数 / 品質問題 / エラー概要等を保持し、has_errors / has_quality_errors / to_dict を提供。
    - ETL パイプライン (設計) は差分取得・品質チェック・idempotent 保存を行う方針を明記。
  - DuckDB の特性（executemany の空パラメータ問題や日付型の扱い）への互換性考慮が随所に実装。
- テスト・デバッグ面の配慮
  - OpenAI 呼び出し箇所はモック可能（内部関数を patch 可能）でテスト容易性を確保。
  - ロギングを各モジュールで適切に出力（info/debug/warning/exception）。

Changed
- 該当なし（初回リリースのため変更履歴は追加のみ）。

Fixed
- 該当なし（初回リリース）。

Security
- 環境変数の取り扱いにおいて OS 環境変数を保護する設計（.env 読み込み時に既存 OS 環境変数を protected として扱う）。
- OpenAI API キーは引数または環境変数（OPENAI_API_KEY）で注入し、未設定時はエラーにして誤動作を防止。

Notes / 実装上の重要ポイント（設計・互換性）
- ルックアヘッドバイアス防止:
  - LLM を用いる news_nlp / regime_detector、および各種計算関数は内部で datetime.today()/date.today() を参照せず、必ず呼び出し元が指定する target_date を基準に動作する設計。
- OpenAI とのやり取り:
  - gpt-4o-mini を想定、JSON mode（response_format={"type": "json_object"}）での応答を期待。
  - レスポンスパース失敗や API エラー時はフェイルセーフ（部分的に0.0やスキップ）で継続する方針。
- DB 書き込み:
  - DuckDB へは明示的トランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を確保。
  - 一部処理では部分失敗時に既存データを保護するために書き込み対象コードを限定して DELETE → INSERT を行う。
- DuckDB 互換性注記:
  - executemany に空リストを与えると失敗するバージョンがあるため、事前チェックを行ってから実行する実装になっている。
- ロバストネス:
  - LLM 呼び出し・外部 API 呼び出しの多くでリトライ（指数バックオフ）を実装。致命的でないエラーはログ記録のうえ処理継続。

開発者向けメモ
- OpenAI 呼び出しの差し替え:
  - テスト時は unittest.mock.patch を用いて kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を差し替えてください。
- 環境変数自動ロードはパッケージ読み込み時に行われるため、テストや一時的な設定変更時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑制できます。

--- 

今後の予定（非網羅）
- strategy / execution / monitoring の具体実装（現時点ではパッケージの公開名のみ存在）。
- 追加の品質チェックモジュール（kabusys.data.quality）や J-Quants クライアントの詳細実装拡充。