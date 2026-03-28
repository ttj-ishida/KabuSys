# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このファイルはコードベースから推測して作成した初期リリース向けの変更履歴です。

なお、本リリースはパッケージバージョン __version__ = "0.1.0" に対応します。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。以下の主要機能・モジュールを実装しました。

### Added
- パッケージ基盤
  - kabusys パッケージを新規追加。
  - パッケージ公開情報（src/kabusys/__init__.py）にバージョンおよび公開モジュールを定義。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーの実装：コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメント処理などに対応。
  - .env 読み込み時の既存 OS 環境変数保護機能（protected set）を実装。override の挙動を制御可能。
  - Settings クラスを提供：J-Quants / kabu API / Slack / DB パス（DuckDB/SQLite）/環境（development/paper_trading/live）/ログレベル等のプロパティを取得・検証。
  - 必須環境変数未設定時に明確なエラーメッセージを出す _require 関数を実装。

- AI（自然言語処理）モジュール（src/kabusys/ai）
  - ニュースNLP（src/kabusys/ai/news_nlp.py）
    - raw_news テーブルを入力に、銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ書き込む機能を実装。
    - 対象時間ウィンドウの計算（JST → UTC 変換）を実装（calc_news_window）。
    - バッチサイズ、トークン肥大化対策（記事数上限・文字数トリム）を導入。
    - OpenAI へのリクエストで JSON mode を利用、429/ネットワーク断/タイムアウト/5xx に対する指数バックオフと再試行ロジックを実装。
    - レスポンスの堅牢なバリデーション実装（JSON 前後ノイズの復元、results フォーマット検査、未知コード無視、数値チェック、±1.0 でクリップ）。
    - DuckDB の executemany による空リスト問題に配慮し、書き込み前に空チェックを行う設計。
    - API キー注入（引数経由）と unittest.mock による _call_openai_api 差し替えを想定したテストフックを提供。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200日移動平均乖離（重み70%）とニュース由来の LLM マクロセンチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む機能を実装。
    - ma200_ratio 計算、マクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini）とスコア合成、閾値判定を含むフローを実装。
    - API 失敗時は macro_sentiment=0.0 でフォールバックするフェイルセーフ設計。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - テスト用に _call_openai_api を差し替え可能。

- データ/ETL/カレンダー（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを参照する営業日判定ユーティリティを提供（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB データ優先、未登録日は曜日（週末）ベースのフォールバックという一貫した設計。
    - calendar_update_job：J-Quants クライアント経由でカレンダー差分取得 → 保存（ON CONFLICT 相当）・バックフィル・健全性チェックの夜間バッチを実装。
    - 最大探索日数やバックフィル日数などを定数化し安全性を担保。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - 差分取得 → 保存 → 品質チェック の流れを想定した ETLResult データクラスを実装（取得数・保存数・品質問題・エラーの集約）。
    - _get_max_date 等のヘルパーで DuckDB テーブルの存在チェックと最大日付取得を実装。
    - backfill／calendar lookahead 等のデフォルト動作を定義し、部分失敗時にも既存データを保護する保存戦略を採用。
    - quality モジュールと連携する設計（品質問題は収集して呼び出し元が判断）。

- リサーチ / ファクター（src/kabusys/research）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M）、200日MA乖離、Volatility（20日 ATR）、Liquidity（20日平均売買代金、出来高比率）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - raw_financials / prices_daily を使って PER、ROE を計算するバリュー指標を実装。
    - データ不足時の None 戻しやログ出力など堅牢性に配慮。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク（rank）、統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで計算する方針。
  - research パッケージの __init__ で主要関数を再エクスポート（利便性向上）。

- データモジュールの公開（src/kabusys/data/__init__.py）
  - pipeline.ETLResult を etl モジュールで再公開。

### Design / Implementation notes
- ルックアヘッドバイアス対策
  - AI スコアリング関数やファクター計算関数は内部で datetime.today() / date.today() を直接参照せず、呼び出し側が target_date を明示的に渡す設計。
  - DB クエリは target_date 未満 / 以上等の排他条件で将来データの参照を防止。

- OpenAI 呼び出し関連
  - gpt-4o-mini と JSON Mode を想定したプロンプト設計とレスポンス検証を実装。
  - API の一時障害や 5xx に対しては指数バックオフで再試行するが、最終的に失敗しても例外を上位に伝えずフェイルセーフで継続する箇所がある（サービス可用性優先の設計）。

- DuckDB 互換性配慮
  - executemany に空リストを渡せないバージョンの問題に対処するチェックを実装。
  - 日付の取り扱いや SQL の互換性を考慮した実装（ROW_NUMBER、window 関数の利用等）。

- テストしやすさ
  - OpenAI 呼び出し用の内部関数を patch 可能にしてユニットテストで差し替えやすくしている。

### Security / Requirements
- AI 機能を利用するには OPENAI_API_KEY（引数経由も可）の設定が必要。
- その他、J-Quants / kabu ステーション / Slack 用の環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）が設定必須。
- デフォルトの DB パスは data/kabusys.duckdb（DuckDB）と data/monitoring.db（SQLite）。

### Fixed
- 初回リリースのため該当なし。

### Changed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

---

注: 実装はコードベースからの推測に基づいて要点をまとめたもので、実際の挙動や外部依存（jquants_client 実装、OpenAI SDK バージョン差異、DuckDB バージョン等）により細部は異なる場合があります。必要であれば、各モジュールごとにより詳細なリリースノートを作成します。