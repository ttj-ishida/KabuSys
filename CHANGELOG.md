CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows Semantic Versioning.

テンプレート
-----------

- フォーマット: Keep a Changelog 準拠
- バージョニング: SemVer

Unreleased
----------

（なし）

0.1.0 - 2026-04-04
------------------

初期リリース。以下の主要機能群を実装・公開しました。

Added
- パッケージ初期化
  - パッケージバージョンを src/kabusys/__init__.py にて __version__="0.1.0" として定義。
  - public API のエクスポート候補として ["data", "strategy", "execution", "monitoring"] を列挙（将来的なモジュール拡張を想定）。

- 環境設定管理
  - src/kabusys/config.py: 環境変数・設定管理モジュールを追加。
    - .env / .env.local ファイルの自動読み込み（プロジェクトルートは .git または pyproject.toml から探索）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env パーサは export KEY=val 形式、クォート、エスケープ、行末コメント処理に対応。
    - 既存 OS 環境変数の保護（protected set）により誤って上書きしない挙動を実装。
    - Settings クラスを公開（settings）し、主要設定値をプロパティで提供：
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須、未設定時は ValueError）
      - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
      - LINE 関連設定、DB パス（DUCKDB_PATH/SQLITE_PATH）、監視用ファイルパスや閾値（CPU/MEM/DISK）
      - KABUSYS_ENV 値検証（development / paper_trading / live のみ許容）
      - LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - ユーティリティプロパティ is_live / is_paper / is_dev

- AI（ニュース NLP・レジーム検出）
  - src/kabusys/ai/news_nlp.py: ニュース記事のセンチメントスコアリング機能を追加。
    - raw_news、news_symbols を集約して銘柄ごとにテキストを準備。
    - OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信（バッチサイズ上限 20 銘柄）。
    - 1銘柄あたりの記事数・文字数上限でトリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - レスポンスの堅牢なバリデーションと数値変換、±1.0 でクリップして ai_scores テーブルへ書き込み（DELETE→INSERT の冪等処理）。
    - テスト容易性: OpenAI 呼び出し箇所は _call_openai_api を介しており、unittest.mock.patch で差し替え可能。
    - 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で計算。lookahead バイアス回避のため datetime.today() を直接参照しない設計。

  - src/kabusys/ai/regime_detector.py: 市場レジーム判定（bull/neutral/bear）を追加。
    - ETF 1321（日経225連動ETF）の 200 日 MA 乖離（重み 70%）とマクロセンチメント（重み 30%）を合成。
    - マクロセンチメントは news_nlp の記事集約に基づき OpenAI により JSON で取得。
    - レジームスコア合成後、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API エラー・パースエラー時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - OpenAI API のリトライ処理（RateLimit/接続/TIMEOUT/5xx）を実装。
    - lookahead バイアス防止設計（prices_daily クエリは target_date 未満限定等）。
    - テスト用に _call_openai_api の差し替えが可能。

- データプラットフォーム関連
  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py, src/kabusys/data/__init__.py:
    - ETLResult データクラスによる ETL 実行結果の集約（取得数、保存数、品質問題、エラー一覧等）。
    - ETL の設計方針（差分更新、バックフィル、品質チェックの収集方針）を反映。
    - pipeline.ETLResult を etl モジュールから再エクスポート。
  - src/kabusys/data/calendar_management.py:
    - JPX（マーケット）カレンダー管理。market_calendar テーブルの夜間バッチ更新（calendar_update_job）と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の API を提供。
    - DB 登録がない場合は曜日ベース（週末除外）でフォールバックする一貫した挙動。
    - calendar_update_job は jquants_client.fetch_market_calendar / save_market_calendar を使用して差分取得・保存（バックフィルを含む）し、健全性チェックを実装。

- リサーチ（ファクター・特徴量探索）
  - src/kabusys/research/factor_research.py:
    - モメンタム（1M/3M/6M/ma200_dev）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER/ROE）を計算する関数を提供（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の prices_daily / raw_financials を参照する設計。不足データ時は None を返す。
    - 各関数は (date, code) ベースの辞書リストを返す。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（スペアマンランク相関: calc_ic）、ランク化ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等外部ライブラリに依存せず標準ライブラリ＋duckdb で実装。
    - rank は同順位の平均ランク算出を行う（丸めにより ties の漏れを防止）。

Changed
- 設計思想として以下を明示:
  - 全 AI / データ処理は lookahead バイアス防止のため日時参照を外部化（target_date に依存）。
  - DB 書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT 相当）して部分失敗時のデータ保護を実現。
  - OpenAI 呼び出しの失敗は致命エラーにしないフェイルセーフ（通常はスコアを 0.0 にフォールバック、ログ出力）。
  - テスト容易性のため、API 呼び出し箇所を差し替え可能に実装。

Fixed
- N/A（初期リリース）

Removed
- N/A（初期リリース）

Notes / 既知の制約・今後の予定
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN: J-Quants API 利用に必要
  - KABU_API_PASSWORD: kabuステーション API パスワード
  - OPENAI_API_KEY: AI 機能（score_news, score_regime）の実行に必須（引数での注入も可）
- デフォルト DB: DuckDB を前提（パスは DUCKDB_PATH 環境変数で指定可能）。DuckDB 0.10 系の挙動（executemany の空リスト不可等）に配慮した実装。
- Python バージョン: 型ヒント（| 演算子、typing の一部表記）等より Python 3.10 以上を想定。
- 未実装 / 将来的な拡張:
  - research.calc_value の PBR・配当利回りは現バージョンでは未実装（注記あり）。
  - strategy / execution / monitoring モジュールは __all__ に含まれているが、今回のコード一覧には個別実装ファイルが含まれていません（今後追加予定）。
- セキュリティ / 運用:
  - .env 自動ロードはデフォルトで有効。CI / テスト環境等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
  - .env の読み込みは保護された OS 環境変数を上書きしない設計（ただし .env.local は上書き用として優先）。
- テスト支援:
  - OpenAI 呼び出しは内部関数をモック可能（unittest.mock.patch を利用）。

導入メモ（簡単な使用例）
- settings の利用:
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path などを参照
- AI スコアリング:
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.ai.regime_detector import score_regime
  - 両関数とも (conn: duckdb.Connection, target_date: date, api_key: str|None) を受け取る
- リサーチ API:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

関連ファイル
- DuckDB を用いた SQL クエリ・ウィンドウ関数を多用しています。既存 DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials など）との互換を確認してください。

もし CHANGELOG に追記や修正（例: リリース日、追加の貢献者、抜けている機能の記載など）が必要であれば教えてください。