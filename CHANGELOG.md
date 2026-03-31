# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従って管理しています。

## [0.1.0] - 2026-03-31

### 追加 (Added)
- パッケージ初期リリース: kabusys — 日本株自動売買・研究用ユーティリティ群を公開。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、行末コメントの取り扱いに対応。
    - 無効行や不正行を安全にスキップ。
  - 環境変数取得ユーティリティ Settings を導入。
    - J-Quants / kabu ステーション / Slack / DB パス等のプロパティを提供。
    - env / log_level の値検証（許容値セット）および補助プロパティ（is_live / is_paper / is_dev）。

- AI（NLP）モジュール (src/kabusys/ai/)
  - ニュースセンチメントスコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別スコアを計算・ai_scores テーブルへ書き込み。
    - チャンク処理（最大 20 銘柄/コール）、1銘柄あたり最大記事数・文字数トリム、JSON Mode による厳格なレスポンス処理。
    - リトライ戦略（429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフ）、レスポンスバリデーション、スコア ±1.0 クリップ。
    - API キー注入対応（api_key 引数または OPENAI_API_KEY 環境変数）。
    - テスト容易性のため _call_openai_api の差し替えポイントを用意。
    - calc_news_window による JST ベースのニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST → UTC に変換して使用）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225 連動ETF）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を組み合わせて日次レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュースフィルタリング（キーワードリスト）、OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント評価、リトライ・フォールバック（失敗時 macro_sentiment=0.0）。
    - ルックアヘッドバイアス回避設計（内部で datetime.today()/date.today() を参照しない、DB クエリで date < target_date を使用）。
    - API 呼び出しの再試行・エラー分類（RateLimit/Connection/Timeout/5xx/非5xx の扱い）とログ出力。

- データプラットフォーム（src/kabusys/data/）
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar に基づく営業日判定ユーティリティ群を提供。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した判定ロジック。
    - calendar_update_job による J-Quants からの差分取得・冪等保存（バックフィル・健全性チェックを含む）。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを導入して ETL 実行結果（取得/保存件数・品質問題・エラー）を構造化して返却。
    - 差分更新、backfill、品質チェック統合の設計方針を実装（jquants_client / quality モジュールと連携する想定）。
    - DuckDB 互換性の考慮（テーブル存在チェック、MAX(date) 取得ロジック、executemany 空リスト回避等）。
  - jquants_client 経由の保存処理を想定した idempotent な保存フローに対応する設計。

- リサーチ（src/kabusys/research/）
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日 ATR、相対ATR、平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB 上で計算する関数を実装。
    - データ不足時の None 扱い、ターゲット日基準のクエリ実装、ログ出力。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）、情報係数（calc_ic：Spearman ランク相関）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。
  - zscore_normalize は kabusys.data.stats から再エクスポートする初期インターフェースを用意。

- その他
  - 各所で DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等パターンを採用し、例外発生時は ROLLBACK を試行してログに記録する堅牢な実装。
  - 多くの場所で詳細なログ出力（info/warning/debug）が追加され、運用観点でのトラブルシュートを容易化。
  - テストを想定した差し替えポイント（OpenAI 呼び出し）や api_key 注入インターフェースを整備。

### 変更 (Changed)
- 初版のため該当なし。

### 修正 (Fixed)
- 初版のため該当なし。

### セキュリティ (Security)
- 初版のため該当なし。

備考:
- OpenAI API を使用する機能は API キーの設定（api_key 引数または OPENAI_API_KEY 環境変数）が必須です。未設定時は ValueError を発生させて明示的に失敗します。
- DuckDB のバージョン差異や運用上の注意点（executemany の空リスト問題、list バインドの互換性等）に対応するための保護コードが含まれています。

（今後のリリースではバグ修正、性能改善、strategy / execution / monitoring の実装追加を予定しています。）