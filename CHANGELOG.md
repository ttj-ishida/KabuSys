# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース（初期実装）。日本株自動売買プラットフォームのコアコンポーネント群を実装・公開しました。

### Added
- パッケージ基盤
  - pkg: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）
  - __all__ に "data", "strategy", "execution", "monitoring" を公開

- 設定・環境変数管理
  - 環境変数自動読み込み機能（.env / .env.local）をプロジェクトルート（.git または pyproject.toml）検出で行う実装を追加（src/kabusys/config.py）
  - .env パーサの実装（クォート、エスケープ、export プレフィックス、インラインコメント処理等に対応）
  - 自動ロード優先度: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用）
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定（env, log_level, is_live 等）を環境変数から取得・検証
  - 必須変数未設定時は明確な例外（ValueError）を発生

- AI（NLP）モジュール
  - ニュースセンチメント集計: score_news を実装（src/kabusys/ai/news_nlp.py）
    - ニュース収集ウィンドウ（JST基準）計算（calc_news_window）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）に JSON mode で送信してセンチメントを取得
    - バッチ処理（最大20銘柄/呼び出し）、記事トリム（最大記事数・最大文字数）を実装
    - リトライ戦略（429・ネットワーク・タイムアウト・5xx に対する指数バックオフ）
    - レスポンス検証とスコアクリッピング（±1.0）
    - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に既存データを保護）
    - テストしやすい設計（_call_openai_api を patch 可能、api_key を引数で注入可能）
  - 市場レジーム判定: score_regime を実装（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロ ニュース由来の LLM センチメント（重み30%）を合成して日次レジーム判定（bull/neutral/bear）
    - DuckDB から prices_daily / raw_news を参照、ma200_ratio 計算、マクロニュース抽出（キーワードベース）、OpenAI 呼び出し（gpt-4o-mini）でマクロセンチメント算出
    - API エラー時はマクロセンチメントを 0.0 とするフェイルセーフ、リトライ実装
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装
  - AI パッケージ公開: score_news を __all__ で公開（src/kabusys/ai/__init__.py）

- データ基盤（DuckDB ベース）
  - ETL パイプラインのインターフェース（ETLResult dataclass を公開）（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETL の結果を構造化して返すクラス（ログ・監査に利用）
    - ETLResult は品質問題・エラーの集計や has_errors / has_quality_errors を提供
  - マーケットカレンダー管理（calendar_management モジュール）を実装（src/kabusys/data/calendar_management.py）
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供
    - DB 値優先、未登録日は曜日ベースでフォールバックする一貫した判定ロジック
    - calendar_update_job: J-Quants からの差分取得→保存（バックフィル・健全性チェック付き）
  - DuckDB の存在チェック等のユーティリティを整備（内部関数）

- リサーチ／ファクター処理
  - research パッケージを追加（src/kabusys/research/）
  - ファクター計算（factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、平均売買代金、出来高比率を計算
    - calc_value: raw_financials を用いた PER / ROE の計算
    - DuckDB を用いた SQL ベースの実装、データ不足時は None を返す設計
  - 特徴量探索（feature_exploration.py）
    - calc_forward_returns: 各ホライズン（デフォルト [1,5,21]）で将来リターンを計算（LEAD を利用）
    - calc_ic: スピアマンのランク相関（IC）を実装（欠損や同順位を考慮）
    - rank: 同順位は平均ランク（丸め対策あり）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出
  - research パッケージの主要関数を __all__ で公開（zscore_normalize は別モジュールから再利用）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーや各種トークンは環境変数から取得する設計（明示的に必須の変数は ValueError を返す）
- .env 自動ロードはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テスト時の安全措置）

### Notes / Implementation Decisions（設計上の注記）
- ルックアヘッドバイアス防止:
  - date.today()/datetime.today() を直接参照せず、関数引数の target_date を基準とする設計を徹底（AI スコアリングやファクター計算等）
  - DB クエリでは target_date 未満／排他条件などで未来データ利用を防止
- OpenAI 呼び出し:
  - gpt-4o-mini を想定し JSON Mode（response_format）を利用
  - リトライは 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフ
  - レスポンスパース失敗や API 諸問題は例外を投げずフェイルセーフ（スコアを 0.0 にフォールバック、あるいは該当銘柄をスキップ）
  - テスト性を考慮し _call_openai_api を patch して差し替え可能
- DuckDB 書き込み:
  - 冪等性を保つため DELETE→INSERT のパターンを採用
  - DuckDB の executemany の制限への対応（空リスト回避）
- テスト容易性:
  - API キーを関数引数で注入可能（環境変数に依存しない単体テストが可能）
  - 内部 API 呼び出し箇所（_call_openai_api 等）をモック可能

---

もしリリースノートに追記してほしい項目（例えば個別 API の使用例、既知の制限、将来のロードマップなど）があれば教えてください。必要に応じてセクションを追加して更新します。