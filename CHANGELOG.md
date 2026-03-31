# CHANGELOG

すべての変更は "Keep a Changelog" の方式に準拠して記載しています。  
バージョンはパッケージ内の __version__ (= 0.1.0) に基づきます。

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買 / データプラットフォーム向けのコア機能群を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージのエントリポイント
  - kabusys.__init__ に公開モジュール一覧を定義（data, strategy, execution, monitoring）。
- 環境設定管理
  - kabusys.config:
    - .env / .env.local の自動ロード機能（プロジェクトルートは .git または pyproject.toml を探索して決定）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パーサー: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等をサポート。
    - OS 環境変数を保護する protected 機構（.env.local による上書き挙動の制御）。
    - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / 実行環境 (KABUSYS_ENV) / LOG_LEVEL などをプロパティ経由で取得・検証。
- AI 関連
  - kabusys.ai パッケージを追加、news_nlp.score_news を公開。
  - ニュース NLP (kabusys.ai.news_nlp):
    - raw_news と news_symbols を用いた銘柄ごとのニュース集約。
    - OpenAI (gpt-4o-mini) の JSON mode を用いたバッチセンチメント評価（最大バッチサイズ 20 銘柄）。
    - 1 銘柄あたりの記事数・文字数制限（記事数=10、文字=3000）によるトークン肥大化対策。
    - 再試行（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装。
    - レスポンスの堅牢なバリデーションとスコア ±1.0 へのクリップ。
    - 成果は ai_scores テーブルへ冪等的に書き込み（対象コードのみ DELETE → INSERT）。
    - テスト用に _call_openai_api を patch 可能に設計。
    - calc_news_window: JST ベースのニュースウィンドウ算出（前日15:00〜当日08:30 JST を UTC に変換して比較）。
  - 市場レジーム判定 (kabusys.ai.regime_detector):
    - ETF 1321（Nikkei225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム ('bull' / 'neutral' / 'bear') を算出。
    - マクロニュース抽出用キーワード群を実装し、最大 20 件までタイトルを LLM に送る。
    - OpenAI API 呼び出しに対するリトライ、エラー時は macro_sentiment=0.0 にフォールバック。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
- リサーチ / ファクター群
  - kabusys.research パッケージ、以下を実装・公開:
    - ファクター計算 (factor_research):
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
      - calc_value: PER（EPS が 0/欠損時は None）、ROE（raw_financials から最新レコードを取得）。
      - 共通点: DuckDB の prices_daily / raw_financials を用いた完全オフライン計算（発注等の外部アクセスなし）。
    - 特徴量探索 (feature_exploration):
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）への将来リターン計算を一括クエリで取得。
      - calc_ic: スピアマン（ランク）相関（IC）計算の実装。3 銘柄未満で計算不能なら None を返す。
      - rank: 同順位は平均ランクで扱うランク変換ユーティリティ（round(..., 12) により ties の安定化）。
      - factor_summary: count/mean/std/min/max/median を返す簡易統計サマリ。
- データプラットフォーム
  - kabusys.data パッケージ:
    - calendar_management:
      - JPX カレンダーの夜間差分更新ジョブ (calendar_update_job) と営業日判定ユーティリティ (is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day) を実装。
      - DB の market_calendar を優先し、未登録日は曜日ベース（週末）でフォールバックする一貫したロジック。
      - lookahead, backfill, sanity チェックを導入。
    - pipeline / etl:
      - ETLResult データクラスを公開（取得件数・保存件数・品質チェック結果・エラー一覧などを保持）。
      - pipeline モジュール（差分取得・save_* による冪等保存・品質チェックの基本設計）に対応するインフラ。
    - etl モジュールは pipeline.ETLResult を再エクスポート。
- ログ・監視設定
  - Settings 経由で PID ファイルパス、CPU/メモリ/ディスク閾値等を取得可能。

### 変更 (Changed)
- （初版のため過去バージョンからの変更はありません）

### 修正 (Fixed)
- （初版のため修正履歴はありません）

### セキュリティ (Security)
- OpenAI API キーは明示的に引数で注入可能（テスト容易化）かつ環境変数 OPENAI_API_KEY を参照する。キー未設定時は明確な ValueError を発生させることで誤動作を防止。

### その他・設計上の留意点
- ルックアヘッドバイアス防止のため、いずれのモジュールも datetime.today() / date.today() をスコープ内で無条件に参照せず、明示的な target_date を引数として受け取る設計になっています。
- OpenAI 呼び出しは各モジュールで独立実装され、テスト時に差し替え可能（patch 可能）な設計です。
- DuckDB に対する埋め込み SQL は互換性を考慮（executemany の空リスト回避等）して記述されています。
- DB 書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT を期待）にし、トランザクション管理（BEGIN/COMMIT/ROLLBACK）を実装しています。

今後のリリースでは、strategy / execution / monitoring 周りの実運用向け機能（発注ロジック・接続管理・監視エージェント等）、ユニットテスト・統合テスト増強、ドキュメント整備を予定しています。