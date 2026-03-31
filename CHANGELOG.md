# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

現在のリリース方針: 初期リリース 0.1.0（機能群の提供）。将来的な変更はここに追記します。

## [0.1.0] - 2026-03-31

初回公開リリース。以下の主要機能・モジュールを追加しました。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの基本初期化（version = 0.1.0）。
  - __all__ に data, strategy, execution, monitoring を公開（将来的な拡張を想定）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に探索（CWD 非依存）。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント扱いの細かいルール。
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - Settings クラスを導入し、J-Quants / kabu / Slack / DB パス /監視閾値 / 環境 (development/paper_trading/live) / ログレベルの取得を提供。
  - 必須環境変数取得時のバリデーションを実装（未設定時は ValueError を送出）。
  - デフォルトの DB パス: DUCKDB_PATH=`data/kabusys.duckdb`、SQLITE_PATH=`data/monitoring.db`。
  - 監視用 PID ファイル・閾値のデフォルト値を提供。

- AI（Natural Language Processing）機能 (kabusys.ai)
  - news_nlp (score_news)
    - raw_news と news_symbols を元に、銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）へバッチ送信しセンチメント（ai_score）を ai_scores テーブルへ書き込み。
    - チャンクバッチ処理（1回あたり最大 20 銘柄）、記事数/文字数トリム、JSON Mode 出力パース。
    - 再試行ロジック（429/ネットワーク断/タイムアウト/5xx は指数バックオフでリトライ）、レスポンス検証とスコアの ±1.0 クリップ。
    - calc_news_window により JST ベースのニュース取り込みウィンドウを計算（前日15:00～当日08:30 JST を UTC に変換）。
    - API キーは引数または環境変数 OPENAI_API_KEY を使用。未設定の場合は ValueError。
    - 戻り値: 書き込んだ銘柄数（int）。
    - フェイルセーフ: API エラーやパース失敗時は個別チャンクをスキップして処理継続。

  - regime_detector (score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、market_regime テーブルへ日次で書き込み。
    - マクロニュースは news_nlp の calc_news_window を利用して抽出。OpenAI でマクロセンチメントを取得（JSON 出力を期待）。
    - LLM 呼び出しの再試行や 5xx 特殊処理を実装。API 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - ルールベースで regime_label を判定（閾値により 'bull' / 'neutral' / 'bear'）。
    - DB 書き込みは冪等（BEGIN / DELETE WHERE date=? / INSERT / COMMIT）し、失敗時は ROLLBACK を試行して例外を伝播。

- データプラットフォーム関連 (kabusys.data)
  - calendar_management
    - JPX カレンダー管理（market_calendar テーブル）を提供。営業日判定・次/前営業日取得・期間内営業日列挙・SQ判定を実装。
    - DB にデータがない場合は曜日（平日）ベースでフォールバックする堅牢設計。
    - 夜間バッチ更新 job (calendar_update_job) を実装し、J-Quants クライアント経由で差分取得・バックフィル・保存を実行。
    - 異常検知（将来日付の健全性チェック）や例外処理を実装。

  - pipeline / ETLResult / etl エクスポート
    - ETL の結果を表す dataclass ETLResult を追加（品質チェック結果・エラー一覧・各種取得/保存数を含む）。
    - ETL モジュールは差分取得、保存（Idempotent）、品質チェックの設計に対応するインターフェースを備える（詳細実装は jquants_client と quality モジュールに依存）。

- Research（研究用）機能 (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER/ROE）等の計算関数を実装。
    - DuckDB 上の prices_daily / raw_financials に対する SQL ベース実装。結果は (date, code) をキーとする dict のリストを返す。
  - feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン）、IC（Spearman の ρ）計算、rank（平均ランクを用いる）、factor_summary（count/mean/std/min/max/median）を提供。
    - pandas 等の外部ライブラリに依存せず、標準ライブラリと DuckDB で実装。
  - data.stats から zscore_normalize を再エクスポート（__init__ 経由）。

### 変更 (Changed)
- 初期リリースのため変更履歴はなし（新規追加中心）。

### 修正 (Fixed)
- 初期リリースのため修正履歴はなし。

### セキュリティ (Security)
- 環境変数の自動ロードはプロジェクトルート検出に依存し、用途によって KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
- Settings クラスで重要なトークン（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）を必須にしており、未設定時は ValueError を送出して早期に検出可能。
- OpenAI API キー（OPENAI_API_KEY）は AI 機能で必須。API キーの注入は引数経由でのテスト用差し替えも可能。

### 既知の注意点 / 設計上の決定
- ルックアヘッドバイアス回避: 全てのバッチ処理（news/regime/research 等）は内部で date / target_date を明示的に扱い、datetime.today()/date.today() を直接参照しない設計。
- フェイルセーフ動作: LLM API の失敗やパースエラーは基本的に局所的にフォールバック（例: macro_sentiment=0.0、チャンクスキップ）し、全体処理が即座に停止しない実装方針。
- DB 書き込みは可能な限り冪等に実装（DELETE→INSERT や ON CONFLICT を想定）し、部分失敗時に既存データを不必要に消さない工夫をしている。
- DuckDB のバージョン差異（executemany の空リスト扱い等）への互換性配慮を行っている。

### 互換性 / マイグレーション
- 初回リリースのためマイグレーション操作は不要。
- 将来的にスキーマ変更や設定キー追加がある場合はこの CHANGELOG に追記予定。

---

今後のリリースでは、strategy / execution / monitoring モジュールの具体的実装、テストカバレッジの拡充、ドキュメント（Usage・API 例）の追加を予定しています。