# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

テンプレートに従い、リリース履歴は安定版（日時付き）と未リリース（Unreleased）で管理します。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-04

初回リリース — 日本株自動売買／リサーチ／データ基盤ライブラリ「KabuSys」0.1.0

### Added
- パッケージ基礎
  - kabusys パッケージを公開。バージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を含めた公開設計（将来的拡張を想定）。

- 設定・環境変数管理 (`kabusys.config`)
  - .env/.env.local からの自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込みの優先順位: OS環境変数 > .env.local > .env。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト用）。
  - export 形式やクォート・インラインコメントを考慮した .env パーサ実装（エスケープ処理対応）。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - データベースパスのデフォルト（DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"）
    - 監視用パス（PID ファイル、kill flag）と監視閾値（CPU/MEM/DISK）
    - KABUSYS_ENV（development/paper_trading/live） と LOG_LEVEL のバリデーション
    - ヘルパープロパティ is_live / is_paper / is_dev
  - 必須環境変数未設定時に明瞭な ValueError を送出する _require 関数。

- データプラットフォーム関連 (`kabusys.data`)
  - カレンダー管理モジュール（calendar_management）:
    - market_calendar を使った営業日判定 API を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - 夜間バッチ更新 job（calendar_update_job）: J-Quants API から差分取得 → 冪等保存、バックフィル・健全性チェックを実装。
    - 最大探索日数等の安全装置（_MAX_SEARCH_DAYS 等）。
  - ETL / パイプライン（pipeline, etl）:
    - ETLResult データクラスを公開し ETL 結果を構造化（品質検査結果・エラーの集約）。
    - 差分更新・バックフィル・品質チェックを想定した設計（jquants_client と quality モジュールと連携）。

- AI（自然言語処理）機能 (`kabusys.ai`)
  - ニュース NLP スコアリング（news_nlp.score_news）:
    - raw_news + news_symbols を銘柄別に集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント (ai_score) を ai_scores テーブルへ書き込み。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換）を厳密に扱う calc_news_window。
    - 1チャンク最大 20 銘柄、1銘柄あたり最大 10 記事・3000 文字にトリム。
    - JSON Mode を利用し厳格な JSON 出力を期待、レスポンスの復元・バリデーション実装。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実施。致命的でないエラーはログ出力の上でスキップ（フェイルセーフ）。
    - DuckDB の executemany の制約を考慮した安全な DELETE → INSERT ロジック（部分失敗時に既存データ保護）。
  - 市場レジーム判定（ai.regime_detector.score_regime）:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - _calc_ma200_ratio（データ不足時は中立 1.0 を返す）、_fetch_macro_news（マクロキーワードでフィルタ）、_score_macro（LLM 呼出とリトライロジック）を提供。
    - OpenAI クライアントと JSON Mode を利用、API 失敗時は macro_sentiment=0.0 にフォールバック。
    - 計算結果を market_regime に冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

- リサーチ機能 (`kabusys.research`)
  - ファクター計算（research.factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足は None）。
    - calc_volatility: 20日 ATR、ATR比率、20日平均売買代金、出来高比率等。
    - calc_value: PER、ROE（raw_financials から最新財務データを取得）。
    - DuckDB SQL を主体とした高速集計実装（外部 API へのアクセスなし）。
  - 特徴量探索（research.feature_exploration）:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン計算。horizons の妥当性チェックあり。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算。データ不足時は None を返す。
    - rank: 同順位は平均ランクで扱うランク化関数（丸めにより ties 対策）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。

- その他ユーティリティ
  - OpenAI 呼び出し用のラッパー関数（各モジュールに独立実装）を用意し、テスト時に patch しやすいように設計。
  - ロギング用の詳細メッセージやワーニング挙動を各所に追加。

### Changed
- 新規リリースのため該当なし。

### Fixed
- 新規リリースのため該当なし。

### Security
- OpenAI API キーや各種シークレットは環境変数で管理することを明記（Settings で必須チェックを行い、未設定時は ValueError を投げる）。
- .env の読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD によって無効化可能（テスト等でシークレット漏洩防止を容易にするため）。

### Notes / 実装上の重要な挙動（ユーザ／開発者向け）
- OpenAI Integration:
  - 使用モデル: gpt-4o-mini。JSON mode（response_format={"type": "json_object"}）を前提に実装。
  - API キーは api_key 引数で注入可能（単体テスト容易化のため）、省略時は環境変数 OPENAI_API_KEY を参照。
  - レスポンスパース失敗や API エラーは基本的にフェイルセーフ（0.0 またはスキップ）として処理し、システム全体が停止しないように設計。
  - テストでは kabusys.ai.*._call_openai_api を patch して外部呼び出しをモックできる。

- 時刻／日付扱い:
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を主要処理で直接参照しない設計。target_date を明示的に渡して deterministic に処理する方針。
  - ニュースウィンドウや移動平均などは target_date 未満（排他）でクエリして将来情報が混入しないようにしている。

- DuckDB に関する注意:
  - executemany に空リストを渡すとエラーになるバージョン（例: DuckDB 0.10）があるため、空チェックを行った上で executemany を呼ぶ実装になっている。
  - DB 書き込みは基本的に冪等操作（DELETE→INSERT）を基本としており、部分失敗時に既存データを不必要に消去しない設計。

- フォールバック:
  - カレンダーデータがない場合は曜日ベースの簡易判定（平日=営業日）で処理を継続。
  - データ不足（MA計算の入力が不足など）がある場合は中立値（ma200_ratio=1.0 など）や None を返し、上位での扱いを明確にしている。

### Breaking Changes
- 初回リリースのため該当なし（将来のリリースでは Settings の名前や環境変数名、DB スキーマ変更等が発生する可能性があります）。

---

アップグレード / 利用開始メモ
- .env.example を参考に必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）を設定してください。
- テストや CI で .env の自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI を使う機能（score_news, score_regime）は API キーが未設定だと ValueError を送出します。api_key を関数引数で渡すことも可能です。
- DuckDB のスキーマ（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials 等）は本リリース想定のスキーマに沿って用意してください（ETL / jquants_client の保存処理と連携します）。

貢献・バグ報告は issue を通じてお願いします。