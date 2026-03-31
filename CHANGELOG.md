CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  

フォーマット:
- 変更はバージョンごとに分け、日付を付記します。
- 各バージョンは Added / Changed / Fixed / Deprecated / Removed / Security のカテゴリで整理します。

v0.1.0 - 2026-03-31
-------------------

初回リリース。日本株自動売買システムのコアライブラリを提供します。主な追加内容は以下の通りです。

Added
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ を追加。バージョンは 0.1.0。公開サブパッケージ: data, strategy, execution, monitoring。
- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数からの自動読み込み実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサーは以下に対応:
    - 空行・コメント行（#）無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のエスケープ処理
    - インラインコメントルール（クォート外で直前がスペース/タブの # をコメント扱い）
  - Settings クラスを提供し、主要な設定値の取得と検証を提供:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパス）
    - KABUSYS_ENV の検証（development / paper_trading / live のみ許容）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- データ基盤モジュール (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルを利用した営業日判定ユーティリティ:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にカレンダーデータがない場合は曜日ベースでフォールバック（週末は非営業日）。
    - カレンダー夜間更新ジョブ calendar_update_job を実装。J-Quants API 経由で差分取得・バックフィル・保存（jquants_client 連携）。
    - 健全性チェック、最大探索日数の制限、バックフィル日数などを備え安全に運用できる設計。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開。ETL の取得数・保存数・品質チェック結果・エラーメッセージを集約。
    - 差分取得・バックフィル・品質チェックの方針に基づく設計。
    - テーブル存在チェック、最大日付取得ユーティリティ等を実装。
  - jquants_client 経由の差分保存設計に対応するインターフェースを準備。
- 研究（Research）モジュール (kabusys.research)
  - ファクター計算 (research.factor_research)
    - Momentum（1M/3M/6M リターン、200日移動平均乖離）
    - Value（PER, ROE。raw_financials から取得）
    - Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）
    - 各関数は DuckDB の prices_daily / raw_financials を参照し、(date, code) キーの辞書リストを返す。
    - データ不足時の None 処理やログ出力のポリシーを明確化。
  - 特徴量探索 (research.feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン算出。horizons の検証あり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。レコード不足時は None。
    - rank, factor_summary: ランク化とファクター統計量サマリを提供。
- AI モジュール (kabusys.ai)
  - ニュース NLP (ai.news_nlp)
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols から銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価。結果を ai_scores テーブルへ置換保存（DELETE→INSERT、部分失敗に強い）。
    - ニュースウィンドウ（JST 基準）を calc_news_window で計算（前日 15:00 JST ～ 当日 08:30 JST を対象）。
    - バッチ処理: 最大 20 銘柄/回のバッチ、1銘柄当たりの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - OpenAI 呼び出しは JSON Mode を使用し、レスポンスの堅牢なバリデーションを実装（部分復元ロジック含む）。
    - リトライ戦略: 429/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ。その他のエラーはスキップし続行（フェイルセーフ）。
    - スコアは ±1.0 にクリップ。書き込みはトランザクションで実行し、ROLLBACK 保護。
    - 公開関数: score_news を __all__ に公開。
  - 市場レジーム判定 (ai.regime_detector)
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日 MA 乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。結果を market_regime テーブルへ冪等書き込み。
    - マクロ記事は raw_news からキーワードフィルタで抽出。OpenAI（gpt-4o-mini）を用いた JSON レスポンス解析とリトライ制御を実装。
    - API 失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。MA 計算でデータ不足時は中立値を使用。
    - レジーム合成値はクリップし閾値でラベルを決定（BULL / BEAR の閾値設定あり）。
- 一貫した設計原則
  - ルックアヘッドバイアス防止: datetime.today() / date.today() を直接参照しない設計（呼び出し側が target_date を渡す）。
  - DuckDB を主要な永続化層として使用。SQL + Python のハイブリッド実装。
  - OpenAI SDK を利用した LLM 呼び出しで、テスト時に差し替え可能な内部ラッパー関数を用意（unittest.mock.patch を想定）。
  - 依存は最小化（標準ライブラリ + duckdb + openai 等）。

Changed
- 初版リリースにつき該当なし。

Fixed
- 初版リリースにつき該当なし。

Deprecated
- 初版リリースにつき該当なし。

Removed
- 初版リリースにつき該当なし。

Security
- 初版リリースにつき該当なし。環境変数および API キーの取り扱いは Settings を通じて明示的に要求され、.env 自動読み込みは環境で無効化可能。

Notes / Usage 注意事項
- OpenAI API キー: score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY を参照します。未設定時は ValueError を送出します。
- DB スキーマ: 各機能は特定のテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）存在を前提とします。実行前にスキーマが準備されていることを確認してください。
- テスト容易性: 各種外部 API 呼び出し部分は内部ラッパーを通しており、テストでパッチすることを想定した設計になっています。
- ログ: 各モジュールは詳細なログを出力するよう設計されており、API失敗やパース失敗時には WARN/INFO/DEBUG が出力されます。

今後の予定（例）
- strategy / execution / monitoring パッケージの実装拡充（注文実行ロジックやモニタリング連携）。
- より多くの品質チェックとデータ補正ルールの導入。
- CI 上での DuckDB スキーマ検証・統合テストの整備。

--- 

この CHANGELOG はコードベースのコメント、ドキュメンテーション文字列、および公開 API から推測して作成しています。実際のリリースノート作成時には、マージされた PR やコミット履歴を参照して補完してください。