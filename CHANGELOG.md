CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。本プロジェクトは Keep a Changelog の形式に準拠しており、セマンティックバージョニングを採用します。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初期公開: kabusys 0.1.0
  - パッケージメタ情報: __version__ = "0.1.0" を定義。
- 環境設定管理モジュール（kabusys.config）を追加
  - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサ実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント判別）。
  - .env 読み込み時の override / protected（OS 環境変数を保護）機能。
  - 必須環境変数を検証する _require と Settings クラスを提供（J-Quants、kabu API、Slack、DB パス、環境モード、ログレベル等）。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェックと便宜プロパティ（is_live / is_paper / is_dev）。
- AI 関連モジュール（kabusys.ai）
  - news_nlp: ニュースから銘柄ごとのセンチメントを取得し ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（JST 基準） calc_news_window を提供。
    - 記事集約（銘柄ごと、記事数・文字数でトリム）、チャンク（最大 20 銘柄）で OpenAI に送信。
    - OpenAI への JSON Mode 呼び出し、レスポンス検証、スコアの ±1.0 クリップ、部分成功時に既存スコアを保護する差分書き込み（DELETE → INSERT）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装。
  - regime_detector: ETF(1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次市場レジーム（bull/neutral/bear）を算出・保存。
    - ma200_ratio の算出、マクロ記事抽出、OpenAI 呼び出し、重み付け合成、冪等的な market_regime テーブルへの書き込みを実装。
    - API 失敗時に macro_sentiment=0.0 とするフェイルセーフ。
  - 両モジュールとも OpenAI 呼び出し部を専用関数化してテスト時にモック差し替え可能に設計。
- データ処理モジュール（kabusys.data）
  - calendar_management: JPX カレンダー（market_calendar）を扱うユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 登録値優先、未登録は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新（バックフィル / 健全性チェック含む）。
  - pipeline / etl:
    - ETLResult データクラスによる ETL 結果の集約（品質チェック結果やエラー一覧を含む）。
    - 差分取得・保存・品質チェックを想定した設計（backfill_days、_MIN_DATA_DATE 等の定数定義）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。
  - jquants_client 経由のデータ取得/保存を想定した設計（fetch/save 抽象化）。
- リサーチモジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）等を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials と価格を組み合わせて PER / ROE を算出（EPS が 0 または欠損時は None）。
    - DuckDB 上の SQL を活用した効率的な実装。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。horizons のバリデーションあり。
    - calc_ic: スピアマンのランク相関（IC）を実装。データ不足時は None。
    - rank / factor_summary: 同順位平均ランク、カラム別統計量（count/mean/std/min/max/median）を算出。
  - 全体的に外部ライブラリに依存せず標準ライブラリ + DuckDB で完結する設計。
- 汎用設計・運用面の配慮
  - ルックアヘッドバイアス防止のため、各処理は datetime.today() / date.today() を参照せず、明示的な target_date を受け取る設計。
  - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等化、失敗時は ROLLBACK を試行して警告ログを出力。
  - OpenAI 呼び出し時の再試行、レスポンスパース失敗時の安全フォールバック、そしてログ出力による障害追跡性向上。
  - DuckDB の executemany における空リスト制約に対応する事前チェック（空のときは実行しない）。

Changed
- （初版のため該当なし）

Fixed
- DuckDB に関する運用上の注意点を考慮して実装
  - executemany に空リストを渡せない制約に対する防御的実装（空チェックを導入）。
  - market_calendar / raw_news / ai_scores 等のテーブルが未作成または空の場合の安全ハンドリングとログ通知。

Security
- 環境変数の自動読み込み時に OS 環境変数を保護する仕組みを導入（protected set）。

Notes / Known limitations
- OpenAI API（gpt-4o-mini）への依存がある。API キーは引数または環境変数 OPENAI_API_KEY で供給する必要がある。API 呼び出し失敗時はフェイルセーフ（スコア 0.0 や処理スキップ）で継続する設計だが、厳密な再現性を求める場合は API の可用性に依存する。
- 一部関数は DuckDB 上のテーブル構造（カラム名・データ型）を前提としているため、スキーマ変更時は対応が必要。
- News/NLP の出力は LLM に依存するため、レスポンス形式の逸脱を想定した検証ロジックを備えるが、想定外パターンによりスコア化がスキップされる可能性がある。

作者
- kabusys チーム

Acknowledgements
- 本リリースは DuckDB と OpenAI API を主要依存先として設計されています。