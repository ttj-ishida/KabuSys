Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-03-31
-------------------

Added
- 初期リリースを追加。
  - パッケージエントリポイント: kabusys（__version__ = 0.1.0）。公開サブモジュール: data, research, ai, execution, strategy, monitoring（__all__ に基づく）。
- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装。読み込み優先順位: OS環境 > .env.local > .env。
  - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索するため、CWD に依存しない実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
  - .env ファイルパーサの実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - 必須環境変数取得ヘルパー（_require）と Settings クラスを提供。J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等を取得可能。
- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄毎のセンチメント（ai_scores テーブル）を計算・保存する機能を実装。
    - タイムウィンドウ計算（JST ベース -> UTC 変換）、1 銘柄あたりの記事上限・文字数上限、チャンクバッチ処理（最大 20 銘柄/リクエスト）をサポート。
    - API エラー（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフリトライ、レスポンスの厳密なバリデーション（JSON 抽出、results 配列検証、コード照合、数値チェック）を実装。
    - DuckDB に対する互換性考慮（executemany に空リストを渡さない等）のための保護処理。
    - テスト用に _call_openai_api を patch して差し替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（225 連動）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みするロジックを実装。
    - prices_daily からの MA 計算は target_date 未満のデータのみ使用し、ルックアヘッドバイアスを防止。
    - マクロ記事が存在する場合は OpenAI を呼び出して macro_sentiment を算出、API 失敗時はフェイルセーフで 0.0 を使用。
    - OpenAI 呼び出しのリトライ・エラーハンドリング（RateLimit, Connection, Timeout, APIError）を実装。
    - テストで置き換え可能な _call_openai_api を内部に持つ（news_nlp と独立した実装を採用）。
- 研究（Research）モジュール (kabusys.research)
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER, ROE）等の定量ファクター計算関数を実装。
    - DuckDB SQL ウィンドウ関数を活用し、prices_daily / raw_financials を使用して結果を (date, code) 単位の dict リストで返す設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（複数ホライズン対応、データ不足時は None）、IC（Spearman の ρ）計算、ランク付けユーティリティ、ファクター統計サマリー等を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。rank 関数は同順位を平均ランクで扱う。
- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを参照して営業日判定（is_trading_day）、前後営業日の検索（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）、SQ 日判定（is_sq_day）を提供。
    - DB 登録がない場合は曜日ベースでフォールバック（週末は非営業日）。最大探索範囲を設定して無限ループ防止。
    - calendar_update_job: J-Quants API からの差分取得・バックフィル・保存処理（フェイルセーフなログとエラーハンドリング）を実装。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - 差分取得、保存（jquants_client の save_* を利用した idempotent 保存）、品質チェック（quality モジュール）を行う ETLResult データ構造とユーティリティを実装。
    - ETLResult には品質問題のリストとエラーリストを含み、辞書化メソッドを提供。
    - テーブル存在チェック、最大日付取得などのヘルパーを実装。
  - jquants_client と連携する想定での設計（fetch / save 呼び出し）。
- 共通設計上の注意点（ドキュメント化・実装）
  - ルックアヘッドバイアス対策: datetime.today()/date.today() を内部処理で参照しない関数設計（外部から target_date を注入して実行）。
  - DuckDB 互換性や部分失敗時のデータ保護（部分的に DELETE → INSERT を行うことで別の銘柄の既存スコアを保護）。
  - OpenAI API 呼び出し時の堅牢なエラーハンドリングとフェイルセーフ（スコア 0.0 へのフォールバック、ログ出力）。
  - テスト容易性を考慮した差し替えポイント（_call_openai_api の patch 等）を提供。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （該当なし）

Notes / Required environment variables
- OpenAI: OPENAI_API_KEY（関数引数で注入可能）
- J-Quants: JQUANTS_REFRESH_TOKEN
- kabu API: KABU_API_PASSWORD, (KABU_API_BASE_URL はデフォルトあり)
- Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DB パス: DUCKDB_PATH (デフォルト data/kabusys.duckdb), SQLITE_PATH (デフォルト data/monitoring.db)

開発者向け補足
- テスト時に .env の自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しをユニットテストでモックする際は kabusys.ai.news_nlp._call_openai_api または kabusys.ai.regime_detector._call_openai_api を patch してください。