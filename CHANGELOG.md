CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従っています。
バージョニングは SemVer を想定しています。

[0.1.0] - 2026-04-03
--------------------

Added
- 初回公開: KabuSys 日本株自動売買システムのコアモジュール群を追加。
  - パッケージのトップレベル: kabusys パッケージ (__version__ = 0.1.0)。主要サブパッケージを公開: data, strategy, execution, monitoring。
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダ実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD に依存しない動作）。
  - .env パーサ実装: コメント行、export プレフィックス、シングル/ダブルクォート内のエスケープ、行内コメント処理などに対応。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - OS 環境変数の上書き保護機能（.env.local を override で読みつつ OS 環境変数を protected として扱う）。
  - Settings クラスを提供し、J-Quants / kabu ステーション / LINE / DB /監視 などの設定プロパティを公開。KABUSYS_ENV / LOG_LEVEL の値検証を実装。
  - デフォルト値（例: KABU_API_BASE_URL、DUCKDB_PATH、PID_FILE_PATH 等）を設定。
- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメント（-1.0〜1.0）を算出して ai_scores に保存する処理を実装。
    - タイムウィンドウ計算 (前日15:00 JST ～ 当日08:30 JST) と記事トリム（記事数上限・文字数上限）の実装。
    - バッチ処理（1 API コールあたり最大20銘柄）、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時に既存スコアを保護する差し替えロジック（DELETE → INSERT）。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフとリトライを実装。
    - テストフレンドリーな _call_openai_api の置換想定（unittest.mock で差し替え可能）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出（キーワードによるフィルタ）、OpenAI 呼び出し（gpt-4o-mini、JSON 出力想定）、API エラー時のフォールバック（macro_sentiment=0.0）、リトライ・バックオフ実装。
    - レジームスコア合成と閾値判定、DB トランザクション制御（BEGIN/DELETE/INSERT/COMMIT、例外時 ROLLBACK）。
- Research モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum（1M/3M/6Mリターン、200日MA乖離）、Volatility（20日ATR・相対ATR・平均売買代金・出来高比率）、Value（PER/ROE）を DuckDB の prices_daily / raw_financials を用いて計算する関数を実装。
    - データ不足時の None 扱い、結果を (date, code) を含む dict リストで返す設計。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ファクター統計サマリー、ランク化ユーティリティを実装。
    - pandas 等に依存せず標準ライブラリで完結する実装。
  - いくつかのユーティリティ関数を再エクスポート（例: zscore_normalize、calc_momentum 等）。
- Data モジュール (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を前提とした is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の判定ロジックを実装。
    - DB にデータがない場合は曜日ベースのフォールバック（週末除外）を使用。DB とフォールバックで一貫した結果を返すよう考慮。
    - calendar_update_job を実装し、J-Quants API から差分取得して market_calendar を冪等に更新（バックフィル・健全性チェックを含む）。
  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult データクラスを導入し、ETL の取得/保存件数、品質検査結果、エラー一覧を記録できるようにした。
    - 差分更新・バックフィル・品質チェックの設計方針を実装（J-Quants クライアントを利用）。
  - etl モジュールで ETLResult を再エクスポート。
- 共通設計方針（クロスモジュール）
  - すべての AI / 研究系関数は datetime.today()/date.today() を内部で参照せず、外部から target_date を受け取ることでルックアヘッドバイアスを排除。
  - OpenAI API 呼び出しは堅牢化（JSON パースの復元ロジック、リトライ、フェイルセーフフォールバック）。
  - DuckDB を主要なローカル分析 DB として利用し、SQL + 少量の Python で処理を実装。
  - DB 書き込みは冪等性・部分失敗に配慮（対象コードの絞り込み、個別 DELETE / INSERT、トランザクション制御）。

Changed
- n/a（初回リリースのため「Added」に相当する実装が中心）

Fixed
- 開発中に見つかった堅牢性向上を反映（初期実装として以下を確立）
  - .env パースのクォート・エスケープ・コメント処理の改善。
  - OpenAI レスポンスの不整合（前後余計テキスト混在）に対する JSON 抽出ロジック。
  - DuckDB executemany の空リスト制約へ対応するガード（空時は実行しない）。

Security
- n/a

Notes / Implementation details
- OpenAI モデルは現状 gpt-4o-mini を利用する設計（JSON Mode を期待）。
- ニューススコアリングのバッチサイズやリトライ回数・バックオフ等はソース内定数で調整可能（_BATCH_SIZE=20, _MAX_RETRIES=3, _RETRY_BASE_SECONDS=1.0 など）。
- ETL / カレンダー更新は J-Quants クライアントに依存するため、実行環境では適切な API 認証情報（例: JQUANTS_REFRESH_TOKEN）を設定する必要あり。
- 自動環境読み込みはプロジェクトルートが検出できない場合はスキップされ、テスト環境向けに無効化できる。

未解決／今後の改善候補
- strategy / execution / monitoring の具体的な実装は今後のリリースで拡充予定（本バージョンではコアユーティリティ・研究・データ基盤を中心に実装）。
- ai モジュールのさらなる評価指標追加、モデル切替の抽象化、並列化オプションの導入検討。
- ETL の品質チェック結果に基づく自動アラートやリトライポリシーの強化。

--- 

以上。必要であればリリースノートの粒度（個別関数ごとの変更／設計注釈）をさらに細かく展開できます。