# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買/データ基盤向けのコアライブラリ群を提供します。

### Added
- パッケージ初期化
  - kabusys パッケージを公開（src/kabusys/__init__.py）。公開サブパッケージ: data, research, ai, execution, strategy, monitoring 等を想定。
  - バージョン: 0.1.0

- 環境設定ユーティリティ（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - export KEY=val 形式、クォート、インラインコメント等に対応した .env パーサ実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
  - Settings クラスを提供（settings インスタンスをエクスポート）。J-Quants、kabu API、Slack、DB パス、環境フラグ（development/paper_trading/live）、ログレベル等の設定取得用プロパティを実装。
  - 必須変数未設定時は ValueError を送出する _require 実装。

- AI 関連（src/kabusys/ai）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄毎の ai_score を算出し ai_scores テーブルへ書き込む。
    - チャンク処理（最大 20 銘柄/コール）、トークン肥大対策（記事数上限・文字数上限）を実装。
    - JSON Mode を想定したレスポンスバリデーション、スコアの ±1.0 クリップ。
    - リトライ（429・ネットワーク・5xx）を指数バックオフで行い、失敗はログに記録してスキップ（フェイルセーフ）。
    - calc_news_window(target_date) と score_news(conn, target_date, api_key=None) を公開。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次でレジーム（bull/neutral/bear）を出力。
    - OpenAI（gpt-4o-mini）へ JSON 出力を要求、API 呼び出しはリトライ・フェイルセーフ実装（失敗時 macro_sentiment=0.0）。
    - DuckDB の prices_daily / raw_news / market_regime を参照し、冪等な DB 書き込みを実施。
    - 公開 API: score_regime(conn, target_date, api_key=None)

- Data モジュール（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを元に営業日判定、前後営業日取得、期間内営業日取得、SQ 日判定等のユーティリティを提供。
    - DB にデータがない場合は曜日ベース（土日を非営業日）でのフォールバックを行う。
    - calendar_update_job(conn, lookahead_days=90) により J-Quants から差分取得し DB 更新（バックフィル・健全性チェックあり）。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - 差分取得→保存→品質チェックのワークフロー設計に対応。
    - ETLResult データクラスを定義し etl モジュールから再エクスポート（ETL 結果の集約・シリアライズ機能）。
    - DB 最終取得日判定、テーブル存在チェック、最大日付取得等のユーティリティを実装。
  - その他: data パッケージの公開インターフェースを準備。

- Research モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials と prices_daily を用いて PER、ROE を計算。
    - DuckDB の SQL を利用した実装で、外部 API 呼び出しは行わない。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズンの将来リターン計算（デフォルト [1,5,21]）。
    - calc_ic: スピアマンランク相関（IC）計算（code での結合・欠損排除・最小サンプルチェック）。
    - rank: 同順位は平均ランクを採るランク付けユーティリティ。
    - factor_summary: count/mean/std/min/max/median の統計サマリー。

- 実装上の設計方針・安全機構（ドキュメント化）
  - すべての「日付基準」関数は datetime.today() / date.today() を直接参照せず、呼び出し元が target_date を渡す設計（ルックアヘッドバイアス防止）。
  - OpenAI 呼び出しは JSON mode を前提とし、パース/バリデーションとフェイルセーフ（失敗時はデフォルト値やスキップ）を実装。
  - DuckDB を主要な永続化手段として使用。INSERT 前の DELETE / executemany を用いた冪等処理を採用（部分失敗で既存データを保護）。
  - 環境変数自動読み込み時、OS 環境変数は保護（.env による上書きを制御）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- .env 自動読み込み時に OS 環境変数を保護する仕組みを実装（.env による既存キー上書きを防止する protected set）。
- OpenAI API キーは明示的に引数で注入可能。未設定時は明示的なエラーを発生させる（誤動作を防止）。

### Notes / Known behavior
- OpenAI モデルは gpt-4o-mini を想定。レスポンスは厳密な JSON を期待するが、パース失敗時は復元処理やフォールバックを試みる。
- DuckDB の executemany で空リストを渡すと問題になる点を考慮して空チェックを入れている（互換性配慮）。
- .env パーサはシェル風のコメント・クォート・エスケープを考慮しているが、極端に複雑な .env 構成は想定外の動作をする可能性あり。
- calendar_update_job は J-Quants クライアント（jquants_client）に依存。API エラー時は 0 を返して安全に終了する。

--- 

開発・運用上の詳細や public API の使用例は各モジュールの docstring を参照してください。