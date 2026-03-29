# CHANGELOG

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

- リリースノートは安定した API と主要機能・設計決定を中心に記載しています。  
- 日付はこのコードベースから推測できる初期公開相当の時点を使用しています。

## [Unreleased]
- 今後の変更点・開発中の機能はここに記載します。

## [0.1.0] - 2026-03-29
初回公開リリース。日本株自動売買フレームワークのコア機能を実装しました。主要な追加点・設計方針は以下の通りです。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = "0.1.0"、主要サブパッケージを公開）。
- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは OS 環境変数からの設定読み込みを自動化（プロジェクトルート検出: .git / pyproject.toml）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env 読み込み時の上書き制御（.env と .env.local の優先度）と OS 環境変数保護（protected）。
  - 高度な .env パーサ実装:
    - export プレフィックス対応（export KEY=val）
    - シングル/ダブルクォート値のエスケープ処理
    - インラインコメントの扱い、無効行スキップ
  - Settings クラスを提供（プロパティ経由で各種必須設定を取得、未設定時は例外を投げる）:
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティ
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）
    - LOG_LEVEL のバリデーション
    - is_live / is_paper / is_dev 補助プロパティ
- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄単位に記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを取得。
    - バッチ処理（銘柄ごとに最大 _BATCH_SIZE=20）とトークン肥大化対策（記事数・文字数上限）。
    - JSON Mode 応答のバリデーション・復元（前後余分テキストの処理）。
    - リトライ / エクスポネンシャルバックオフ（429・ネットワーク断・タイムアウト・5xx の扱い）。
    - DuckDB への冪等書き込み（取得済みコードのみ DELETE → INSERT）。
    - ルックアヘッドバイアス防止（datetime.today() を直接参照しない時間窓設計）。
    - テスト性: _call_openai_api をパッチして差し替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - 日次で ETF(1321) の 200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）の合成により市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出用キーワード集合（日本・米国等）を組み込み。
    - OpenAI 呼び出しに対するリトライ・エラーハンドリングとフェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - 結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - テスト性: _call_openai_api の差し替えを想定。
- Data モジュール（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX マーケットカレンダーを扱うユーティリティ：is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - market_calendar が空の場合は曜日ベースのフォールバック（週末 = 休場）。
    - calendar_update_job: J-Quants API からの差分取得・バックフィル・健全性チェック・保存のフローを実装。
    - 最大探索日数やバックフィル日数等の安全制御を実装（_MAX_SEARCH_DAYS / _BACKFILL_DAYS / _SANITY_MAX_FUTURE_DAYS 等）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - 差分取得、保存（idempotent）、品質チェックの流れに対応する ETLResult データクラスを公開。
    - データ最小取得日・バックフィル・カレンダー先読み等のデフォルト値を定義。
    - DuckDB を前提としたテーブル存在チェックや最大日付取得ユーティリティを実装。
  - jquants_client 関連の抽象化（fetch / save 呼び出しを想定）。
- Research モジュール（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算を実装
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離（データ不足時に None を返す挙動）
    - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比率
    - calc_value: raw_financials からの PER/ROE 取得（EPS=0 や欠損時は None）
    - DuckDB 上の SQL ウィンドウ関数を活用した実装（LOOKUP 範囲に余裕を持たせたスキャン）
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD を活用）
    - calc_ic: スピアマンのランク相関（IC）計算（レコード不足時は None）
    - rank: 同順位は平均ランクとするランク化ユーティリティ（丸めによる ties 対策）
    - factor_summary: 各カラムの基本統計量（count/mean/std/min/max/median）
  - zscore_normalize は kabusys.data.stats から再エクスポート
- テスト性・安全性
  - LLM 呼び出しや外部 API コール箇所は差し替え（モック）しやすい実装（プライベート関数をパッチする想定）。
  - 外部 API 失敗時は例外を投げずフォールバック（中立スコアやスキップ）して処理を継続する設計を採用。
  - DuckDB executemany の空リスト問題に配慮したコード（空のときは呼ばない）。

### Changed
- 初版のため該当なし（新規実装）。

### Fixed
- .env パーサの堅牢化（export プレフィックス・クォート・エスケープ・インラインコメントの扱い）により様々な .env 形式の読み込みに対応。

### Security
- 環境変数の自動読み込みで OS 環境変数を保護する仕組みを導入（.env の上書き回避）。
- API キー未設定時は明示的に ValueError を出して早期検出する設計。

### Notes / Design Decisions
- すべての「日付に依存する処理」はルックアヘッドバイアスを避けるために datetime.today()/date.today() を直接参照しないよう設計している（テスト時は target_date を注入）。
- DuckDB を一次ストアとして前提。SQL（ウィンドウ関数等）を多用することで計算を DB 上で効率的に行う。
- LLM のレスポンスは厳密な JSON を期待するが、実運用上の誤差（前後テキスト混入など）へ耐性を持たせる処理を入れている。
- データ書き込みは可能な限り冪等（DELETE→INSERT や ON CONFLICT 相当）にして部分失敗時のデータ保護を行う。

---

将来的には以下が想定されます（未実装・要検討）
- 単体テスト・統合テストの追加（OpenAI / J-Quants のモックを用いた CI 実行）。
- 発注・実行エンジン（execution）や監視（monitoring）の詳細実装とドキュメント整備。
- Pydantic 等を用いた設定バリデーションの強化や型安全化。