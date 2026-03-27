# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

全般:
- このリポジトリは日本株自動売買システム "KabuSys" の初期実装を含みます。
- パッケージバージョン: 0.1.0

## [0.1.0] - 2026-03-27

### 追加 (Added)
- パッケージメタ情報
  - パッケージ初期化: kabusys.__init__ にて __version__ = "0.1.0" を定義し、公開サブパッケージを宣言 (data, strategy, execution, monitoring)。

- 設定/環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を読み込む自動ローダーを実装（プロジェクトルート検出に .git / pyproject.toml を使用）。
  - .env/.env.local の読み込み順序を実装（OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - 複雑な .env 行のパース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - Settings クラスを追加し、必須値のチェック（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）とデフォルト値（KABU_API_BASE_URL、データベースパス等）を提供。
  - 環境変数検証ロジック（KABUSYS_ENV, LOG_LEVEL の許容値チェック）および is_live / is_paper / is_dev のユーティリティを追加。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）:
    - raw_news と news_symbols を参照し、指定タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）に基づいて記事を銘柄毎に集約。
    - OpenAI（gpt-4o-mini）を用いたバッチセンチメント評価（JSON Mode）を実装。1 API コールで最大 _BATCH_SIZE=20 銘柄まで処理。
    - 入力トリミング（1銘柄当たり最大記事数・最大文字数）およびリトライ（429・ネットワーク・タイムアウト・5xx に対するエクスポネンシャルバックオフ）を備える。
    - API レスポンスの厳密なバリデーション、スコアの ±1.0 クリップ、結果を ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
    - API キー注入可能（api_key 引数または OPENAI_API_KEY 環境変数）。

  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321（Nikkei 225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を使用し、ma200_ratio の計算、マクロキーワードでニュース抽出、OpenAI による macro_sentiment 評価を実装。
    - レジームスコア合成、ラベル判定、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を提供。
    - API 呼び出し失敗時は macro_sentiment=0.0 のフェイルセーフ、最大リトライ回数とバックオフを実装。
    - ルックアヘッド防止のため内部で datetime.today()/date.today() を直接参照しない設計。

- データモジュール (kabusys.data)
  - カレンダー管理（kabusys.data.calendar_management）:
    - JPX カレンダー（market_calendar）を扱うユーティリティを実装（営業日判定、次/前営業日、期間内営業日リスト、SQ 判定）。
    - DB にカレンダーがない場合は曜日ベース（土日除外）のフォールバックにより一貫した判定を提供。
    - calendar_update_job を実装し、J-Quants API から差分取得して market_calendar を冪等に更新（バックフィル、健全性チェックを含む）。

  - ETL パイプライン関連（kabusys.data.pipeline / etl）:
    - ETLResult データクラスを公開（ETL 実行結果の集約: fetched/saved 数、品質チェック・エラーの収集）。
    - 差分取得、バックフィル、品質チェック（quality モジュールと連携）を想定したユーティリティを実装。
    - DuckDB を使用した最大日付取得やテーブル存在チェック等のヘルパーを提供。
    - jquants_client 経由の保存処理を想定（fetch/save の抽象化ポイントを確保）。

- 研究向けモジュール (kabusys.research)
  - factor_research:
    - Momentum, Value, Volatility, Liquidity 等の定量ファクター計算関数を実装。
    - calc_momentum, calc_volatility, calc_value を提供（prices_daily / raw_financials のみ使用）。
    - 各関数は (date, code) をキーとした辞書リストを返す仕様。
    - DuckDB のウィンドウ関数や LAG/AVG を利用した実装でデータ不足時の None 処理を明示。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意 horizon 対応）、IC（Information Coefficient）計算 calc_ic（Spearman ランク相関）、rank, factor_summary 等の探索用ユーティリティを実装。
    - 外部依存なし（標準ライブラリのみ）、欠損/有限値チェック等を含む堅牢な実装。

- その他の実装上の配慮
  - DuckDB を前提とした SQL 実行と結果処理。
  - API 呼び出し周りはテスト差し替え（unittest.mock.patch）を想定した設計（内部 _call_openai_api をモジュール単位で分離）。
  - ロギングを各モジュールに広く導入し、エラー時の詳細ログ／警告を出力。
  - DB 書き込みは冪等性を重視（DELETE→INSERT、オンコンフリクトや executemany の互換性に配慮）し、例外時には ROLLBACK を試行。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### 破壊的変更 (Breaking Changes)
- 初版リリースのため該当なし。ただし以下の外部前提があります:
  - DuckDB を用いること、特に executemany に関するバージョン依存の挙動（DuckDB 0.10 系での空リストバインド回避）を前提とした実装が含まれる点。
  - OpenAI SDK の応答形式 / 例外クラスに依存しており、将来 SDK の API が変わると一部ハンドリングを調整する必要がある可能性。

### セキュリティ (Security)
- 初期リリースのため該当なし。
- 注意: OpenAI API キーや各種トークンは環境変数/ .env に保存される前提。運用時は適切な秘密管理を推奨。

### 既知の制約・注意点 (Known issues / Notes)
- news_nlp / regime_detector は OpenAI の JSON Mode を利用する期待で実装されているが、現実には余分なテキストが混入することがあるためパーサの救済処理（先頭と末尾の {} の抽出）を導入している。完全な堅牢化にはさらに厳密なレスポンス検証や再試行戦略が有効。
- API のリトライ対象・非対象の判定は現状の実装に依存（429・ネットワーク・タイムアウト・5xx を主にリトライ）。他の例外は基本的にスキップする設計。
- カレンダー更新ジョブは jquants_client の fetch/save を利用する想定（実際の API クライアント実装に依存）。
- ルックアヘッドバイアス防止のため、スコアリング関数は内部で date.today() を参照しない設計になっている。すべての関数は外部から target_date を明示的に渡すことが前提。
- .env パーサはかなり強力だが、非常に特殊な .env の書式（複雑なインラインコメントや複数行値等）に対応しない場合がある。

---

今後の予定（例）
- strategy / execution / monitoring の初期実装（バックテスト・注文実行・モニタリング連携）の追加
- テストカバレッジ拡充（ユニット/統合テスト）、CI/CD パイプラインの整備
- jquants_client の実装/モック、DuckDB スキーマ定義と初期データロードスクリプトの追加

（以上）