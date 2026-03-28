# Changelog

すべての重要な変更点を Keep a Changelog の形式に従って日本語で記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- （現時点のコードベースは初回リリース相当の内容のため、未リリース変更はありません）

## [0.1.0] - 2026-03-28
初回公開リリース。日本株自動売買／リサーチ用のコアライブラリを提供します。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージ（__version__ = 0.1.0）と主要サブパッケージのエクスポートを追加（data, research, ai, 等を想定）。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）により、カレントワーキングディレクトリに依存しない読み込みを実現。
  - .env と .env.local の優先順位を実装（OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロード無効化可能。
  - .env のパースは export 文、クォート、エスケープ、インラインコメントなどを考慮した堅牢な実装。
  - Settings クラスを提供し、主要な必須環境変数とデフォルト値を集約:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - 環境 (KABUSYS_ENV) とログレベル (LOG_LEVEL) の検証（許容値チェック）。
- AI モジュール (src/kabusys/ai/)
  - ニュース NLP (news_nlp.py)
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（最大記事数・文字数トリム）を実装。
    - JSON Mode を利用した厳格なレスポンスバリデーションとスコアクリッピング（±1.0）。
    - リトライ（429・接続断・タイムアウト・5xx）を指数バックオフで実装。部分失敗時に既存データを保護する idempotent な DB 更新ロジック。
    - テスト容易性のため _call_openai_api を patch で差し替え可能。
    - calc_news_window ユーティリティを公開（JST ウィンドウ → UTC naive datetime を返す）。
  - 市場レジーム検出 (regime_detector.py)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - OpenAI（gpt-4o-mini）呼び出し、JSON レスポンスパース、リトライ/フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - DB（DuckDB）の prices_daily, raw_news, market_regime を用いた計算と冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - テストのために _call_openai_api を差し替え可能にしてモジュール間の結合を低く保つ設計。
- データ処理モジュール (src/kabusys/data/)
  - カレンダー管理 (calendar_management.py)
    - market_calendar を元にした営業日判定ロジックを追加（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベース（土日除外）のフォールバックを行う。最大探索日数制限で無限ループ回避。
    - calendar_update_job を実装し、J-Quants API クライアント経由で JPX カレンダーを差分取得して保存（バックフィル・健全性チェックを含む）。
  - ETL パイプライン (pipeline.py, etl.py)
    - 差分取得→保存→品質チェックのための ETLResult データクラスを実装（取得数・保存数・quality issues・エラー一覧などを含む）。
    - jquants_client および quality モジュールとの統合を想定した差分ロード設計（backfill の扱い、id_token 注入可能）。
    - _get_max_date などのヘルパー実装。
  - data.etl は ETLResult を再エクスポート。
- Research（src/kabusys/research/）
  - factor_research.py
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比）、バリュー（PER、ROE）を DuckDB 上の SQL/ウィンドウ関数で計算する関数を追加。
    - 各関数は prices_daily / raw_financials のみを参照し、結果は (date, code) をキーとする dict リストで返却。
  - feature_exploration.py
    - 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ランク変換ユーティリティ、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - pandas に依存せず標準ライブラリのみで実装。
  - research パッケージは主要関数を上位にエクスポート（zscore_normalize は data.stats から）。
- 汎用設計方針・品質
  - すべての「日付基準」処理で datetime.today()/date.today() を直接参照しない設計を採用（ルックアヘッドバイアス防止）。
  - DuckDB を主要なオンディスク分析 DB として利用。
  - OpenAI 呼び出しは JSON Mode を使い、厳格なレスポンス検証を行う。
  - API 失敗時は例外を投げずにフォールバック（フェイルセーフ）する箇所を明示し、部分失敗時にも他データを保護するよう DB 操作は冪等性を重視。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 廃止 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

注記:
- AI 機能を利用する関数（score_news, score_regime）は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須です。未設定の場合は ValueError を送出します。
- .env パースや DB 書き込みの細かな挙動（例: DuckDB の executemany の空リスト制約）に対する考慮が含まれています。テスト時は該当ユーティリティ関数をモックすることで安定してテスト可能です。