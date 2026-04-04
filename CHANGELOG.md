CHANGELOG
=========
すべての注目すべき変更を記録します。This project adheres to "Keep a Changelog" と [Semantic Versioning](https://semver.org/) に準拠します。

v0.1.0 - 2026-04-04
------------------

Added
- パッケージの初回公開（バージョン 0.1.0）。
- 基本パッケージエントリ:
  - src/kabusys/__init__.py にて version と公開サブパッケージ（data, strategy, execution, monitoring）を宣言。
- 環境設定 / .env 管理:
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動ロードする仕組みを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - export KEY=val 形式やクォート・エスケープ・行コメントのパースに対応するパーサを実装。
    - OS 環境変数は保護（.env の上書きを防止）するオプションをサポート。
    - 必須変数チェック用 _require 関数を提供（未設定時に ValueError を送出）。
    - Settings クラスを提供し、J-Quants / kabu / LINE / DB /監視/ログ設定等をプロパティで取得可能。
    - KABUSYS_ENV の検証、LOG_LEVEL の検証、便宜的な is_live/is_paper/is_dev プロパティを提供。
- AI（自然言語処理）関連:
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini・JSON Mode）でセンチメント評価して ai_scores テーブルへ保存するフローを実装。
    - ニュース収集ウィンドウ（JST基準: 前日15:00〜当日08:30）を calc_news_window にて算出。
    - バッチ処理（最大 20 銘柄）、1銘柄あたりの記事数/文字数制限、レスポンスバリデーション、スコアの ±1.0 クリップを実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装。API 失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - テスト容易性のため _call_openai_api を直接 patch して差し替え可能に設計。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込みする処理を実装。
    - prices_daily と raw_news の参照、OpenAI 呼び出し（gpt-4o-mini）とリトライ/フォールバック（API失敗時は macro_sentiment=0.0）を実装。
    - レジーム合成スコアのクリップと閾値判定、トランザクション（BEGIN/DELETE/INSERT/COMMIT）およびロールバック時のログを実装。
- Research（ファクター計算 / 特徴量探索）:
  - src/kabusys/research/*
    - factor_research.py: calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を使用）。
      - Momentum: 1M/3M/6M リターン、200日MA乖離（データ不足時は None）。
      - Volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率。
      - Value: PER（EPS が無効な場合は None）, ROE（raw_financials から最新の報告データを取得）。
    - feature_exploration.py: calc_forward_returns（任意ホライズンの将来リターン）、calc_ic（スピアマンランク相関によるIC）、rank（同順位は平均ランク）、factor_summary（統計量）を実装。
    - research パッケージの __all__ に主要関数を公開。data.stats の zscore_normalize を re-export。
    - 実装方針として DuckDB を直接操作し、外部ライブラリ（pandas 等）に依存しない設計。
- Data プラットフォーム:
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ロジックを実装。
    - market_calendar が未取得の際は曜日ベースでフォールバックする設計、DB登録値優先の一貫性、探索上限(_MAX_SEARCH_DAYS) による無限ループ防止、カレンダー更新の夜間バッチ（calendar_update_job）を実装。
    - J-Quants クライアント経由の取得・保存処理呼び出し、バックフィル・健全性チェックの導入。
  - src/kabusys/data/pipeline.py
    - ETLResult dataclass による ETL 処理結果の表現（取得数・保存数・品質問題・エラー一覧等）。
    - 差分更新、backfill、品質チェック（quality モジュール）を意識した ETL パイプライン設計の骨子を実装。
  - src/kabusys/data/etl.py で ETLResult を公開。
  - DuckDB を前提とした SQL 実装（互換性処理や executemany の空リスト回避など注意点を反映）。
- 汎用 / 実装上の配慮:
  - 全体を通して「ルックアヘッドバイアス防止」の設計方針を採用（datetime.today()/date.today() を直接参照せず、関数に target_date を注入するなど）。
  - OpenAI 呼び出しの失敗に対するフェイルセーフ（API失敗 = その部分を 0 相当で継続、例外を全面的に投げない設計箇所がある）。
  - ロギング（logger）を各モジュールで活用し、警告・情報・例外時ログを適切に出力。
  - DuckDB トランザクション制御（BEGIN/COMMIT/ROLLBACK）による冪等書き込みを意識した実装。
  - テストのしやすさを考慮し、OpenAI 呼び出し箇所を差し替え可能に設計（unit test 用の patch ポイントを提供）。

Changed
-（初期リリースのため該当なし）

Fixed
-（初期リリースのため該当なし）

Removed
-（初期リリースのため該当なし）

Security
- OpenAI API キーの扱い:
  - score_news と score_regime は api_key 引数を受け取り（None の場合は環境変数 OPENAI_API_KEY を参照）し、未設定時は ValueError を送出することで誤操作を防止。

Notes / Migration / Usage
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings 経由で必須チェックが行われる（未設定時は ValueError）。
- .env の自動読み込みはプロジェクトルート検出を行うため、パッケージ配布後もカレントディレクトリに依存しない挙動を目指しています。必要時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑制してください。
- OpenAI の呼び出しは gpt-4o-mini と JSON Mode を前提としたプロンプト設計になっています。API レスポンスのフォーマット変化に対してはレスポンスパースでの保護（JSON 抽出、例外処理）を備えています。

今後の予定（非網羅）
- 発注・実行（execution）や監視（monitoring）、strategy 層の実装・テスト拡充。
- ドキュメント（Usage / API / Data Schema）とサンプル ETL ジョブ、CI テストの追加。
- 性能・スケーラビリティ改善、DuckDB マルチスレッド使用時の注意点検証。

--- 
この CHANGELOG はソースコードの実装内容から生成しています。実際のリリースノートに反映する際は、リリース日や追加の変更点（バグ修正、API 互換性情報等）を適宜補完してください。