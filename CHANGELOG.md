# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、本CHANGELOGはコードベースから推測した変更点／機能説明をもとに作成しています。

## [Unreleased]

### Added
- なし（次回リリースに向けた未反映の変更はありません）

---

## [0.1.0] - 2026-03-27

初回公開リリース。以下の主要機能とモジュールを実装しました。

### Added
- パッケージ基盤
  - kabusys パッケージ初期バージョン（__version__ = "0.1.0"）。
  - パッケージ公開APIとして data, strategy, execution, monitoring を __all__ に定義。

- 設定管理（kabusys.config）
  - .env / .env.local ファイルと OS 環境変数を組み合わせた自動設定読み込みを実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサは以下に対応：
    - export KEY=val 形式
    - シングル/ダブルクォートとバックスラッシュエスケープ
    - インラインコメントの取り扱い（クォート有無に応じた解析）
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得可能：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（既定: data/kabusys.duckdb）, SQLITE_PATH（既定: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）と LOG_LEVEL の検証
    - is_live / is_paper / is_dev の便利プロパティ

- AI（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を読み、銘柄ごとにニュースを集約。
    - OpenAI（gpt-4o-mini）へバッチ送信し、{"results": [{"code": "...", "score": ...}, ...]} 形式でスコアを取得。
    - バッチサイズ、記事数・文字数上限、JSONレスポンスの堅牢なバリデーションを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - スコアは ±1.0 にクリップ。取得したスコアを ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
    - 時間ウィンドウ計算（JST基準） calc_news_window を提供（テスト容易性のため datetime.today/date.today を直接参照しない設計）。
    - テスト用に _call_openai_api を差し替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を参照し、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI 呼び出しは専用実装で、API キー注入可能（api_key 引数 or OPENAI_API_KEY 環境変数）。
    - APIエラー時は macro_sentiment=0.0 のフェイルセーフで継続、リトライとログ出力を実装。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを利用した営業日判定ロジックを提供：
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録が無い日については曜日ベース（土日非営業日）でフォールバック。
    - calendar_update_job により J-Quants API からの差分取得・バックフィル・保存処理を実装。
    - 最大探索日数・バックフィル日数・健全性チェックなど安全対策を導入。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラス（target_date, fetched/saved counts, quality_issues, errors 等）を実装して公開（kabusys.data.etl で再エクスポート）。
    - 差分取得、idempotent な保存（jquants_client の save_* を想定）および品質チェック設計方針を反映。
    - DB 最大日付取得等のユーティリティを実装。
    - backfill を考慮した範囲計算と市場カレンダー連携。

- リサーチ（kabusys.research）
  - Factor 計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20 日 ATR）、流動性（平均売買代金、出来高比率）、バリュー（PER, ROE）等を DuckDB 上の SQL で計算する関数を提供：
      - calc_momentum, calc_volatility, calc_value
    - データ不足時には None を返す等の堅牢性を確保。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン算出（calc_forward_returns）、IC（calc_ic）、ランク化ユーティリティ（rank）、および統計サマリー（factor_summary）を実装。
    - 外部ライブラリへ依存せず標準ライブラリのみで実装。
    - calc_forward_returns は horizons パラメータの妥当性検査、まとめて1クエリで取得する最適化を実装。
    - calc_ic はスピアマン（ランク相関）を実装し、データ不足時は None を返す。

### Changed
- 初回リリースのため該当なし（初実装群）。

### Fixed
- 初回リリースのため該当なし。

### Security
- OpenAI を利用する機能は api_key を引数で注入可能にし、環境変数 OPENAI_API_KEY も利用できるように設計。
- 必須の機密情報（Slack / API トークン等）は Settings 経由で明示的に要求する実装。

### Notes / Design decisions
- ルックアヘッドバイアス防止のため、いずれの処理も内部で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）。
- DuckDB の executemany に空リストを渡せない制約を考慮し、空チェックを行ってから実行する実装。
- DB 書き込みは可能な限り冪等化（DELETE → INSERT や ON CONFLICT 相当の保存）を行う。
- OpenAI 呼出しに対してはリトライ／バックオフ戦略を実装し、API障害時はフェイルセーフ（スコアを 0 またはスキップ）で処理継続。
- テスト容易性のため、内部の OpenAI 呼び出し関数（_call_openai_api）をモック差し替え可能にしている。

---

作成にあたってコードベースから機能・設計方針を推測してまとめています。リリースノートや変更履歴の追加・修正が必要であれば、目的に合わせて日付・詳細・セクションを更新します。