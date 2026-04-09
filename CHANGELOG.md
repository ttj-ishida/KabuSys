# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従います。  
このファイルはコードベースから推測して作成した初期リリースの変更履歴です。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-09

### Added
- パッケージ基盤
  - パッケージルートを定義（src/kabusys/__init__.py）。バージョンは `0.1.0`。
  - public API のモジュール一覧を `__all__` に定義（data, strategy, execution, monitoring）。

- 環境設定 / 設定読み込み（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。
    - 読み込み順: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に探索（CWD 非依存）。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、インラインコメントの扱い等）。
  - .env 上書き時に OS 環境変数を保護する仕組み（protected set）を追加。
  - Settings クラスを提供。主要プロパティ:
    - J-Quants / kabu API 関連: JQUANTS_REFRESH_TOKEN（必須）, KABU_API_PASSWORD（必須）, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - LINE 通知: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - データベースパス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - Paper trading: PAPER_FILL_MODE（instant/partial/never/reject のバリデーション）, PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
    - 監視関連: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEMORY/DISK 閾値
    - システム: KABUSYS_ENV（development/paper_trading/live のバリデーション）, LOG_LEVEL（DEBUG/INFO/... のバリデーション）, is_live/is_paper/is_dev ヘルパー
  - 必須環境変数未設定時は明確な ValueError を発生させる `_require` 実装。

- AI モジュール（src/kabusys/ai/*.py）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、銘柄ごとのニュースをまとめて OpenAI（gpt-4o-mini）にバッチ送信してセンチメントを算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算するユーティリティ `calc_news_window`。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたりの記事数・文字数制限（上限: 記事数 10、文字数 3000）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ付きリトライ。その他エラーはスキップして継続（フェイルセーフ）。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。
    - 書き込みは部分失敗を避けるため、取得成功したコードのみ DELETE → INSERT で置換（冪等性確保）。DuckDB の executemany の制約に配慮した実装。
    - テスト用に OpenAI 呼び出し (_call_openai_api) をパッチ差し替え可能（unittest.mock.patch を想定）。
    - 成功時に書き込んだ銘柄数を返す API `score_news` を公開。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離とニュース由来のマクロセンチメントを合成して日次で 'bull'/'neutral'/'bear' を判定する `score_regime` を実装。
    - ma200_ratio の計算（ルックアヘッド防止のため target_date 未満のみ使用、データ不足時は中立 1.0 を返す）。
    - マクロキーワードで raw_news をフィルタし、最大 20 件のタイトルを LLM に投げて macro_sentiment を得る。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - スコア合成は重み付け (MA 70%, Macro 30%)、クリップ、閾値判定（bull / bear 判定閾値）。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理。
    - OpenAI 呼び出しのリトライ・例外処理を備える。テスト用に _call_openai_api を差し替え可能。

- データ処理 / ETL（src/kabusys/data/*.py）
  - ETL 結果のデータクラス `ETLResult`（src/kabusys/data/pipeline.py）を公開（src/kabusys/data/etl.py で再エクスポート）。
    - 取得/保存件数、品質チェック結果、エラー一覧を保持。`has_errors` / `has_quality_errors` / `to_dict` を提供。
  - 市場カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定ユーティリティ：is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB にデータがない、または一部しかない場合の曜日ベースフォールバック（週末を休日扱い）に対応。
    - 夜間バッチ更新 job `calendar_update_job` を実装。J-Quants クライアント経由で差分取得・バックフィル・保存（jq.fetch_market_calendar / jq.save_market_calendar の呼び出し）を行う。
    - サニティチェック（未来日に関する異常検知）、最大探索日数制限で無限ループを防止。

- リサーチ / ファクター計算（src/kabusys/research/*.py）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M）、200日 MA 乖離、ATR ベースのボラティリティ、出来高/売買代金流動性指標、財務指標（PER, ROE）を DuckDB クエリで計算する関数群を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 返却、パフォーマンスを考慮したスキャン範囲、DuckDB ウィンドウ関数利用。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）のリターン計算。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関（順位の同順位は平均ランク処理）。
    - factor_summary：各ファクター列の count/mean/std/min/max/median を計算。
    - rank ユーティリティ：同順位の平均ランク付与かつ丸めで ties の判定漏れを防止。
  - research パッケージの public API を `__all__` でエクスポート。

### Design / Behavior notes
- ルックアヘッドバイアス対策
  - AI スコア・レジーム判定・ETL・ファクター計算の各所で datetime.today() / date.today() を直接参照しない設計。すべて target_date を明示的に渡すことで、過去データだけに基づく再現性のある計算を保証。
- 冪等性 / 部分失敗対策
  - DB 書き込みは可能な限り冪等（DELETE→INSERT や ON CONFLICT 相当）にして、部分失敗で既存データを不用意に消さない工夫を実装。
  - 例外発生時の COMMIT/ROLLBACK を明確に扱い、ROLLBACK の失敗もログに記録。
- フェイルセーフ
  - 外部 API（OpenAI / J-Quants）失敗時は可能な範囲で処理を継続（マクロセンチメント 0.0、スコア取得失敗はスキップ等）し、致命的な例外を最小化。
- テスト親和性
  - AI モジュールの OpenAI 呼び出しは内部関数（_call_openai_api）をパッチ差し替え可能にして単体テストを容易にする設計。

### Fixed
- なし（初期リリース）

### Changed
- なし（初期リリース）

### Security
- .env 読み込み時に OS 環境変数を保護する仕組みを導入（自動上書きを制限）。  
- 自動 .env ロードは環境変数で無効化可能（テストや CI 用）。

### Breaking Changes
- なし（初期リリース）

---

備考:
- 本 CHANGELOG はリポジトリ内のソースコードから機能・設計を推測して作成した初期の変更履歴です。実際のリリースノート作成時には、リリース日付・マイグレーション手順・互換性注記などを実環境の変更に合わせて追記してください。