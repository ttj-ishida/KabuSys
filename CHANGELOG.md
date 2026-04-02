# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このプロジェクトの初期リリースに関する概要は以下の通りです。

全般なルール:
- すべての変更は機能別に「Added / Changed / Fixed / Removed / Security」に分類しています。
- 日付はリリース日を示します。
- 実装の設計方針・制約（例: ルックアヘッドバイアス回避、DuckDB テーブル名、エラー時フォールバックなど）も重要な情報として明記しています。

## [Unreleased]
- 現在未リリースの変更はありません。

## [0.1.0] - 2026-04-02
初回リリース — 基本的な日本株自動売買／データ基盤・リサーチ・AI ユーティリティ群を提供。

### Added
- パッケージ基盤
  - kabusys パッケージの初期化とバージョン管理を追加 (`src/kabusys/__init__.py`、`__version__ = "0.1.0"`).

- 環境設定
  - 環境変数/設定管理モジュールを追加 (`src/kabusys/config.py`)。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）を実装し、ルートから `.env` / `.env.local` を自動読み込み。
    - 読み込み順序: OS 環境変数 > .env.local > .env（既存 OS 環境変数は保護）。
    - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env のパースでシングル/ダブルクォート、エスケープ、export 形式、インラインコメントなどに対応。
    - 設定アクセス用の Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 監視設定 / ログレベル / env 判定など）。
    - バリデーション: KABUSYS_ENV, LOG_LEVEL の許容値チェック。必須変数未設定時は ValueError を送出。
    - Path 型でのパス拡張（`expanduser()`）をサポート。

- データプラットフォーム（DuckDB ベース）
  - ETL パイプラインの結果型 ETLResult を公開 (`src/kabusys/data/etl.py`, `pipeline.py`)。
    - ETL のフェイルセーフ設計、バックフィル、品質チェックの枠組みを提供。
  - ETL 実装の主要ユーティリティ（差分取得、最大日付取得、テーブル存在チェック、ETLResult データクラス）を追加 (`src/kabusys/data/pipeline.py`)。
  - マーケットカレンダー管理モジュールを追加 (`src/kabusys/data/calendar_management.py`)。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - DB 登録値優先、未登録日の曜日ベースフォールバック、最大探索日数制限、バックフィル、健全性チェックをサポート。
    - 夜間バッチジョブ `calendar_update_job`：J-Quants から差分取得して market_calendar テーブルへ冪等保存。

- リサーチ（ファクター計算・特徴量探索）
  - 主要ファクター計算モジュールを追加 (`src/kabusys/research/factor_research.py`)。
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER, ROE）等の計算関数を提供。
    - DuckDB に対する SQL ベース実装。データ不足時は None を返す設計。
  - 特徴量探索ユーティリティを追加 (`src/kabusys/research/feature_exploration.py`)。
    - 将来リターン計算 (calc_forward_returns)、IC（Information Coefficient）計算(calc_ic)、ランク化(rank)、統計サマリー(factor_summary) を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージの再エクスポートを追加 (`src/kabusys/research/__init__.py`)。

- AI / NLP
  - ニュース NLP スコアリングモジュールを追加 (`src/kabusys/ai/news_nlp.py`)。
    - raw_news + news_symbols を集約し、銘柄ごとにニュースを統合して OpenAI（gpt-4o-mini）へ送信しセンチメント（-1.0〜1.0）を得る。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの最大記事数・文字数トリムをサポート。
    - JSON Mode のレスポンスを期待、レスポンスバリデーションとスコアクリップ（±1.0）を実装。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで行い、致命的失敗はスキップして継続するフェイルセーフ挙動。
    - DuckDB への書き込みは部分置換（該当コードのみ DELETE → INSERT）で保護的に実行。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（unittest.mock.patch を想定）。
  - 市場レジーム判定モジュールを追加 (`src/kabusys/ai/regime_detector.py`)。
    - ETF 1321（日経225連動）200日 MA 乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して 1 日単位でレジーム（bull/neutral/bear）を算出。
    - prices_daily からのデータ取得は target_date 未満のみを参照し、ルックアヘッドバイアスを回避。
    - マクロニュースは news_nlp 側の窓関数 calc_news_window を利用して抽出、OpenAI による JSON レスポンスをパース。
    - API 失敗時やパース失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - 結果は market_regime テーブルへトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等書き込み。

- ユーティリティ / エクスポート
  - data/etl: ETLResult を公開。
  - ai/__init__.py, research/__init__.py による主要 API の再エクスポート。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- OpenAI API キーや各種機密値は Settings 経由で環境変数から取得し、.env 自動ロードの上書き保護（OS 環境変数保護）を実施。
- 自動ロードは環境変数で無効化可能（テスト時等）。

### Notes / Constraints / Design decisions（重要）
- DuckDB 前提: 多くの処理は DuckDB 接続（DuckDBPyConnection）と特定テーブル（例: prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials, market_regime）を前提としています。テーブルスキーマは実装側で想定された形で存在する必要があります。
- ルックアヘッドバイアス対策: AI 関数およびリサーチ関数は内部で datetime.today()/date.today() を参照せず、外部から target_date を受け取る設計です。
- フェイルセーフ: OpenAI 呼び出しの失敗やパースエラーは基本的に例外を上位へ投げず、0.0 やスキップで継続する挙動が多く採用されています（ログは出力）。
- トランザクションと冪等性: DB への書き込みは多くの場合 BEGIN/DELETE/INSERT/COMMIT のパターンで冪等に実装。部分書き込みにより他データの保護を行っています。
- OpenAI 依存: gpt-4o-mini と JSON mode を想定。レスポンスの厳密な JSON 出力を期待しているため、モデル/設定変更時はレスポンス処理の調整が必要です。
- テスト支援: OpenAI 呼び出し用の内部関数は差し替え（モック）しやすく実装されています（_call_openai_api のパッチなど）。
- .env パーサ: export 形式やクォート内のエスケープ、インラインコメント等を考慮したパーサを実装。特殊ケースのパース挙動は実運用での検証を推奨します。

---

今後のリリース案（例）
- 機能追加: PBR・配当利回りの計算、ETL のより詳細な品質レポート、Slack 連携による監視通知、kabu ステーションとの発注モジュール。
- 改善: OpenAI レスポンスのより堅牢な正規化、高頻度バッチ処理の最適化、DuckDB のバージョン互換性対応、ユニット/統合テストの充実。

（この CHANGELOG はコードベースから推測して作成しています。実際の変更履歴やリリースノート作成時はコミット履歴や PR の説明を併せて記載してください。）