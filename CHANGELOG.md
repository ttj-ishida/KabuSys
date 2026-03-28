# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
このファイルでは主にコードベースの初版リリースに含まれる機能・設計上の注意点・公開 API をまとめています。

なお、バージョン番号はパッケージ定義 (src/kabusys/__init__.py) に準拠しています。

## [Unreleased]

（現時点のリポジトリは初回リリースの状態のため Unreleased は空です。）

---

## [0.1.0] - 2026-03-28

初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開。パッケージバージョンは 0.1.0。
  - kabusys.__all__ により外部公開想定のサブパッケージ名（data, strategy, execution, monitoring）を宣言。

- 設定・環境管理 (src/kabusys/config.py)
  - .env ファイルと環境変数から設定を読み込む自動ローダを実装。
    - 自動ロードの優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1（テスト用など）。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応、インラインコメント処理など）。
  - 環境値取得のラッパ Settings クラスを提供（settings インスタンスを公開）。
    - 必須設定に対する _require() を実装し、未設定時に ValueError を送出。
    - サポートする設定例:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH, SQLITE_PATH
      - KABUSYS_ENV（development / paper_trading / live の検証）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - settings.is_live / is_paper / is_dev ヘルパーを提供。

- データプラットフォーム周り (src/kabusys/data)
  - calendar_management.py
    - JPX カレンダー取得・保持ロジック（market_calendar テーブル）と営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得の場合は曜日（土日）ベースのフォールバックを採用。
    - calendar_update_job により J-Quants から差分取得して冪等保存（バックフィル、健全性チェック含む）。
  - pipeline.py / etl.py
    - ETL パイプライン用のユーティリティと ETLResult データクラスを実装。
    - 差分取得・保存・品質チェックの設計に基づく処理を実現するための基盤。
    - ETLResult.to_dict() により品質問題をシリアライズ可能。
  - jquants_client 等のクライアント層（参照実装想定）を利用するインターフェースを想定。

- 研究・因子分析 (src/kabusys/research)
  - factor_research.py
    - モメンタム（1M/3M/6M、200日 MA 乖離）、ボラティリティ/流動性（20日 ATR、平均売買代金、出来高変化率）、バリュー（PER, ROE）を計算する関数を実装。
    - calc_momentum, calc_volatility, calc_value を提供。すべて DuckDB の prices_daily / raw_financials を参照して計算。
    - Zスコア正規化は別モジュール（kabusys.data.stats）を利用する設計。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank、factor_summary を実装。
    - 外部依存（pandas 等）に頼らず標準ライブラリ + DuckDB を用いた実装。
  - research.__init__ で主要関数群を再エクスポート。

- AI（ニュース NLP / レジーム判定） (src/kabusys/ai)
  - news_nlp.py
    - raw_news / news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI（gpt-4o-mini）を用いて銘柄毎にセンチメントスコアを算出。
    - バッチ処理（1回あたり最大 20 銘柄）、1 銘柄あたり最大記事数・文字数制限、JSON mode を使用した応答パースを実装。
    - リトライ戦略（429, ネットワーク断, タイムアウト, 5xx に対する指数バックオフ）、レスポンスの厳格なバリデーション、スコアの ±1.0 クリッピング、結果の部分置換（DELETE → INSERT）による冪等性保護を実装。
    - calc_news_window(target_date) により JST 基準のニュースウィンドウ（前日 15:00～当日 08:30 JST）を UTC naive datetime で返すユーティリティを提供。
    - score_news(conn, target_date, api_key=None) を公開。OpenAI API キーが未指定かつ環境変数 OPENAI_API_KEY がない場合は ValueError を送出。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来の LLM マクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定する score_regime(conn, target_date, api_key=None) を実装。
    - raw_news からマクロキーワードで記事を抽出、OpenAI（gpt-4o-mini）でマクロセンチメントを評価しスコア合成。
    - LLM 呼び出しの失敗時は macro_sentiment=0.0 とするフェイルセーフ、API リトライ（指数バックオフ）を実装。
    - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
  - ai.__init__ で score_news をエクスポート。

- テスト・運用を考慮した設計上の注意点（ドキュメント化）
  - ルックアヘッドバイアスを防ぐため、主要な関数は datetime.today()/date.today() を参照せず、必ず target_date を引数で受け取る設計。
  - API キーや外部状態への依存を明示し、未設定時の例外挙動を明文化。
  - OpenAI 呼び出し部分はテストで差し替え可能（_call_openai_api の patch）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env 読み込みの堅牢化
  - ファイル読み込み失敗時に warnings.warn を出す実装とし、読み込み失敗でプロセスがクラッシュしないようにした。
  - .env の上書きロジックに protected キーセットを導入し、OS 環境変数をユーザ設定で不用意に上書きしないようにした。

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY から供給する設計。ログ等に API キーを出力しないことを想定。
- .env 自動ロードで OS 環境変数を保護する仕組み（protected set）を導入。

---

## 既知の前提・注意事項 / マイグレーションメモ
- DuckDB をデータ層として利用する前提で実装されています。関数は特定のテーブルスキーマ（例: prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials, market_regime 等）を参照します。これらテーブルの存在・スキーマ整合性を事前に用意してください。
- OpenAI 呼び出しを行う機能（score_news, score_regime）は実行時にネットワークアクセスと API クレジットが必要です。テストでは _call_openai_api をモックする想定です。
- .env パースの挙動は POSIX の .env 形式に近く実用上の妥当性を考慮していますが、特殊なエッジケースは手動確認してください。
- ETL とカレンダー更新は外部 API（J-Quants 等）との連携を前提とします。API クライアント（kabusys.data.jquants_client）の実装・エラー処理に依存します。

---

（注）リリースノートはコード内容から推測して作成しています。実際のリリース履歴や公開日付・外部クライアント実装等はプロジェクトの正式情報に従って調整してください。