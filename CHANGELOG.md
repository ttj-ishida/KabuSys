"""
CHANGELOG
=========

すべての notable な変更点はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。

※ この CHANGELOG は、提供されたコードベースの内容から推測して作成した初期リリース履歴です。
"""

Unreleased
----------
- なし

[0.1.0] - 2026-03-29
--------------------
Added
- パッケージ初期リリース (kabusys v0.1.0)
  - src/kabusys/__init__.py によりパッケージ公開 (data, strategy, execution, monitoring を __all__ で公開)
- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装
      - 読み込み順: OS 環境変数 > .env.local > .env
      - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
      - プロジェクトルート特定は __file__ を起点に .git または pyproject.toml を探索して決定（CWD 非依存）
    - .env パーサを実装（export プレフィクス対応、シングル/ダブルクォートのエスケープ処理、コメント処理）
    - 環境変数必須チェック用のヘルパー _require と Settings クラスを提供
    - 主要設定プロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（development / paper_trading / live のバリデーション）
      - LOG_LEVEL（DEBUG/INFO/... のバリデーション）
- AI モジュール（OpenAI を利用したニュース/NLP関連）
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄ごとに集約して LLM に渡しセンチメントを算出、ai_scores テーブルへ書き込み
    - 時間ウィンドウ: target_date の前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）
    - チャンク処理（デフォルト 20 銘柄/コール）、1銘柄あたり最大記事数・最大文字数でトリム
    - OpenAI JSON Mode を利用し、レスポンス検証・スコアの ±1.0 クリップを実装
    - レート制限(429)、ネットワーク断、タイムアウト、5xx に対して指数バックオフでリトライ
    - 部分成功時に既存スコアを消さない idempotent な DB 書き込み（DELETE→INSERT、空パラメータ回避）
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日 MA 乖離 (重み 70%) とマクロニュース LLM センチメント (重み 30%) を合成して市場レジーム（bull/neutral/bear）を判定
    - calc_news_window を利用してマクロ記事の検索ウィンドウを算出、OpenAI（gpt-4o-mini）で macro_sentiment を評価
    - LLM 呼び出しに対するリトライ/フォールバック: API 失敗時は macro_sentiment = 0.0 として継続
    - レジーム結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）
  - 共通設計方針:
    - datetime.today() / date.today() に依存せず、ルックアヘッドバイアスを避ける設計
    - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock.patch を想定）
    - 使用モデル: gpt-4o-mini（レスポンスは厳密な JSON を期待）
- Research（因子・特徴量解析）
  - src/kabusys/research/factor_research.py
    - モメンタム (1M/3M/6M)、200 日 MA 乖離、20 日 ATR、20 日平均売買代金・出来高比率、PER/ROE（raw_financials 組合せ）を計算する関数群を提供
    - 各関数は DuckDB を受け取り、prices_daily / raw_financials を参照して (date, code) をキーとする辞書リストを返す
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（任意ホライズン）、IC（Spearman の ρ）計算、ランク変換、ファクター統計サマリーを提供
    - pandas 等外部ライブラリに依存しない純 Python + DuckDB 実装
  - src/kabusys/research/__init__.py で主要 API を再エクスポート（zscore_normalize は data.stats から）
- Data プラットフォーム
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar テーブル操作）、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、夜間 calendar_update_job を実装
    - market_calendar が未取得の場合は曜日ベース（土日非営業）でフォールバックする挙動を採用
    - calendar_update_job は J-Quants クライアントを用いて差分取得・バックフィル・健全性チェックを行い、冪等的に保存
  - src/kabusys/data/pipeline.py
    - ETL パイプラインの骨組みとユーティリティ関数（差分取得、保存、品質チェックの考え方）
    - ETLResult dataclass を実装（取得件数・保存件数・品質問題・エラー集約、has_errors, has_quality_errors, to_dict を提供）
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート
  - DuckDB との互換性／注意点:
    - executemany に空リストを渡せないバージョン (例: DuckDB 0.10) を考慮したガード実装
- 公開 API / エクスポートの整理
  - ai/__init__.py, research/__init__.py, data/etl.py 等で主要関数や型を再エクスポートして利用しやすく整理

Fixed
- .env パースロジックでの以下の改善（config.py）
  - export プレフィクス、シングル/ダブルクォート内のバックスラッシュエスケープに対応
  - クォートなし値のインラインコメント扱いの条件を厳格化（直前がスペースまたはタブのみコメントと認識）
- DuckDB 書き込みでの部分失敗による既存データ消失を避けるため、書き込み対象コードを絞って DELETE → INSERT を行う実装に修正
- news_nlp のレスポンスパースで JSON mode の「前後余計なテキスト」対策として最外の {} を抽出するリカバリ実装を追加
- rank() 実装で丸めを行い tie の検出漏れを防止する（round(v, 12) を採用）

Security
- OpenAI API キーの取り扱いについて注意喚起
  - AI 関数群 (score_news, score_regime) は api_key 引数または環境変数 OPENAI_API_KEY を参照する。
  - api_key が提供されない場合は ValueError を送出して明示的にエラー扱いにする（誤った公開・未設定を防止）。
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テストや CI 用に安全策を用意）

Notes / Migration
- 環境変数名（代表）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
  - KABUSYS_ENV (development|paper_trading|live), LOG_LEVEL
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
- AI モデルは gpt-4o-mini を前提に設計。JSON Mode を利用するため、API レスポンス形式に依存する点に注意
- 日付/時間の扱い:
  - AI モジュールはルックアヘッドバイアスを避けるため、target_date ベースで window を計算し、内部で現在時刻を参照しない設計
- DB スキーマ依存:
  - 本実装は prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等のテーブル存在を前提としている
- 既知の制約:
  - 一部の DB バインディングや DuckDB のバージョン依存挙動（executemany の空リスト等）に対応するためのワークアラウンドを実装しているが、環境により追加検証が必要

Acknowledgements
- 本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のリリースノートや変更履歴と差分がある場合は、プロジェクトの公式履歴に基づいて調整してください。