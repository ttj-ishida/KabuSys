Changelog
=========

すべての変更は Keep a Changelog の形式に従います。  
安定版リリースのバージョン番号はセマンティックバージョニングに従います。

v0.1.0 - 2026-03-28
-------------------

Added
- パッケージ初回リリース。モジュール群と主要機能を実装。
- パッケージメタ情報
  - kabusys.__version__ = "0.1.0"
  - __all__ に主要サブパッケージ（data, research, ai 等）を公開。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を読み込み（CWD 非依存）。
  - .env パースロジックを強化：
    - export KEY=val 形式対応
    - シングル/ダブルクォート中のバックスラッシュエスケープ対応
    - インラインコメントの取り扱いを細かく制御
  - 自動読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DBパス / 実行環境等のプロパティを取得可能：
    - 必須変数チェック（_require により未設定時は ValueError）
    - env 値検証（development / paper_trading / live）
    - log_level 検証（DEBUG, INFO, ...）
    - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）を用意

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から対象記事を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む。
    - バッチ処理（最大 20 銘柄／コール）、記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - JSON Mode を前提とした API 呼び出し、レスポンスの堅牢なバリデーション（余計な前後テキストの復元含む）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - API 呼び出しの差し替え（単体テスト向けに _call_openai_api を patch 可能）。
    - 失敗時はフェイルセーフでスキップ（例外を投げず処理継続）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で market_regime に保存。
    - OpenAI 呼び出しは news_nlp と独立した実装（モジュール結合を避ける設計）。
    - API キー注入（引数 or 環境変数 OPENAI_API_KEY）、リトライ・フォールバック（失敗時 macro_sentiment=0.0）。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバックハンドリング。

- データ / ETL（kabusys.data）
  - calendar_management
    - JPX カレンダー管理ロジック（market_calendar を用いた営業日判定、next/prev/get_trading_days/is_sq_day 等）。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を休場）。
    - calendar_update_job：J-Quants から差分取得して market_calendar を冪等更新。バックフィルと健全性チェックを実装。
  - pipeline / ETLResult
    - ETLResult dataclass を公開（pipeline.ETLResult を kabusys.data.etl 経由で再エクスポート）。
    - 差分取得、バックフィル、品質チェック（quality モジュール）等の設計を反映したユーティリティ（最小データ日、lookahead、backfill の定義等）。
    - DuckDB を前提としたテーブル存在チェック・最大日付取得等のユーティリティ関数実装。

- リサーチ（kabusys.research）
  - factor_research
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、出来高・売買代金指標）、Value（PER, ROE）を計算する関数を実装。
    - DuckDB 上で SQL を用いた効率的な計算、データ不足時の None 処理、結果は (date, code) をキーとした dict のリストで返す。
    - 本番の発注 API にはアクセスしない設計。
  - feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン、入力検証あり）。
    - IC（Information Coefficient）を計算する calc_ic（スピアマンのランク相関）。
    - ランク変換ユーティリティ rank（平均ランクで ties を処理）。
    - ファクター統計要約 factor_summary（count/mean/std/min/max/median を計算）。
    - pandas 等の外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。

Changed
- 初期実装における設計上の注意点や安全策を明文化・実装：
  - ルックアヘッドバイアス防止のため、各処理は datetime.today()/date.today() を内部参照しない（target_date を明示的に受け取る）。
  - DB 書き込みは基本的にトランザクションで行い、失敗時はロールバックを試行してログ出力。
  - DuckDB の executemany に対する互換性考慮（空リストは送らない）や日付型取り扱いの互換性ラッパーを追加。

Fixed
- （初回リリース）設計上の落とし穴や予防措置をコード上で対処：
  - .env 読み込み時のファイル読み込みエラーを警告に落とし、プロセスを継続するように変更（OSError を捕捉）。
  - OpenAI API の APIError における status_code の有無を getattr で安全に扱うように修正。
  - JSON レスポンスパースで余計な前後テキストが混ざる場合に {} の抽出で復元を試みる堅牢化。

Security
- 環境変数の扱いに注意：
  - 自動読み込み時に既存の OS 環境変数を protected として上書きしないデフォルト挙動を採用。
  - 機密情報（API キー等）は Settings 経由で必須チェックを行い、未設定時は ValueError を発生させ安全性を確保。

Notes / Known limitations
- Value ファクターで PBR・配当利回りは未実装（注記あり）。
- OpenAI への呼び出しは gpt-4o-mini + JSON mode 前提。API 仕様変更やモデル変更に伴う修正が必要になる可能性あり。
- ETL / calendar の一部関数は jquants_client（外部モジュール）に依存しており、外部 API の可用性に影響される。
- DuckDB バージョン差異による挙動（リストバインド等）に対応するための互換措置を入れているが、環境依存の差分テスト推奨。

開発者向け補足
- 単体テストのために以下を差し替え可能：
  - kabusys.ai.news_nlp._call_openai_api を unittest.mock.patch で置換して API 呼び出しをモック化可能。
  - kabusys.ai.regime_detector._call_openai_api も同様。
- 自動 .env ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

今後の予定（非確定）
- 追加ファクター（PBR、配当利回り等）の実装。
- モデル切替やローカル LLM 対応の抽象化。
- pipeline の品質チェック結果に基づく自動アラート / 修正ワークフローの追加。

----- 

（この CHANGELOG はリポジトリ内のソースコードから機能・設計方針を推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース担当者の確認を推奨します。）