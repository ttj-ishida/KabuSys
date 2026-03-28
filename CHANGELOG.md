# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
安定版リリース履歴を日付付きで記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システムの基本コンポーネントを実装しました。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 設定管理
  - 環境変数・設定読み込みモジュール（kabusys.config）を追加。
    - プロジェクトルート（.git または pyproject.toml）から .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント処理に対応。
    - .env 読み込み時に OS 環境変数を保護する protected 機構を実装（.env.local は override=True により優先）。
    - Settings クラスを提供し、必須キーチェック（_require）、パス（duckdb/sqlite）や KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）、便宜的プロパティ（is_live, is_paper, is_dev）を実装。
- AI（自然言語処理）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols から銘柄ごとにニュース集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて一括センチメント評価。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST の UTC 変換）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄／API コール）、記事数・文字数の上限トリミング、レスポンスバリデーション、スコアの ±1.0 クリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対するエクスポネンシャルバックオフリトライ実装。失敗はログ記録の上でスキップ（フェイルセーフ）。
    - DuckDB への書き込みは部分失敗耐性を考慮し、スコア取得済みコードのみ DELETE → INSERT（個別 executemany）で置換。
    - テスト容易性のため _call_openai_api の差し替え（unittest.mock.patch）を想定。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみ使用してルックアヘッドバイアスを防止。
    - マクロニュースはニュースタイトルでキーワードフィルタを行い、OpenAI で JSON レスポンスをパース。API エラー時は macro_sentiment=0.0 にフォールバック。
    - 冪等な market_regime テーブル更新（BEGIN / DELETE / INSERT / COMMIT）を実装。
- Research（因子計算・特徴量探索）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials を用いて計算する関数群を提供（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None ハンドリング、結果は (date, code) キーの dict リストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：複数ホライズン（デフォルト [1,5,21]）に対応し、範囲チェックと効率的な SQL 取得を実装。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンのランク相関を実装。データ不足（有効レコード < 3）は None を返す。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）を提供。外部ライブラリに依存せず標準ライブラリのみで実装。
- Data（データ基盤）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar をベースに is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定 API を提供。
    - DB 未取得日には曜日ベース（週末を非営業日）でフォールバック。DB 登録がある場合は DB 値を優先する一貫したルール。
    - calendar_update_job を実装し、J-Quants API から差分取得→保存を行う（バックフィル、健全性チェック、冪等保存を考慮）。
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETL 実行結果を格納する ETLResult dataclass を追加（品質問題、エラーリスト、集計値を含む）。
    - ETL パイプラインのユーティリティ（差分取得、max date 取得、テーブル存在確認等）の内部関数を実装。
    - jquants_client / quality モジュールとの連携設計（差分取得・保存・品質チェックのためのフック想定）。
  - DuckDB 互換性と安全性のための実装注意点を導入（executemany の空リスト回避、日付型変換ヘルパ等）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Security
- 環境変数の読み込み時に OS 環境変数を保護（protected set）し、.env による上書きを制御。
- OpenAI API キーは明示的な引数または OPENAI_API_KEY 環境変数で供給する設計。キー未設定時は ValueError を明示的に発生させる。

### Notes / 実装上の主な設計判断と互換性
- 全ての機能で datetime.today()/date.today() を直接参照しない設計（関数呼び出し側が target_date を渡す方式）により、ルックアヘッドバイアスを避ける実装方針を採用。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスのパースは冗長なケース（前後余計なテキスト）にもある程度耐性を持つ。API エラーは基本フェイルセーフ（中立スコアやスキップ）で処理継続。
- テスト容易性を考慮し、AI モジュールの内部 API 呼び出し（_call_openai_api）をパッチ差し替え可能に設計。
- DuckDB のバージョン差分（executemany の空リスト扱いなど）に配慮した実装を含む。
- DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）を前提とするため、利用時は該当テーブルの準備が必要。

---

今後のリリースでは以下を検討しています：
- strategy / execution / monitoring サブパッケージの実装（実資金・模擬取引の注文ロジック、監視アラートの実装）
- より詳細な品質チェックルールと自動修復機能
- OpenAI 呼び出しのコスト最適化（トークン管理・プロンプト最適化）および別 LLM への対応オプション

もし特定ファイルや機能についてリリース注記を詳細化したい場合は、どのモジュールを優先するか指示してください。