# CHANGELOG

すべての重要な変更履歴をここに記載します。本ファイルは「Keep a Changelog」準拠の形式で記述しています。

フォーマット:
- 変更はセクション（Added, Changed, Fixed, Deprecated, Removed, Security）ごとに整理しています。
- バージョンはパッケージ内の __version__（0.1.0）に合わせて初版を記載しています。

## [0.1.0] - 2026-04-03

初回リリース（初期実装）。日本株自動売買システム「KabuSys」の基盤機能を実装しました。

### Added
- パッケージ初期公開
  - モジュール構成: kabusys.data, kabusys.research, kabusys.ai, kabusys.config などの主要サブパッケージを追加。
  - パッケージバージョン: 0.1.0

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定値を自動読み込みする機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）により、CWD に依存しない自動ロードを実現。
  - .env/.env.local の読み込み順 (OS 環境変数 > .env.local > .env)。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - export KEY=val、シングル/ダブルクォート、バックスラッシュエスケープ、行コメント等に対応した堅牢なパーサを実装。
  - Settings クラスを提供（J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定などのプロパティ）。
  - 必須環境変数未設定時に明確な ValueError を投げる _require() を実装。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）を実装。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を使って銘柄毎のニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントをスコア化して ai_scores テーブルへ書き込むパイプラインを実装。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window() で提供。
  - バッチ処理（最大 20 銘柄 / API コール）・記事トリム（文字数制限）を実装。
  - レスポンス検証ロジック（JSON復元、results 配列検証、コード照合、数値チェック、±1 のクリップ）を実装。
  - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフを実装。
  - DuckDB に対する安全な置換書き込み（DELETE → INSERT、executemany 空リスト回避）を実装。
  - フェイルセーフ設計：API 失敗時は例外で中断せず該当チャンクをスキップ。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出し market_regime テーブルに保存する実装。
  - マクロキーワードによる raw_news のフィルタリング機能を実装。
  - OpenAI 呼び出しは独立実装とし、API 失敗時のフォールバック（macro_sentiment = 0.0）を採用。
  - 計算はルックアヘッドバイアス対策（target_date 未満のデータのみ使用）を徹底。
  - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT、ROLLBACK 対応）。

- データ基盤ユーティリティ（kabusys.data）
  - ETLResult データクラスと ETL 用インターフェース（pipeline.ETLResult の再エクスポート）を実装。
  - ETL pipeline 基盤（kabusys.data.pipeline）を実装：差分取得、保存（jquants_client 経由、冪等）、品質チェックの集約、結果オブジェクト（ETLResult）。
  - market_calendar を扱うカレンダー管理（kabusys.data.calendar_management）を実装：is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day / calendar_update_job。
    - DB 登録がない場合の曜日ベースフォールバックや、DB の部分的登録にも一貫した動作をする設計。
    - カレンダー更新処理で J-Quants から差分取得→保存（バックフィル・健全性チェック含む）を実装。

- リサーチ機能（kabusys.research）
  - ファクター計算（calc_momentum, calc_value, calc_volatility）を実装：
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離
    - Value: PER / ROE（raw_financials より）
    - Volatility / Liquidity: 20 日 ATR、平均売買代金、出来高比率
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns（任意ホライズンの将来リターン）
    - calc_ic（スピアマンランク相関による IC 計算）
    - factor_summary（基本統計量）
    - rank（平均ランク方式で同順位処理）
  - すべて DuckDB クエリ / 標準ライブラリで完結し、本番口座や外部発注 API に依存しない設計。

### Changed
- （初回リリース）設計方針注記を各モジュールに反映：
  - ルックアヘッドバイアス対策を徹底（target_date ベースでの時間スコープ設計）。
  - DuckDB の互換性を意識した実装（executemany の空リスト回避、date 型整合処理など）。
  - 外部依存（OpenAI 呼び出し）はカプセル化してテスト容易性を確保（テスト時に差し替え可能）。

### Fixed
- N/A（初版リリースのため、過去バージョンの修正項目はなし）。

### Deprecated
- N/A

### Removed
- N/A

### Security
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY から解決。未設定時は明確なエラーを出力して漏洩リスクのある挙動を回避。
- .env 読み込みで OS 環境変数を保護する protected セットを導入（.env.local のオーバーライド挙動も制御）。

## 既知の制約 / 注意点
- OpenAI（gpt-4o-mini）への呼び出しは外部 API に依存するため、API レスポンスやレートによって処理結果が変動します。実行時は OPENAI_API_KEY を設定してください。
- news_nlp/regime_detector はレスポンスの不整合や API 障害時にフェイルセーフ（該当データのスキップや 0.0 フォールバック）する設計ですが、完全な再現性を求めるユースケースでは API 可用性の確保が必要です。
- DuckDB と SQL の挙動に依存するため、DuckDB のバージョン差異に注意（executemany の挙動等）。
- calendar_update_job は J-Quants クライアント（jquants_client）に依存します。API 仕様変更時は影響があります。

## マイグレーション / 利用開始メモ
- 環境変数設定:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（Settings のプロパティを参照）
  - OpenAI を利用する場合: OPENAI_API_KEY を設定（score_news / score_regime の引数でも注入可）
- データベース:
  - デフォルトの DuckDB パスは data/kabusys.duckdb、SQLite（監視）デフォルトは data/monitoring.db。必要に応じて環境変数でオーバーライド可能。
- テスト:
  - OpenAI 呼び出し関数は内部でラップしているため、unittest.mock.patch により _call_openai_api をモックして単体テストが可能。

---

今後のリリースでは以下を検討しています（例）:
- ai_scores / market_regime の追加入力項目・メタ情報保存。
- OpenAI 呼び出しのロギング・監査強化（プロンプト保存ポリシー）。
- ETL の並列化・進捗監視 API。