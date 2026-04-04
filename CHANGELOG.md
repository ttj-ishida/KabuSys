# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記録されています。  
このファイルはコードベース（初期バージョン v0.1.0）から推測して作成しています。

全般的な記載方針:
- 日付はこのCHANGELOG作成日（2026-04-04）を使用しています。
- 記載はソースコードの公開 API、設計方針、既知の動作（フォールバックやフェイルセーフ）を中心にまとめています。

## [Unreleased]

## [0.1.0] - 2026-04-04
初回リリース。本リポジトリは日本株の自動売買／リサーチ基盤を構成する複数モジュールを提供します。主な追加点を以下に列挙します。

### Added
- パッケージ基盤
  - kabusys パッケージ基本設定（src/kabusys/__init__.py、バージョン v0.1.0）。
  - パッケージ公開 API に data, strategy, execution, monitoring を含める。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env/.env.local の自動ロード機構を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - ロード優先順位: OS 環境変数 > .env.local > .env。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
  - .env ファイルの柔軟なパーサ（export プレフィックス、シングル/ダブルクォート内のエスケープ、行内コメントの扱いなど）。
  - Settings クラスによる型付きアクセス（duckdb/sqlite ファイルパス、Kabu API/LINE トークン、監視閾値など）。
  - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値チェック）。
  - 必須環境変数未設定時に ValueError を送出する _require 関数（J-Quants / Kabu API など）。

- AI（自然言語処理）モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信して銘柄ごとのセンチメント（ai_score）を生成。
    - タイムウィンドウ計算（JST 基準：前日 15:00 ～ 当日 08:30）を calc_news_window 関数で提供。
    - バッチサイズ、記事数上限、文字数上限を制御（トークン肥大化対策）。
    - API 呼び出しはリトライ（429/ネットワーク/タイムアウト/5xx）を伴うエクスポネンシャルバックオフで実行。失敗した銘柄はスキップして継続するフェイルセーフ設計。
    - レスポンスの厳密なバリデーションとスコア ±1.0 のクリップ。部分成功時は該当銘柄のみ ai_scores テーブルを置換（DELETE → INSERT）して既存データを保護。
    - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock.patch）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）を用いた 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - レジーム合成ロジック（スケーリング、クリップ、閾値）と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - OpenAI 呼び出しはリトライ／ステータスによる分岐を実装し、API 失敗時は macro_sentiment=0.0 にフォールバックして継続。
    - ルックアヘッドバイアス回避のため datetime.today()/date.today() を参照せず、prices_daily クエリは target_date 未満のデータのみを利用。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar）を扱うユーティリティを提供：is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - market_calendar が未登録の場合は曜日（土日）ベースのフォールバックを使用。DB 登録値は優先。
    - 夜間バッチ更新 job (calendar_update_job) を実装（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索日数やバックフィル日数などの安全策を導入。

  - ETL パイプライン基盤（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを導入（ETL 実行結果の集約、品質問題・エラー一覧の保持、辞書変換メソッド）。
    - 差分更新・バックフィル・品質チェックを想定した設計（J-Quants クライアント経由で idempotent に保存）。
    - _table_exists / _get_max_date 等の内部ユーティリティを実装。
    - etl モジュールで ETLResult を再エクスポート。

- リサーチ機能（src/kabusys/research）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR）、Liquidity（20 日平均売買代金、出来高比率）、Value（PER、ROE）などのファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL ベースの処理。過去データ不足時には None を返す設計。
    - 設計方針として本番の発注 API には接続せず、prices_daily / raw_financials のみを参照。

  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns、horizons バリデーション、1 クエリ実行による取得）、IC（Information Coefficient）計算（Spearman の ρ をランク換算で実装）、統計サマリー（factor_summary）を提供。
    - ランク変換関数 rank を実装（同順位は平均ランク、丸めによる ties 対策）。
    - pandas 等の外部ライブラリに依存しない純 Python + DuckDB 実装。

- テスト性／運用を考慮した実装
  - OpenAI 呼び出し部分はモック差し替えポイントを明確にしている（各モジュールの _call_openai_api）。
  - DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 想定箇所あり）。
  - フェイルセーフ原則を採用（API 失敗で例外を投げずスキップまたはデフォルト値で継続する箇所が多い）。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Removed
- （初回リリースにつき該当なし）

### Security
- 環境変数・API キーはコード内で直接ハードコーディングせず、Settings 経由で取得。OpenAI API キー未設定時は明示的に ValueError を発生させる挙動を導入。

### Notes / Known behaviors
- OpenAI API は gpt-4o-mini を想定し JSON mode を利用するプロンプト設計となっている。レスポンス形式が想定と異なる場合はログを出してスキップする設計。
- DuckDB 固有の制約（executemany に空リストが渡せない等）を考慮した実装が複数存在する（ai/news_nlp.py の DELETE/INSERT ロジック等）。
- 時刻の扱いは明示的に UTC naive / JST 変換を意識しており、ルックアヘッドバイアスを避けるため date/datetime の参照手法に注意している（関数は target_date を引数に取り現在時刻を参照しない）。
- プロジェクトルート探索は __file__ を基準にするため、CWD に依存しない挙動となる。パッケージ配布後の実行でも .env 自動ロードが期待通り動作するよう設計されている。
- ロギングや warnings により問題検出時の診断が可能。DB 書き込み失敗時は ROLLBACK を試行し、失敗時は警告ログを出力する仕組み。

もし追加の詳細（例: 各関数の引数や返り値の具体例、想定テーブルスキーマ、リリース日を変更したい等）が必要であれば指示してください。