# CHANGELOG

すべての変更は「Keep a Changelog」の仕様に準拠して記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/

注: 本 CHANGELOG は提示されたソースコードから実装内容・設計意図を推測して作成しています。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-03-31
初回リリース。以下の主要機能と実装を含みます。

### Added
- パッケージ基盤
  - kabusys パッケージの初期エントリポイント（src/kabusys/__init__.py）。
  - パッケージバージョンを 0.1.0 に設定。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local 自動読み込み（読み込み優先順位: OS 環境 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .git または pyproject.toml を基準にプロジェクトルートを探索し、CWD に依存しない自動ロード実装。
  - 高度な .env パーサ実装:
    - コメント行・export プレフィックス対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなしでのインラインコメント検出（直前がスペース/タブの場合のみ）
  - 既存 OS 環境変数の保護（protected set）と override フラグをサポート。
  - Settings クラスでアプリ設定をプロパティとして公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の必須チェック（未設定で ValueError）。
    - KABU_API_BASE_URL, DUCKDB_PATH（既定: data/kabusys.duckdb）, SQLITE_PATH（既定: data/monitoring.db）, PID_FILE_PATH 等のデフォルト。
    - 環境別判定プロパティ（is_live / is_paper / is_dev）と LOG_LEVEL 検証。
    - リソース閾値（CPU/MEM/DISK）の読み込み。

- AI / ニュース分析（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を用いた銘柄ごとのニュース集約ロジック（窓: 前日15:00 JST〜当日08:30 JST を UTC に変換して比較）。
  - OpenAI（gpt-4o-mini）を用いたバッチセンチメント評価:
    - 1バッチで最大 20 銘柄処理、1銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK=10、_MAX_CHARS_PER_STOCK=3000）。
    - JSON-mode レスポンスのバリデーション（results リスト、code/score の検証、未知コード無視、スコアを ±1 にクリップ）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフおよびリトライ。
    - 失敗時は安全にスキップし、部分成功のみ ai_scores テーブルを置換（DELETE → INSERT）して既存スコアを保護。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（ユニットテストで patch 可能）。
  - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。API キー未設定時は ValueError。

- AI / 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（Nikkei225 連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
  - ma200_ratio 計算（target_date 未満データのみ使用、データ不足時は中立値 1.0 を返す）。
  - マクロニュース抽出（マクロキーワードによるフィルタ）と LLM 呼び出し（gpt-4o-mini）。記事がない場合は LLM 呼び出しをスキップして macro_sentiment=0.0。
  - LLM 呼び出しはリトライ・バックオフを実装し、永続的失敗時は 0.0 にフォールバック（例外を投げず継続）。
  - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。API キー未設定時は ValueError。

- リサーチ / ファクター計算（src/kabusys/research/*.py）
  - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（データ不足時は None）。
  - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率。
  - calc_value: raw_financials から最新の EPS/ROE を取得して PER / ROE を計算（EPS=0/欠損時は None）。PBR 等は未実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード<3 の場合は None）。
    - rank: 同順位は平均ランク（丸めにより ties の検出精度を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算。
  - 全体の設計方針として DuckDB 接続を受け取り、prices_daily / raw_financials のみ参照し、外部発注やネットワークアクセスは行わない。

- データ基盤（src/kabusys/data/*.py）
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブルの夜間更新ジョブ calendar_update_job）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB データが存在する場合は DB 値を優先し、未登録日は曜日ベース（平日）でフォールバックする一貫したロジック。
    - calendar_update_job は jquants_client を使って差分取得・バックフィル（直近 _BACKFILL_DAYS を必ず再取得）し、健全性チェックを実施。
  - pipeline / ETL:
    - ETLResult データクラス（ETL 実行結果の構造化、品質問題やエラーの一覧を保持）。
    - ETL パイプライン設計の骨格（差分取得、保存、品質チェックの設計方針を実装）。jquants_client と quality モジュールを利用する想定。
    - data.etl に ETLResult を再エクスポート。

- 共通実装
  - DuckDB を主要な分析ストレージとして使用する想定（関数は DuckDB 接続を受け取る）。
  - 時刻/日付の扱いでルックアヘッドバイアスを避ける設計（datetime.today()/date.today() を直接参照しない箇所が明記されている点）。
  - ロギング（logger）を広範に使用し、失敗時は警告/例外ログを残す実装。

### Fixed
- （初回リリースのため該当なし）

### Changed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーや各種トークンは環境変数で必須化（Settings で未設定時は明示的にエラーを出す）。.env 自動読み込みを無効にするフラグを提供してテスト/運用の安全性を確保。

### Notes / Known issues
- ソーススニペットの終端（src/kabusys/data/pipeline.py の末尾付近）に不完全な行（例: `return date.fro` のような途中断片）があり、スニペットの一部が欠落している可能性があります。実運用前に該当関数の完全実装を確認してください。
- 実行には外部モジュール（openai、duckdb、jquants_client 相当）が必要です。OpenAI 呼び出しや J-Quants クライアントは実環境での API キー設定および依存ライブラリの導入が前提です。
- AI モデルは gpt-4o-mini を想定しているため、将来的なモデル差替えや API 仕様変更に備えた抽象化の検討を推奨します。

---

（終）