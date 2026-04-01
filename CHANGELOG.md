CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。  
https://semver.org/ を参照してください。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-01
--------------------

初期リリース。日本株自動売買/データ基盤のコア機能を実装しました。主な追加点・設計方針・注意事項は以下のとおりです。

Added（追加）
- パッケージ基本情報
  - kabusys パッケージ初期化（バージョン 0.1.0、公開 API の __all__ 設定）。
- 設定管理（kabusys.config）
  - .env ファイル／環境変数読み込みユーティリティ実装。
  - 自動ロード順序: OS 環境変数 > .env.local > .env（プロジェクトルートを .git / pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用途）。
  - 柔軟な .env パーサ（export 形式、シングル/ダブルクォート内のエスケープ、インラインコメント処理など）。
  - Settings クラスを公開（J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境フラグ等のプロパティを提供）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）および必須変数未設定時の明示的エラー。
- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（news_nlp.score_news）
    - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini, JSON mode) により銘柄ごとのセンチメントを算出。
    - チャンクバッチ処理（最大 20 銘柄 / API コール）、1 銘柄あたりの制限（最大記事数・最大文字数トリム）。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）と指数バックオフ。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、既知コードのみ受け入れ、数値判定、±1 でクリップ）。
    - 書き込みは冪等（対象コードのみ DELETE → INSERT）で部分失敗時に既存スコアを保護。
    - ロックアヘッドバイアスを避けるため datetime.today()/date.today() を参照しない設計。
  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）。
    - マクロニュースは predefined キーワードでフィルタし、OpenAI に JSON 出力を要求してスコアを取得。
    - API 呼び出し失敗時のフェイルセーフ（macro_sentiment=0.0）やリトライ制御を実装。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
- データモジュール（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日ユーティリティを実装。
    - market_calendar テーブルが未取得の場合は曜日ベースのフォールバック（土日を非営業日扱い）。
    - calendar_update_job: J-Quants API からの差分取得と保存、バックフィル（直近数日）の取り込み、健全性チェックを実装。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー一覧等を保持）。
    - 差分更新・バックフィル・品質検査の実装方針を定義。
  - etl モジュールで ETLResult を再エクスポート。
- Research モジュール（kabusys.research）
  - factor_research: calc_momentum / calc_value / calc_volatility 実装
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）
    - Value（PER, ROE を raw_financials から取得）
    - Volatility（20 日 ATR, 相対 ATR, 20 日平均売買代金, 出来高比率）
    - DuckDB を用いた SQL 主導の実装、データ不足時は None を返す挙動。
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank 実装
    - 将来リターンの計算（複数ホライズン対応、horizons の検証）
    - Spearman ランク相関による IC 計算（rank 関数は同順位を平均ランクで処理）
    - 基本統計量サマリー（count/mean/std/min/max/median）
  - research パッケージの公開 API を整理（各種関数を __all__ でエクスポート）。
- 内部ユーティリティ
  - DuckDB に依存した多くの処理で、空の executemany を避ける等の互換性対策を追加。
  - OpenAI 呼び出しはモジュールごとに private 関数を持たせ、ユニットテストで差し替えやすく設計。

Changed（変更）
- 初版のため既存からの変更は無し。

Fixed（修正）
- 初版のため修正履歴は無し。

Notes（注意事項 / 設計上の決定）
- OpenAI の利用
  - gpt-4o-mini + JSON mode を利用する想定。API キーは引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY を参照。
  - API 失敗時にはフェイルセーフで中立スコア（0.0）やスキップを行い、処理を継続する設計。
- ルックアヘッドバイアス対策
  - AI スコアリング・レジーム判定では内部で現在時刻を参照しない（target_date 未満 / 前日ウィンドウの排他条件などを使用）。
- データベース（DuckDB）
  - SQL でウィンドウ関数を多用し、過去 N レコードや LEAD/LAG を用いて計算。
  - DuckDB の現行制約（executemany の空リスト不可等）を考慮した実装。
- 環境変数パース
  - .env のパースは可能な限りシェル互換の書式に対応（export, quoted string, エスケープ, インラインコメントの特別扱い）。
- 部分書き込みの保護
  - AI スコア等の書き込みは対象コードのみ DELETE → INSERT を行い、部分失敗が発生しても既存データを不必要に消さない設計。
- 必須設定
  - Slack / kabu / J-Quants / OpenAI 等の重要な設定は Settings で必須チェックを行う（未設定時は ValueError を送出）。

Known issues（既知の制限）
- OpenAI からの出力が所定の JSON 構造を満たさない場合、該当チャンクはスキップされる（ログに警告）。
- news_nlp のレスポンスパースは前後に余計なテキストが混在するケースを部分的に復元するが、すべてのケースをカバーするわけではない。
- 一部のユーティリティ（例: jquants_client や monitoring, execution パッケージ内部の実装参照）は本差分に含まれないため、実行環境に応じた追加実装・設定が必要。

Contributing（貢献）
- バグ報告・機能提案は Issue にてお願いします。プルリクエストにて修正を歓迎します。

License
-------
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください。