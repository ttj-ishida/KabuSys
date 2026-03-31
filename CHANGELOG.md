# CHANGELOG

すべての着目すべき変更は Keep a Changelog の形式に従って記載しています。  
バージョン番号はパッケージ定義（kabusys.__version__ = "0.1.0"）に基づきます。日付はコードベースの現時点（2026-03-31）を使用しています。  

全般:
- 本リリースは初期公開相当の機能群をまとめたバージョン 0.1.0 です。
- データ取得・ETL、マーケットカレンダー管理、研究用ファクター計算、ニュースNLP（LLM）連携、マーケットレジーム判定、設定管理など自動売買プラットフォームの基礎機能を提供します。
- 内部設計上の重要な方針（ルックアヘッドバイアス回避、冪等書き込み、フェイルセーフ、DuckDB互換性配慮など）を実装しています。

Unreleased
- なし

0.1.0 - 2026-03-31
Added
- パッケージ初期構成
  - kabusys パッケージの公開モジュール定義を追加（data, strategy, execution, monitoring を __all__ で公開）。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機構を導入（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env と .env.local の優先度制御（OS 環境変数の保護を考慮した override/protected ロジック）。
  - 複数形式の .env 行パース対応（export 句、シングル／ダブルクォート、エスケープ、インラインコメントの扱い）。
  - 必須項目取得用の _require helper と環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
  - 各種設定プロパティ（J-Quants / kabu ステーション / Slack / データベースパス / 監視閾値 など）。

- AI / ニュース NLP (kabusys.ai.news_nlp)
  - raw_news と news_symbols を集約して銘柄単位でニュースを結合し、OpenAI（gpt-4o-mini）を用いて銘柄ごとにセンチメント（ai_score）を取得して ai_scores に書き込む機能を実装。
  - スコア取得のバッチ処理（1 API 呼び出しで最大 20 銘柄処理）、1 銘柄あたりの記事数/文字数上限の実装。
  - JSON Mode を用いた厳格なレスポンス検証（レスポンスのパース・バリデーション・既知コードのみ採用）。
  - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）、および一部例外でのスキップ（フェイルセーフ）。
  - スコアは ±1.0 にクリップ。DuckDB の executemany の制約を考慮した部分置換（DELETE → INSERT）実装。
  - テスト容易性のため _call_openai_api の差し替えを想定。

- AI / レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（日経225 連動）を対象に 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し日次の市場レジーム（bull/neutral/bear）を判定、market_regime テーブルへ冪等的に保存する機能を実装。
  - prices_daily からの MA200 計算（target_date 未満のデータのみを使用することでルックアヘッドを防止）。
  - マクロニュース抽出（キーワードによるフィルタリング）、LLM 呼び出し結果の JSON パース、スコア合成、閾値に基づくラベル判定。
  - OpenAI クライアント統合（API エラー処理、リトライ、フェイルセーフ時は macro_sentiment=0.0）。
  - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等手順、失敗時は ROLLBACK を行い例外を伝播。

- 研究（Research）モジュール (kabusys.research)
  - ファクター計算群を提供:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（EPS=0/欠損時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などを計算。
  - 特徴量探索ユーティリティ:
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を使用）を一括で算出（デフォルト [1,5,21]）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（有効レコード 3 件未満は None）。
    - rank, factor_summary: ランク付け（同順位は平均ランク）と基本統計量計算を提供。
  - 全て DuckDB に対する SQL／標準ライブラリ実装で外部 API にはアクセスしない方針。

- データ / カレンダー管理 (kabusys.data.calendar_management)
  - market_calendar テーブルを使った営業日判定ロジックを実装:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
  - DB データが不十分な場合は曜日ベースのフォールバック（週末除外）で一貫した判定を行う設計。
  - calendar_update_job: J-Quants から差分（lookahead）でカレンダーを取得して market_calendar に冪等保存。バックフィルと健全性チェックを実装。
  - 最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループを防止。

- データ / ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
  - ETLResult データクラスを導入し ETL の各種カウント／品質問題／エラーを集約する仕組みを提供。
  - ETL の差分更新、バックフィル、品質チェック方針（品質問題は収集して上位判断へ委ねる）をコード内で定義。
  - DuckDB テーブル存在チェック等のユーティリティを提供。
  - kabusys.data.etl で ETLResult を公開再エクスポート。

- 互換性 / 運用配慮
  - DuckDB のバージョン差異（executemany の空パラメータ制約等）に対する回避実装を多数導入。
  - OpenAI 呼び出しに対する明示的リトライ・ログ出力およびテスト代替フックを用意。
  - ルックアヘッドバイアス防止のため datetime.today() / date.today() 参照を最小化する設計（target_date を明示的に受け取る API を多用）。
  - ロギングによる診断性（warning/info/debug レベル）を各所で強化。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

注記（内部実装／設計メモ）
- .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テスト時の isolation に便利）。
- OpenAI 連携は JSON Mode（response_format={"type": "json_object"}）を前提とする実装になっているが、実運用ではモデル挙動に依存するためレスポンスの堅牢なバリデーションを行っている（部分的に前後余白テキストを抽出してパースする復元処理あり）。
- AI スコア処理は部分失敗時に既存データを保護するため、書き込み対象コードを限定した上で DELETE → INSERT を行う設計。
- DuckDB の日付型の扱いや型互換性に配慮して日付変換ユーティリティを提供している。

今後の予定（想定）
- strategy / execution / monitoring モジュールの詳細実装（現在はパッケージ公開対象としてプレースホルダあり）。
- テスト補強（ユニット・統合テスト）、CI ワークフロー、ドキュメントの拡充。
- OpenAI API 周りのエラーハンドリング改善（コスト・レート制限戦略の追加）やモデルの切替容易性向上。

--- 

この CHANGELOG はコードベースの実装内容（ソースコード内の docstring、関数名、コメント、定数等）から推測して作成しています。実際のリリースノート作成時は実際のコミット履歴・マージ記録・CHANGELOG の管理方針に従って調整してください。