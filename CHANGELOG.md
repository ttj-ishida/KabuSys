Keep a Changelog
=================

すべての重要な変更点をこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初回公開。
- 基本情報
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
- 設定管理
  - 環境変数管理モジュールを追加（src/kabusys/config.py）。
    - .env と .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パースの強化: コメント、export プレフィクス、シングル/ダブルクォート内のバックスラッシュエスケープに対応。
    - override / protected オプションにより OS 環境変数を保護して .env.local で上書き可能。
    - Settings クラスにより主要設定をプロパティで取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）、値検証（KABUSYS_ENV, LOG_LEVEL）を実装。
- AI（自然言語処理）機能
  - ニュースNLP スコアリング（src/kabusys/ai/news_nlp.py）。
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window() で提供。
    - バッチ処理（最大20銘柄/チャンク）、トークン肥大対策（最大記事数・最大文字数制限）、JSON レスポンス検証、スコアクリップ、リトライ（429/ネットワーク/タイムアウト/5xx）を実装。
    - スコアを ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT、部分失敗時に既存データを保護）。
    - テスト容易性のため _call_openai_api の差し替えを想定。
    - 公開関数: score_news(conn, target_date, api_key=None)。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）。
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し、日次で市場レジーム（bull / neutral / bear）を判定。
    - マクロニュース抽出（キーワードによるフィルタ）、LLM 呼び出し（gpt-4o-mini, JSON Mode）、リトライ・フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - 判定結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 公開関数: score_regime(conn, target_date, api_key=None)。
- データプラットフォーム / ETL
  - ETL パイプラインのインターフェース（src/kabusys/data/pipeline.py）。
    - ETL 実行結果を保持する dataclass ETLResult を追加（品質チェック結果・エラー集約・シリアライズ機能付き）。
  - etl モジュール再エクスポート（src/kabusys/data/etl.py）。
  - 市場カレンダー管理（src/kabusys/data/calendar_management.py）。
    - market_calendar テーブル管理、JPX カレンダーの夜間差分取得ジョブ（calendar_update_job）、各種営業日判定ユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 未取得時の曜日ベースのフォールバック、バックフィル・健全性チェックを実装。
- リサーチ / ファクター
  - research パッケージ（src/kabusys/research/）。
    - ファクター計算（src/kabusys/research/factor_research.py）:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）等を計算。
      - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
      - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算。
    - 特徴量探索（src/kabusys/research/feature_exploration.py）:
      - calc_forward_returns: 将来リターン（任意ホライズン）を一括取得。
      - calc_ic: スピアマンのランク相関（IC）計算。
      - factor_summary: 基本統計量（count/mean/std/min/max/median）算出。
      - rank: 同順位の平均ランクを考慮したランク付け関数。
- データユーティリティ
  - DuckDB を想定した SQL + Python 実装により、prices_daily, raw_news, raw_financials, market_regime, ai_scores 等の読み書きロジックを提供。
- ロギング・フォールバック設計
  - API 呼び出し失敗時のフォールバック（例: macro_sentiment=0.0、スコア計算スキップ）を多用し、例外で全体を停止させない堅牢設計。
  - 重要操作（DB 書き込み）時はトランザクション（BEGIN/COMMIT/ROLLBACK）を使用、ROLLBACK 失敗時には警告ログを出力。

Changed
- （初回リリースのため履歴的変更なし）
- 設計方針の明示:
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を内部処理で直接参照しない実装方針を採用（target_date を明示的引数として受け取る）。
  - DuckDB のバージョン差分（executemany の空リスト禁止など）に配慮した互換性実装。

Fixed
- .env パーサの堅牢化により以下のケースを正しく処理:
  - export KEY=val 形式のサポート。
  - クォート内のバックスラッシュエスケープ処理。
  - インラインコメントの扱い（クォート有無による差分処理）。
  - 読み込み失敗時の警告発行。

Security
- OpenAI API キーの取り扱い:
  - score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY が必須（未設定時は ValueError を送出）。
- 環境変数読み込み時に OS 環境（既存 os.environ）を保護する仕組み（protected set）を導入。

Notes / Implementation details
- OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）を前提とするが、パース時に余分な前後テキストを含むケースに対する復元ロジックを備える。
- LLM レスポンスのバリデーションを厳密に行い、不正な出力は無視してフォールバックする。
- 各種定数（リトライ回数、バックオフ、ウィンドウサイズ、上限数など）はモジュール内トップに定義され、テストや運用での調整が容易。
- テスト容易性のため、内部の API 呼び出しラッパー関数（_kabusys.ai.*._call_openai_api）を unittest.mock.patch で差し替え可能にしている。

Unreleased
- 今後の予定（例）
  - PBR / 配当利回り等のバリューファクター追加。
  - ETL の個別ステップ実行 API と監査ログ強化。
  - OpenAI への送信プロンプトやモデル切替の設定化。

以上