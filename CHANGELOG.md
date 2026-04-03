CHANGELOG
=========

すべての重要な変更は Keep a Changelog の慣習に従って記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-03
------------------

Added
- 基本パッケージとバージョン情報
  - pakage 名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - パブリックサブパッケージとして data, strategy, execution, monitoring を __all__ で公開。

- 環境設定管理
  - .env / .env.local を自動読み込みする環境変数管理機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを __file__ を起点に .git または pyproject.toml から探索して発見（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env の読み込み順序: OS 環境変数 > .env.local（上書き）> .env（未設定のみ）。
    - OS 環境変数は protected として上書きを防止。
  - .env パーサを細かく実装:
    - export KEY=val 形式対応。
    - シングル/ダブルクォートとバックスラッシュエスケープを正しく処理。
    - インラインコメント（#）の扱いを改善（クォート有無での扱い差分）。
  - Settings クラスを提供し、アプリケーション設定にアクセス可能:
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 環境名・ログレベル等のプロパティを定義。
    - 必須環境変数未設定時は分かりやすい ValueError を送出（例: OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値を列挙、無効値で例外）。

- AI モジュール（OpenAI 統合）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄毎にニュースを結合し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを取得。
    - チャンク単位処理（最大 20 銘柄 / バッチ）、1銘柄あたり最大記事数と文字数トリム（_MAX_ARTICLES_PER_STOCK=10、_MAX_CHARS_PER_STOCK=3000）。
    - JSON Mode を使用し、レスポンスを厳格に検証（results 配列・code/score 構造・スコア数値性）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ付きリトライ（_MAX_RETRIES, _RETRY_BASE_SECONDS）。
    - 失敗・検証エラー時は該当チャンクをスキップして他チャンクは継続（フェイルセーフ設計）。
    - DuckDB への書き込みは idempotent（DELETE → INSERT の順で、部分失敗時に既存データを保護）。
    - テスト容易化のため OpenAI 呼び出し関数をパッチ可能に実装（_call_openai_api を monkeypatch 可能）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の market_regime を算出。
    - news_nlp の calc_news_window を利用してリークを防止する時間窓設計。
    - OpenAI 呼び出しは gpt-4o-mini、JSON パース失敗／API 障害時は macro_sentiment=0.0 にフォールバック。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - 設定として最大記事数やリトライ回数、モデル名など定数化。

- Data / ETL / カレンダー
  - ETL パイプラインと結果型（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを公開（ETL のフェッチ数／保存数／品質チェック結果／エラーの集約）。
    - 差分更新、バックフィル方針、品質チェックとの連携を設計に反映。
  - JPX 市場カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルのデータ有無に応じた営業日判定ロジックを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - DB にデータがある場合は DB 値優先、未登録日は曜日ベースのフォールバック。
    - calendar_update_job により J-Quants から差分取得 → 冪等保存。バックフィル・整合性チェックを実装。
    - 最大探索日数等の安全策を導入（_MAX_SEARCH_DAYS, _SANITY_MAX_FUTURE_DAYS 等）。

- Research（因子・特徴量探索）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum (1M/3M/6M)、200日 MA 乖離、ATR(20)、流動性指標（20日平均売買代金・出来高比）等を計算する関数を提供。
    - DuckDB 内の prices_daily / raw_financials を参照して計算。結果は (date, code) をキーとした辞書リストで返却。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン取得（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）等を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - research 上位 API を __all__ にて公開（zscore_normalize は data.stats から再利用）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / Migration / Requirements
- 必要な DB テーブル（代表例）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等が事前に存在することが前提。
  - DuckDB をメインの分析 DB として利用（DuckDB 接続オブジェクトを関数に渡す設計）。
- 環境変数
  - OpenAI API を利用する機能（score_news, score_regime）は OPENAI_API_KEY が必要。関数引数 api_key により注入可能。
  - J-Quants, kabu, LINE 用の環境変数も Settings で参照される（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN 等）。
- テスト支援
  - OpenAI 呼び出し箇所は内部関数（_call_openai_api）をパッチ可能にしており、ユニットテストでのモックが容易。
- 設計方針
  - ルックアヘッドバイアスを避けるため datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）。
  - API 障害に対してフェイルセーフ（スコアを 0.0 にフォールバック、チャンク単位での続行）を採用。
  - DB 書き込みはできる限り冪等に実装（DELETE→INSERT、ON CONFLICT に委ねる実装方針）。

今後の予定（アイデア）
- more fine-grained logging / observability の拡充（メトリクス出力、Prometheus 等）。
- strategy / execution モジュールの実装・実稼働に向けたシミュレーションと安全ガードの追加。
- ai モデル差し替えやローカル LLM のサポートを容易にする抽象化。
- CI 用の DuckDB テストフィクスチャ整備。

もし CHANGELOG に追加したい詳細（たとえばリリース日・担当者・リスク情報や後方互換性に関する注記）があれば教えてください。必要に応じて追記します。