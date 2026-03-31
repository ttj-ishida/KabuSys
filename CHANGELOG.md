# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティック バージョニングを採用します。

現在の日付: 2026-03-31

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-31

### Added
- パッケージ初期リリース。kabusys のコア機能群を追加。
  - パッケージメタ情報
    - バージョン: 0.1.0（src/kabusys/__init__.py）
    - パブリック API: data, strategy, execution, monitoring を __all__ で公開（将来的なサブパッケージ構成を想定）。
- 設定管理モジュール（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を実装。
  - export KEY=val 形式、クォート処理、インラインコメント処理など、.env の柔軟なパースロジックを実装。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスで各種設定をプロパティとして提供（J-Quants / kabu API / Slack / DB パス / 監視しきい値 / 環境種別・ログレベル検証等）。
  - 環境値検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）と必須環境変数取得時の明示的エラーを追加。
- AI モジュール（src/kabusys/ai/*）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントを算出。
    - タイムウィンドウ算出（前日 15:00 JST ～ 当日 08:30 JST 相当の UTC ウィンドウ）を提供する calc_news_window を実装。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの最大記事数・文字数制限、レスポンスの厳密バリデーション、スコアの ±1.0 クリップ、部分書き込み（成功したコードのみ INSERT）によるフェイルセーフ実装。
    - API 呼び出しはリトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を備える。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を算出して market_regime テーブルへ冪等書き込み。
    - マクロキーワード抽出、OpenAI 呼び出し（gpt-4o-mini）とレスポンスパース、リトライとフェイルセーフ（API 失敗時に macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス回避のため datetime.today() を参照しない設計。
  - ai.__init__ で score_news を公開。
- データプラットフォーム（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar）を参照し営業日判定・前後営業日の算出・期間内営業日の取得・SQ日判定を提供。
    - DB 未取得時は曜日ベース（土日除外）でフォールバックする堅牢なロジック。
    - calendar_update_job により J-Quants からの差分取得・バックフィル・健全性チェック・冪等保存を実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py と etl.py）
    - 差分取得 → 保存（jquants_client 経由の idempotent 保存）→ 品質チェック（quality モジュール）という ETL フローの基礎を実装。
    - ETLResult dataclass を追加（取得数・保存数・品質問題・エラーの集約、has_errors / has_quality_errors / to_dict を提供）。
    - パイプライン内部ユーティリティ（テーブル存在確認、最大日付取得など）を実装。
  - data パッケージで ETLResult を再エクスポート（src/kabusys/data/etl.py）。
- リサーチ（src/kabusys/research/*）
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高変化率）、バリュー（PER、ROE）ファクター計算を実装。
    - DuckDB 上の SQL ウィンドウ関数を活用して効率的な計算を行う。データ不足時の None ハンドリング。
  - feature_exploration.py
    - 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、rank（同順位は平均ランク）、factor_summary（基本統計量）を実装。
    - pandas 等の外部依存を使わず標準ライブラリ／DuckDB で実装。
  - research パッケージの __init__ で主要関数群を公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
- エラーハンドリング・設計方針
  - 多くのモジュールで「ルックアヘッドバイアスを防ぐため datetime.today()/date.today() を参照しない」方針を採用。
  - OpenAI 呼び出しは堅牢なリトライ・フェイルセーフ実装（API 失敗時に処理継続またはスコアを中立化）を採用。
  - DuckDB の executemany の制約（空リスト不可）等、実行時の互換性問題に配慮した実装。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- 環境変数の必須チェック（OpenAI API キー / Slack / KabuAPI パスワード等）により、設定漏れを早期に検出。

### Notes / Implementation details
- OpenAI の呼び出しは OpenAI SDK の chat.completions.create を使用し、JSON mode（response_format={"type":"json_object"}）で厳密 JSON を期待する実装。ただしレスポンスパース時に余分な文字列が混入するケースも考慮してフォールバックパースを実装。
- DuckDB を前提とした SQL を多用しており、SQL 側で可能な集計・ウィンドウ関数を活用している。
- jquants_client、quality モジュールは data パッケージから呼び出す想定（実装ファイルは本差分に含まれないがインターフェースを前提とした設計）。
- 一部モジュールではテスト容易性を考慮して API 呼び出し部分を差し替え可能（例: unittest.mock.patch による _call_openai_api 差し替え想定）。

---

このリリースは「プロジェクトの実装骨格」として、データ取り込み（ETL / calendar）、解析（research）、AI ベースのニュース・レジーム判定、環境設定管理の主要機能を含みます。今後のリリースでは strategy / execution / monitoring の具体的な実装、単体テストや CI、ドキュメント追記、パフォーマンス改善や追加セキュリティ対策などを予定しています。