# Changelog

すべての重要な変更はここに記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
初回リリース

### Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - __all__ に data, strategy, execution, monitoring をエクスポート（将来的なサブモジュールの公開インターフェースを宣言）

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装
    - プロジェクトルート検出は .git または pyproject.toml を起点に探索（配布後も CWD に依存しない）
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - .env のパースで `export KEY=val` 形式、クォート内のエスケープ、インラインコメントの扱いに対応
    - .env 読み込み時に OS 環境変数を保護する protected キーセットをサポート
  - Settings クラスを提供（プロパティ経由で各種設定を取得）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須設定として取得（未設定時は ValueError を送出）
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH にデフォルト値を設定
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）のバリデーション
    - is_live / is_paper / is_dev 補助プロパティを追加

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリングモジュール (news_nlp.score_news)
    - raw_news と news_symbols を元に「前日 15:00 JST ～ 当日 08:30 JST」のウィンドウで記事を集約し、銘柄ごとに OpenAI（gpt-4o-mini）でセンチメントスコアを算出
    - バッチ処理: 最大 20 銘柄 / 回、1 銘柄あたり最大 10 記事・3000 文字でトリム
    - JSON Mode を利用した厳密なレスポンス検証およびパースの耐性（前後ノイズが混入した場合の {} 抽出）
    - API エラー（429、ネットワーク、タイムアウト、5xx）は指数バックオフでリトライし、リトライ上限超過時は該当チャンクをスキップ（フェイルセーフ）
    - 成功したスコアのみを ai_scores テーブルへ DELETE → INSERT のトランザクションで置換（部分失敗時に既存データを保護）
  - 市場レジーム判定モジュール (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull / neutral / bear）を判定
    - LLM 呼び出しはニュース用と独立した内部実装（モジュール結合を避ける）
    - API 失敗時は macro_sentiment を 0.0 として処理を継続（フェイルセーフ）
    - market_regime テーブルへ冪等的（BEGIN / DELETE / INSERT / COMMIT）に書き込み

- Research（量的リサーチ）機能 (kabusys.research)
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などを DuckDB 上で計算
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率などを計算
    - calc_value: raw_financials から最新の財務指標を参照し PER / ROE を計算
    - 設計上外部 API にアクセスせず DuckDB と SQL/Python の組合せで計算
  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一括取得
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算
    - factor_summary / rank: ファクター統計サマリーとランク変換ユーティリティ
  - kabusys.data.stats の zscore_normalize を再エクスポート

- Data / ETL 周り (kabusys.data)
  - calendar_management
    - market_calendar に基づく営業日判定・次/前営業日の取得・期間の営業日リスト取得・SQ判定を提供
    - DB にカレンダーが無い場合は曜日（土日）ベースのフォールバックを使用
    - calendar_update_job: J-Quants API を用いた差分取得と market_calendar テーブルへの冪等保存（バックフィル・健全性チェックを実装）
  - pipeline (ETL)
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラー一覧などを集約）
    - 差分更新・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合の検出）を想定した設計
  - etl モジュールで pipeline.ETLResult を再エクスポート

- DuckDB を主要なローカルデータストアとして利用
  - デフォルトの DuckDB ファイルパス: data/kabusys.duckdb（Settings.duckdb_path）
  - SQLite は監視用途等で別パスに保存可能（Settings.sqlite_path）

### Design Notes / Implementation Details
- ルックアヘッドバイアス対策
  - いずれの AI / リサーチ機能も datetime.today() / date.today() を直接参照せず、target_date 引数で日付を明示的に与える設計
  - DB クエリは target_date 未満（排他）や LEAD/LAG の扱いによりルックアヘッドを防止
- OpenAI 呼び出し
  - gpt-4o-mini を想定、JSON モードでの応答整形を前提とした実装
  - 429、接続断、タイムアウト、サーバー 5xx をリトライ対象とする指数バックオフを実装
  - 非致命的な API 失敗時はデフォルト値（0.0）やスキップで継続するフェイルセーフ設計
- トランザクション / 耐障害性
  - 書き込みは明示的な BEGIN / COMMIT / ROLLBACK を使用して冪等性と部分失敗時のデータ保護を確保
  - DuckDB の executemany の挙動（空リスト不可など）を考慮した実装
- レスポンス検証
  - LLM レスポンスは厳密にバリデーション（キー/型/スコアの数値性、既知コードの照合）を行い、不正な結果はスキップ
  - JSON パースに失敗する場合でも最大の復元処理（最外の {} 抽出など）を試みる

### Security
- 機密情報（OpenAI API キー、J-Quants トークン、kabu API パスワード、Slack トークン等）は環境変数経由で取得し、未設定時は明示的にエラーを投げることで早期検出を促す

### Fixed
- （このリリースでは特定のバグフィックス履歴はありません — 初回リリース）

### Deprecated
- （なし）

### Removed
- （なし）

---

注記:
- 実際の外部クライアント実装（例: kabusys.data.jquants_client や live 発注ロジックなど）は本コード断片に含まれていないため、CHANGELOG は現行コードから推測可能な機能・設計方針に基づいて記述しています。