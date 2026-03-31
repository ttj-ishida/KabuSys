CHANGELOG
=========

すべての注目すべき変更をここに記載します。フォーマットは「Keep a Changelog」に準拠しています。

リリース方針:
- バージョン 0.1.0 はライブラリの初回公開相当の機能セットをまとめたリリースです。
- 各関数は可能な限りルックアヘッドバイアスを避ける設計（date.today() / datetime.today() を直接参照しない等）となっています。

[Unreleased]
------------

- 現在なし。

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ化の初期公開
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を追加。
  - パッケージトップで主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード:
    - プロジェクトルートを .git または pyproject.toml から探索して判定（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応（テスト向け）。
  - .env パーサーの強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - インラインコメント判定（クォートなしでは '#' の直前が空白/タブの場合をコメントと判定）。
  - オーバーライド制御と protected キー:
    - _load_env_file に override フラグと protected キー集合を導入し、OS環境変数の上書きを防止。
  - 設定項目:
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB / SQLite）/監視閾値（CPU/MEM/DISK）/PID ファイルパス 等をプロパティとして提供。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）を実施。
    - 必須変数未設定時は ValueError を送出する _require() を提供。

- AI（LLM）機能
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode でセンチメント評価を行い ai_scores テーブルへ書き込む機能を実装。
    - ウィンドウ定義（JST 前日15:00 ～ 当日08:30 を UTC に変換）と記事トリミング（最大記事数・最大文字数）を実装。
    - バッチ処理（最大 20 銘柄/リクエスト）とリトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）を実装。
    - OpenAI レスポンスの堅牢なバリデーション（JSON パース、results リスト・code/score 型チェック、スコアの有限性検査、±1.0 のクリップ）。
    - DuckDB の executemany 空リスト制約に配慮した DELETE/INSERT の実装（部分失敗時に既存スコアを保護）。
    - score_news 関数を公開（kabusys.ai.__all__ に score_news を登録）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする機能を実装。
    - マクロニュース抽出のためのキーワードリストを実装（日本・米国・グローバル要因）。
    - OpenAI 呼び出しは独立実装とし、API エラー時はマクロセンチメントを 0.0 にフォールバック（例外を上げず継続）。
    - LLM 呼び出しは最大リトライ、指数バックオフ、5xx の扱いを厳密に管理。
    - score_regime 関数を公開。

- データ基盤（Data）
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを追加し、ETL 実行結果（取得数、保存数、品質問題、エラー概要）を構造化して保持・辞書化する機能を提供。
    - 差分更新、バックフィル、品質チェックの設計方針に基づくユーティリティが整備されている（J-Quants クライアント連携前提）。
    - kabusys.data.etl で ETLResult を再エクスポート。

  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを用いた営業日判定ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録がない日については曜日ベースのフォールバック（平日は営業日、土日非営業）。
    - calendar_update_job を実装し J-Quants からの差分取得・冪等保存（バックフィル・健全性チェック含む）を行う。

- リサーチ機能 (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム（1M/3M/6M リターン・200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER/ROE）を DuckDB 上で計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - データ不足時の挙動（必要行数未満なら None）を定義。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算（calc_forward_returns）と IC（calc_ic）計算、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等外部依存せず標準ライブラリと DuckDB のみで実装。

- モジュール公開の整理
  - 各サブパッケージの __init__.py で公開 API を明示（ai, research, data 等）。

Changed
- 設計方針として全てのスコアリング/判定関数でルックアヘッドバイアス防止（外部時刻の直接参照を行わない）を明確化。
- DuckDB の互換性（executemany の空リスト不可など）に合わせた実装を適用。

Fixed / Robustness improvements
- OpenAI API 呼び出し関連の堅牢化:
  - 429・接続断・タイムアウト・5xx に対するリトライと指数バックオフを統一的に実装。
  - API の 5xx と非5xx を区別してリトライ可否を判断。
  - レスポンスパース失敗時は警告ログを出しフェイルセーフでスコアを 0.0（或いは処理スキップ）にする実装。
  - JSON mode でも前後に余計なテキストが混入するケースに備え、最外の {} を抽出してパースする復元ロジックを追加。
- DB 書き込みの冪等性確保:
  - market_regime と ai_scores への書き込みで BEGIN/DELETE/INSERT/COMMIT のパターンを使い、例外時は ROLLBACK を試行。
  - ai_scores については部分書き込みで既存データを保護する戦略を採用。
- ニュース集約とトリミング:
  - 1 銘柄あたりの最大記事件数・最大文字数を設定してトークン肥大化を防止。

Security
- 環境変数読み込み時に OS 環境変数を protected として自動上書きを防止する仕組みを導入。
- OpenAI API キーが未設定の場合、明確な ValueError を発生させて誤った挙動を防止。

Notes / Known constraints
- OpenAI の利用は gpt-4o-mini を想定しており、JSON Mode を前提としたパース処理を行っています。モデル仕様変更があった場合はパース・エラーハンドリングを見直してください。
- DuckDB のバージョン差異（特に executemany の挙動やリスト型バインド）に配慮した実装を行っていますが、環境によっては微調整が必要になる場合があります。
- 多くの関数は外部 API（J-Quants / OpenAI / kabu ステーション等）に依存するため、ユニットテストでは該当部分をモック（_call_openai_api 等）することを想定しています。

Breaking Changes
- リリース初版のため後方互換性の変更履歴はありません。ただし、いくつかの関数（score_news, score_regime 等）は OpenAI API キー未設定時に ValueError を送出するように設計されています。呼び出し側は api_key 引数または環境変数 OPENAI_API_KEY の設定を必須としてください。

Contributing
- このリポジトリはテスト容易性を意識しており、OpenAI 呼び出し等をモックできるよう内部呼び出しを分離しています。機能追加や修正を行う際は、ルックアヘッドバイアスと冪等性（DB 書き込み）に注意してください。