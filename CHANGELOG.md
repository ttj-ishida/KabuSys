# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
このプロジェクトの初期リリースに相当する内容を、ソースコードから推測してまとめています。

なお日付はコード解析時点（2026-03-31）を使用しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-31

### Added
- 基本パッケージ構成
  - kabusys パッケージの公開モジュールを定義（data, strategy, execution, monitoring）。
  - バージョン: 0.1.0

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイル（.env, .env.local）および OS 環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探すため、CWD に依存しない。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途）。
  - .env のパースは以下に対応:
    - コメント行、空行、export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなし値のインラインコメント処理（直前がスペース/タブの場合のみ）
  - 既存 OS 環境変数を保護しつつ .env.local により上書き可能（.env は上書きしない）。
  - Settings クラスを提供し、必須環境変数取得用の _require を含む。
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト値を持つ項目: KABU_API_BASE_URL, DUCKDB_PATH（data/kabusys.duckdb）, SQLITE_PATH（data/monitoring.db）
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパー

- AI（LLM）関連（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols をソースとして、銘柄ごとにニュースを集約して OpenAI (gpt-4o-mini) に送信しセンチメントスコアを ai_scores テーブルへ保存する処理を実装。
    - 特徴:
      - JST ベースの時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で計算し、DB の UTC 時刻と比較する。
      - 1 銘柄あたりの最大記事数／最大文字数でトリム（トークン肥大化対策）。
      - 最大 20 銘柄ずつバッチ送信（_BATCH_SIZE）。
      - JSON Mode を使った厳密な JSON 出力を期待しつつ、前後余計なテキストが混ざる場合の復元ロジックを導入。
      - レートリミット（429）・ネットワーク断・タイムアウト・5xx を指数バックオフでリトライ。その他の APIError は失敗扱いでスキップ。
      - レスポンスのバリデーション（results 配列の存在、code の照合、スコアの数値性、有限値判定）、およびスコアの ±1.0 クリップ。
      - 書き込みは部分失敗時の保護を考慮し、対象コードのみ DELETE → INSERT の冪等更新を実施（DuckDB の executemany の注意点を考慮）。
      - テスト用フック: OpenAI 呼び出しを _call_openai_api をパッチすることで差し替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次のレジーム（bull / neutral / bear）を判定し market_regime テーブルへ保存する処理を実装。
    - 特徴:
      - prices_daily から 1321 の過去 _MA_WINDOW 日データにより ma200_ratio を計算（target_date 未満のデータのみ使用、ルックアヘッドバイアス防止）。
      - raw_news からマクロキーワードでフィルタしたタイトルを取得し、LLM（gpt-4o-mini）により macro_sentiment を取得（記事なしなら LLM 呼ばず macro_sentiment=0）。
      - OpenAI 呼び出しはリトライロジックを備え、失敗時は macro_sentiment=0.0 にフォールバックして継続（例外は上げない）。
      - 最終スコアは clip され、閾値に応じてラベル化し DB に冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
      - テスト用に OpenAI 呼び出しを差し替え可能。
    - 設計上の注意点・安全策を明記（ルックアヘッド対策、API 失敗フェイルセーフ等）。

- Research（kabusys.research）
  - factor_research: ファクター計算の実装
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率
    - calc_value: EPS ベースの PER、ROE（raw_financials から最新レコードを取得）
    - いずれも DuckDB に対する SQL ウィンドウ関数を活用し、date, code をキーとした dict リストを返す。
    - データ不足時の挙動（例: MA200 行数不足 → None）を明記。
  - feature_exploration: 将来リターン・IC・統計サマリー等の実装
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得、入力検証（horizons の型/範囲）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関を計算（有効レコード < 3 なら None）。
    - rank: 同順位は平均ランクを返す実装（丸めによる ties 対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算。
    - 外部依存を避け、標準ライブラリのみで実装。

- Data（kabusys.data）
  - calendar_management: 市場カレンダー管理と営業日補助関数
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar が存在しない場合は曜日ベースのフォールバック（週末除外）を行う。
    - カレンダーの夜間バッチ更新 job (calendar_update_job) を実装し、J-Quants クライアント経由で差分取得・バックフィル・健全性チェックを行う。
  - pipeline / etl
    - ETLResult データクラスを公開（結果集約、品質問題・エラー列挙、has_errors/has_quality_errors プロパティ、to_dict）。
    - ETL の補助関数（テーブル存在確認、最大日付取得など）を実装。
    - DuckDB と互換性を考慮した実装（ex: executemany 空リスト回避など）。
  - etl を公開インターフェースとして再エクスポート（ETLResult）。

- テスト・開発に役立つ実装ノート
  - OpenAI 呼び出しを差し替え可能な設計（ユニットテストでモック可能）。
  - DuckDB の特性（executemany の空リスト不可など）をコメントで明示。
  - 各モジュールでルックアヘッドバイアス防止のため date.today()/datetime.today() を直接参照しない方針を採用（target_date を明示的に受け取る）。

### Changed
- 初回リリースのため該当なし（現状は新規追加のみの想定）。

### Fixed
- 初回リリースのため該当なし（現状は新規追加のみの想定）。

### Deprecated
- なし

### Removed
- なし

### Security
- 環境変数（API トークン等）は Settings 経由で必須チェックを行う設計。  
  - OpenAI API キーは score_news / score_regime に明示的な api_key 引数を渡すか環境変数 OPENAI_API_KEY を設定する必要があります。
- .env 読み込みはデフォルトで有効だが、テスト等で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / Upgrade considerations
- データベース（DuckDB）側に以下のテーブル／スキーマが存在することが前提となる機能が多数あります:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など
- OpenAI SDK のバージョン差異による例外クラスや属性差異（例: APIError に status_code がある場合/ない場合）を考慮した堅牢化処理を行っています。
- DuckDB のバージョンによっては list 型バインドの挙動が異なるため、互換性を取る実装を採用しています（個別 DELETE の実行等）。
- LLM の応答パースは堅牢化されているものの、常に正しい JSON が返るとは限らないため、不正応答はスキップしてフォールバック（0.0）する方針です。
- 本リリースは「アルゴリズム実装とデータパイプライン／AI 関連処理の骨組み」を提供することを目的としており、本番稼働時には DB スキーマ、認証情報、API レート制限運用、モニタリング等を整備してください。

---

もし特定ファイルごと・関数ごとの変更点をより詳細に分離したい場合や、想定されるリリースノート（利用者向け）に整形したい場合は、その形式に合わせて出力します。どの粒度で欲しいか教えてください。