# CHANGELOG

すべての重要な変更は Keep a Changelog 準拠で記載します。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-28

初回公開リリース。本プロジェクトのコア機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)

- パッケージの基本構成
  - kabusys パッケージを追加。トップレベルで data, strategy, execution, monitoring モジュールを公開。
  - バージョン: 0.1.0（src/kabusys/__init__.py）。

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env/.env.local ファイル自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーは以下の仕様をサポート:
    - 空行・コメント行 (#) を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応。
    - クォートなしの場合、直前に空白またはタブがある `#` をインラインコメントとして除去。
  - .env の上書き挙動:
    - .env は OS 環境変数を上書きしない（override=False）。
    - .env.local は override=True で上書き。ただし、起動時の OS 環境変数は protected される。
  - Settings クラスを提供（settings = Settings()）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の必須チェック。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- ニュース NLP（AI）モジュール (src/kabusys/ai/news_nlp.py)
  - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出。
  - 機能:
    - ニュース時間窓計算 (calc_news_window)（JST基準で前日15:00〜当日08:30 を UTC 変換して扱う）。
    - 記事集約 (_fetch_articles): 1銘柄あたり最新 N 件、文字数トリム制御。
    - バッチ送信（最大 _BATCH_SIZE=20 銘柄/コール）と JSON Mode (response_format) を利用する呼び出し。
    - リトライ（429、ネットワーク断、タイムアウト、5xx）を指数バックオフで処理。
    - レスポンス検証 (_validate_and_extract): JSON 抽出、"results" フォーマット検証、未知コード除外、スコア数値変換、±1.0 でクリップ。
    - DuckDB への書き込みは部分的置換戦略（DELETE for codes → INSERT）で idempotent に処理。DuckDB 0.10 の executemany 空パラメータ制約に対するガード実装あり。
  - テスト容易性:
    - OpenAI 呼び出し部分はモジュール内プライベート関数で定義されており、unittest.mock.patch による差し替えを想定。

- マーケットレジーム判定（AI）モジュール (src/kabusys/ai/regime_detector.py)
  - ETF（1321）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull / neutral / bear）を実装。
  - 機能:
    - ma200 比率計算（_calc_ma200_ratio）: target_date 未満のデータのみ使用してルックアヘッドを防止。データ不足時は中立（1.0）を返す。
    - マクロニュース抽出（_fetch_macro_news）: キーワードマッチによるタイトル抽出（最大 _MAX_MACRO_ARTICLES）。
    - LLM スコアリング（_score_macro）: OpenAI 呼び出し、JSON 解析、リトライ（429/ネットワーク/5xx）およびフェイルセーフで macro_sentiment=0.0 にフォールバック。
    - 最終スコア合成と market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）・例外時は ROLLBACK。
  - OpenAI 呼び出しは gpt-4o-mini を指定、JSON mode を利用。
  - 設計上、datetime.today()/date.today() を直接参照せず、入力の target_date にのみ依存することでルックアヘッドバイアスを排除。

- ETL / データパイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
  - ETLResult データクラスを実装（target_date, fetched/saved counts, quality issues, errors 等）。
  - 差分取得（最終取得日判定）、バックフィル（デフォルト _DEFAULT_BACKFILL_DAYS=3）、品質チェックを踏まえた ETL 設計方針を記述。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
  - market_calendar を用いた営業日判定・探索機能を提供:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
  - DB 登録有無に応じたフォールバックロジック（DB 登録があれば DB を優先、未登録日は曜日ベースのフォールバック）。
  - 最大探索日数制限 (_MAX_SEARCH_DAYS) により無限ループを回避。
  - calendar_update_job 実装:
    - J-Quants API (jquants_client) から差分取得し market_calendar を冪等に保存。
    - バックフィル、健全性チェック（将来日付の異常検出）を実装。
    - fetch / save の障害を捕捉して安全に 0 を返す設計。

- リサーチ（ファクター計算 / 特徴量探索） (src/kabusys/research/*.py)
  - factor_research.py:
    - calc_momentum: mom_1m/3m/6m、ma200_dev を計算（DuckDB SQL ベース、データ不足は None）。
    - calc_volatility: ATR(20)・相対ATR・20日平均売買代金・出来高比率を計算（true_range の NULL 伝播を考慮）。
    - calc_value: raw_financials から最新財務を結合して PER / ROE を算出（EPS が 0/NULL の場合は None）。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズンに対する将来リターンを一括取得（horizons 検証・最大 252 日上限）。
    - calc_ic: スピアマン型ランク相関（Information Coefficient）を計算。十分な有効レコードがない場合は None を返す。
    - rank: 同順位は平均ランクで処理（内部で round(v,12) による丸めを利用して ties の検出を安定化）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを提供。
  - すべての研究機能は DuckDB に対する SQL または標準ライブラリのみで実装され、外部ライブラリ（pandas 等）に依存しない。

- DuckDB を用いた一貫した DB 操作
  - DuckDB 接続を受け取り SQL + Python で処理を行う設計。
  - DuckDB のバージョン依存性（executemany の空リスト不可等）に対する回避ロジックを実装。

### 改善 (Improved)

- 安全性・堅牢性の向上
  - OpenAI 呼び出しでのエラー種別に応じたハンドリングと適切なログ出力（RateLimitError / APIConnectionError / APITimeoutError / APIError / JSON パースエラー）。
  - 外部 API の失敗は例外送出ではなくフェイルセーフ（中央値や 0.0）にフォールバックする箇所を明示。
  - DB 書き込みを冪等に行い、失敗時は ROLLBACK を試行し、ROLLBACK 自体の失敗を警告ログで通知。

### ドキュメント (Documentation)

- 各モジュールに処理フロー、設計方針、注意点（ルックアヘッドバイアス回避、テストフック、DuckDB 互換性等）を詳細にドキュメントコメントとして追加。

### テスト支援 (Tests)

- OpenAI 呼び出し箇所は内部関数化しており、unittest.mock.patch による差し替えでテスト可能。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装拡充（現状はパッケージ公開のみ）。
- モデルやプロンプトのチューニング、エッジケースの追加テストカバレッジ拡張。
- CI / リリースパイプライン整備、サンプルデータやマイグレーションツールの提供。

---

発行者: kabusys 開発チーム