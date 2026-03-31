CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
フォーマット: (バージョン) - YYYY-MM-DD

[Unreleased]
------------

- なし

0.1.0 - 2026-03-31
------------------

Added
- 初期リリース。日本株自動売買システム "KabuSys" のコアモジュール群を追加。
  - パッケージ初期化
    - src/kabusys/__init__.py: バージョン __version__="0.1.0"、公開サブパッケージ data, strategy, execution, monitoring をエクスポート。
  - 設定・環境変数管理
    - src/kabusys/config.py:
      - .env/.env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする仕組みを実装。
      - export KEY=val 形式やクォート／エスケープ、行内コメントを考慮したパーサを実装。
      - OS 環境変数を保護する protected オプション、上書き制御（override）、自動ロードの無効化フラグ (KABUSYS_DISABLE_AUTO_ENV_LOAD) をサポート。
      - 必須環境変数チェック（_require）と Settings クラスを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN 等）。環境値の検証（KABUSYS_ENV, LOG_LEVEL）を行う。
  - AI（自然言語処理）機能
    - src/kabusys/ai/news_nlp.py:
      - ニュース記事を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントをスコアリングする score_news を実装。
      - タイムウィンドウ計算（JST基準）、記事集約、チャンク単位（最大20銘柄）での API 呼出し、結果バリデーション、スコアの ±1.0 クリッピング、DuckDB への冪等書き込み（DELETE→INSERT）を実装。
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライと、失敗時のフェイルセーフ動作（スキップ）を実装。
      - テスト容易性のため _call_openai_api をパッチ可能に設計。
    - src/kabusys/ai/regime_detector.py:
      - ETF 1321（Nikkei 連動）の200日移動平均乖離（70% 重み）とニュースベースのマクロセンチメント（30% 重み）を合成して日次市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
      - ma200_ratio 計算（ルックアヘッド回避のため target_date 未満データのみ使用）、マクロニュース抽出、OpenAI 呼出し（gpt-4o-mini）によるセンチメント評価、冪等な DB 書き込みを実装。
      - API 呼出しのリトライ、エラー時の macro_sentiment=0.0 フォールバック等を備える。
    - ai パッケージの公開 API は score_news, score_regime を想定。
  - Data（データ基盤）
    - src/kabusys/data/pipeline.py, etl.py:
      - ETLResult データクラスと ETL パイプライン用ユーティリティを実装。差分取得、バックフィル（デフォルト3日）、品質チェックとの連携、DuckDB への保存（idempotent）を想定。
      - テーブル存在確認や最大日付取得などの内部ユーティリティを提供。
    - src/kabusys/data/calendar_management.py:
      - JPX マーケットカレンダーの管理、営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）と夜間バッチ更新 job (calendar_update_job) を実装。
      - market_calendar が未取得時は曜日ベースのフォールバックを行い、DB 登録値の優先使用、最大探索日数制限、バックフィル戦略、健全性チェックを実装。
    - src/kabusys/data/__init__.py, etl の再エクスポートを追加。
  - Research（リサーチ）機能
    - src/kabusys/research/factor_research.py:
      - Momentum/Volatility/Value 等の定量ファクター計算（calc_momentum, calc_volatility, calc_value）を実装。DuckDB の prices_daily / raw_financials を参照して計算。結果は (date, code) をキーとする辞書リストで返す。
      - パフォーマンスや欠損制御（データ不足時は None）を考慮した実装。
    - src/kabusys/research/feature_exploration.py:
      - 将来リターン計算 calc_forward_returns（任意ホライズン対応）、IC (Spearman ランク相関) を計算する calc_ic、ランク化ユーティリティ rank、ファクター統計サマリー factor_summary を実装。
    - src/kabusys/research/__init__.py: 主要関数の再エクスポートを追加。
  - 汎用設計方針（クロスモジュール）
    - ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照しない（外部から target_date を受け取る設計）。
    - DuckDB を主要な分析用ストレージとして想定し、SQL と Python を組み合わせた実装。
    - 外部 API 呼出しはフェイルセーフ（エラー時フォールバックか部分処理スキップ）を採用し、致命的な例外は上位に伝播するが多くのケースで継続可能な設計。
    - テスト容易性のため内部的な API 呼出し箇所は patch 可能に設計（ユニットテストでモック化しやすい）。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Security
- 新規リリースのため該当なし。

Notes / マイグレーション
- OpenAI API を利用する機能（score_news, score_regime）を使用する場合は OPENAI_API_KEY を環境変数に設定するか、各関数の api_key 引数を渡してください。未設定時は ValueError を送出します。
- .env 自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ（prices_daily, raw_news, ai_scores, market_calendar, raw_financials など）が必要です。ETL / 保存処理前にスキーマを準備してください。

Acknowledgements / テストフック
- OpenAI 呼び出しの内部ラッパー関数（各モジュールの _call_openai_api）を unittest.mock.patch で差し替えることにより API 呼出しをモック可能です（ユニットテストを想定した設計）。

以上。