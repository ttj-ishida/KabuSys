CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に準拠して記載しています。  

0.1.0 - 2026-03-29
------------------

Added
- 初回リリース。日本株自動売買 / リサーチ用ユーティリティ群を追加。
  - パッケージ公開:
    - src/kabusys/__init__.py にてバージョンを "0.1.0" として公開。主要サブパッケージを __all__ でエクスポート（data, strategy, execution, monitoring）。
  - 環境設定:
    - src/kabusys/config.py
      - .env ファイルおよび OS 環境変数から設定を読み込む自動ローダーを実装（プロジェクトルート判定は .git / pyproject.toml を探索）。
      - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープに対応）。
      - .env/.env.local の読み込み順序と override の制御、OS 環境変数を保護する protected セットを導入。
      - Settings クラスを提供し、J-Quants、kabuステーション、Slack、データベースパス、ログレベル、環境種別（development/paper_trading/live）などのプロパティを公開。値検証（有効な env 値・ログレベル）と必須キー未設定時のエラーを備える。
      - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD のサポート。
  - AI（ニュース/NLP・レジーム判定）:
    - src/kabusys/ai/news_nlp.py
      - ニュース記事に対する銘柄単位センチメント解析機能を実装（score_news）。
      - JSTの時間ウィンドウ定義（前日15:00〜当日08:30）を calc_news_window で提供し、それを基に raw_news / news_symbols から銘柄ごとに記事を集約。
      - API 呼び出しは OpenAI の chat completions（gpt-4o-mini, JSON mode）を使用。銘柄をチャンク（デフォルト最大20銘柄）で送信。
      - トークン肥大化対策（1銘柄あたりの最大記事数・文字数トリム）。
      - レスポンスのバリデーション（JSON復元・results 構造・コード検査・数値検証）とスコアの ±1.0 クリップ。
      - 429・ネットワーク断・タイムアウト・5xx に対するリトライ（指数バックオフ）。失敗はフェイルセーフでスキップし、処理継続。
      - DuckDB へは冪等的に書き込み（DELETE → INSERT、executemany の空リスト回避処理）。
      - テスト容易性のため _call_openai_api を差し替え可能に設計。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321（Nikkei225連動）200日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
      - prices_daily から ma200 乖離を計算するロジック（ルックアヘッドを防ぐため target_date 未満のデータのみ使用）。
      - raw_news からマクロキーワードで記事タイトルを抽出し、LLM（gpt-4o-mini）で macro_sentiment を取得。API失敗時は 0.0 にフォールバック。
      - レジームスコア合成・ラベル化と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
      - API 呼び出しのリトライ・エラーハンドリング実装。テスト用に _call_openai_api の差し替えを想定。
  - Data / ETL / カレンダー:
    - src/kabusys/data/calendar_management.py
      - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを追加。
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の API を提供。
      - market_calendar の未取得時は曜日ベース（土日除外）でフォールバックする一貫した挙動。
      - 夜間バッチ更新 calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。
    - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
      - ETLパイプライン用の ETLResult 型を導入（pipeline モジュールの再エクスポートも行う）。
      - 差分更新・バックフィル・品質チェック（quality モジュールとの連携）を考慮した設計方針を実装。
      - DuckDB の max date 取得ユーティリティ等を実装。
  - Research（ファクター計算・特徴量探索）:
    - src/kabusys/research/factor_research.py
      - Momentum, Volatility, Value 系のファクター計算関数を実装:
        - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算（データ不足時は None）。
        - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率等を計算。
        - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（EPS 0/欠損は None）。
      - DuckDB 上の SQL ウィンドウ関数を活用した実装。
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）で将来リターンを計算。
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード <3 の場合は None）。
      - rank: 同順位は平均ランクとするランク化ユーティリティ（浮動小数の丸め対策あり）。
      - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - その他ユーティリティ:
    - src/kabusys/data/__init__.py、src/kabusys/ai/__init__.py、src/kabusys/research/__init__.py で主要関数のエクスポート整理。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数の自動ロードでは OS 環境変数を保護する仕組み（protected set）を導入。
- OpenAI API キー等の必須値は Settings で明示的に要求し、未設定時は ValueError を発生させることでキー漏洩や誤設定の早期検出を促進。

Notes / 注意事項
- DuckDB スキーマ:
  - 多くの関数は prices_daily / raw_news / news_symbols / ai_scores / raw_financials / market_calendar / market_regime 等のテーブルを前提としています。実行前に対応するスキーマ・インデックスが存在することを確認してください。
- AI 機能:
  - news_nlp.score_news / regime_detector.score_regime は OpenAI API（gpt-4o-mini）を呼び出します。api_key 引数でキーを注入するか、環境変数 OPENAI_API_KEY を設定してください。
  - API 呼び出しは JSON Mode を仮定したレスポンス検証を行いますが、外部 API の仕様変更によりパース/バリデーションが失敗する可能性があります。ログに注意してください。
- ルックアヘッド防止:
  - すべての AI / リサーチ処理は datetime.today()/date.today() を直接参照しない設計です。必ず target_date を呼び出し側で指定してください。
- テスト支援:
  - OpenAI 呼び出し箇所は内部の _call_openai_api を patch して差し替え可能に実装しており、ユニットテスト容易性に配慮しています。
- 自動 .env ロード:
  - 自動ロードが不要な場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

今後の予定（非網羅）
- Strategy / execution / monitoring サブパッケージの実装拡充（現状はエクスポートプレースホルダを提供）。
- ai モデル周りの追加検証（プロンプト改善、応答フォーマット堅牢化）。
- 品質チェック（quality モジュール）と ETL の観測性向上。

------------------------------------------------------------
この CHANGELOG はコードベース（src/ 配下のファイル）から推測して作成しています。実際のリリースノートには運用上の注意やデプロイ手順、互換性ポリシーなどを追記することを推奨します。