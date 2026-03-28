# Changelog

すべての注記は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このファイルはコードベース（kabusys パッケージ）の現状から機能・設計意図を推測して作成した変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買プラットフォームのコアライブラリを実装。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。モジュール公開: data, strategy, execution, monitoring。
- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env/.env.local の読み込み優先度に対応。OS 環境変数の保護（protected set）をサポート。
  - 行パーサはコメント・クォート・export 形式に対応。
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 必須環境変数未設定時に ValueError を投げる _require 関数と Settings クラスを提供。
  - 設定項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, DUCKDB_PATH, KABUSYS_ENV, LOG_LEVEL など）をプロパティとして公開。env 値検証（有効な環境値・ログレベル）を実装。
- AI（自然言語処理・レジーム判定）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して、銘柄ごとのニュースをまとめ、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 20 銘柄 / コール）・1 銘柄当たりの最大記事数/文字数トリム・JSON Mode レスポンスバリデーションを実装。
    - 再試行（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフを実装。失敗時はフォールバック（スキップ・空辞書）して処理継続するフェイルセーフ方針。
    - レスポンス検証で不正なレスポンスはログ警告して無視。スコアは ±1.0 にクリップ。
    - DuckDB への書き込みは冪等的（DELETE → INSERT）で、部分失敗時に既存スコアを保護する実装。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（_call_openai_api をパッチ可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出して market_regime テーブルへ冪等書き込み。
    - マクロキーワードによる raw_news フィルタリング、最大取得件数、OpenAI 呼び出しのリトライ・エラーハンドリングを実装。API 失敗時は macro_sentiment=0.0 として継続するフェイルセーフ。
    - ルックアヘッドバイアス回避のため target_date 未満のみを参照するクエリ設計。
- データ基盤（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得・backfill ロジック、品質チェックフック（quality モジュール連携）を想定した ETLResult データクラスを追加。
    - DuckDB の最大日付取得やテーブル存在確認などのユーティリティを提供。
    - ETL 操作中に検出した品質問題を収集して呼び出し元が判断できる設計（Fail-Fast ではなく全件収集）。
  - ETL 公開インターフェース（kabusys.data.etl）で ETLResult を再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを前提に営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバックする堅牢な挙動。
    - calendar_update_job により J-Quants API から差分取得 → 保存（冪等）・バックフィル・健全性チェックを実施。
    - 最大探索日数制限で無限ループを回避。
- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR、相対 ATR、平均売買代金・出来高比率）、Value（PER、ROE）を実装。
    - DuckDB の SQL ウィンドウ関数を活用して効率的に計算。データ不足時は None を返す設計。
    - 外部 API にアクセスしない（安全性）。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（スピアマンの順位相関）計算、ランク変換、統計サマリーを実装。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで完結する実装。
- ロギングと設計方針
  - 各モジュールで詳細なログ出力（info/warning/debug）を実装し、異常系はログで通知。
  - ルックアヘッドバイアスを避けるため datetime.today()/date.today() を利用しない関数群（target_date を引数に取る設計）。
  - DuckDB を中心としたデータ操作設計（冪等性を重視した DELETE→INSERT パターン、executemany の空リスト回避等の互換性考慮）。
  - OpenAI 呼び出し関連はモデル名（gpt-4o-mini）と JSON Mode を利用し、エラーハンドリングと再試行戦略を実装。

### Security
- 環境変数読み込みで OS 環境変数を上書きしないデフォルト挙動を採用。明示的に .env.local で上書き可能。
- 必須キーが未設定の場合は明示的な例外を出すことで誤設定を早期検出。

### Notes / Implementation details
- OpenAI クライアントは openai.OpenAI を直接利用（api_key を注入して生成）。テストのために _call_openai_api をモック可能。
- DuckDB に対する SQL 文はモジュール内で直接組み立てられている（注：SQL 注入は内部用途のため想定外だがパラメータバインドを利用）。
- 日付・時間は基本的に date / naive datetime（UTC 換算）で統一し、タイムゾーン混入を避ける設計。

### Breaking Changes
- 初回リリースのためなし。

### Fixed
- 初回リリースのためなし。

---

今後の更新候補（推測）
- strategy / execution / monitoring モジュールの実装（注文発注ロジック・監視パイプライン・Slack 通知など）。
- テストカバレッジ追加、CI ワークフロー、パッケージ配布設定の整備。
- パフォーマンス最適化（大規模データ向けのバッチ処理改善）、OpenAI レスポンスのより堅牢な検証ロジック強化。