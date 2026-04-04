CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

注: 日付はリリース日を示します。

Unreleased
----------
- なし

[0.1.0] - 2026-04-04
--------------------
初回リリース。以下の主要機能と実装を追加。

Added
- パッケージ基本情報
  - パッケージ名 kabusys、バージョン 0.1.0 を追加（src/kabusys/__init__.py）。
  - __all__ を通じて主要サブパッケージ群を公開: data, strategy, execution, monitoring。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（配布後も動作）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - 環境変数保護（既存 OS 環境変数を上書きしない、.env.local は上書き可能）を実装。
  - 設定アクセス用 Settings クラスを実装。J-Quants / kabu / LINE / DB / 監視 / システム設定をプロパティで提供。
  - バリデーション: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の妥当性チェック。
  - pid/kill-flag、リソース閾値（CPU/メモリ/ディスク）など監視用設定を追加。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news + news_symbols を集約して銘柄別にニュースを結合し、OpenAI（gpt-4o-mini）の JSON モードで一括センチメント評価する実装を追加。
  - タイムウィンドウ計算（JST 基準: 前日 15:00 ～ 当日 08:30 → UTC 変換）を提供（calc_news_window）。
  - バッチサイズ制御（最大 20 銘柄/リクエスト）、記事数/文字数トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
  - 再試行ロジック（429/ネットワーク/タイムアウト/5xx に対するエクスポネンシャルバックオフ）。
  - レスポンスバリデーション（JSON 抽出、results リスト、code・score の検証、±1.0 でクリップ）。
  - 取得スコアを ai_scores テーブルへ冪等的に書き込む（DELETE → INSERT、部分失敗時に既存データを保護）。
  - テスト容易性: OpenAI 呼び出しを置き換え可能（_call_openai_api を patch 可能）。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で market_regime に書き込む機能を実装。
  - ma200 比の計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）、マクロニュース抽出、LLM 呼び出し（gpt-4o-mini）の実装。
  - API エラー時は macro_sentiment を 0.0 とするフェイルセーフ、冪等 DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
  - OpenAI 呼び出しのリトライ・エラーハンドリングを実装。
  - テスト容易性: _call_openai_api の差し替えを想定。

- データプラットフォーム（src/kabusys/data/*）
  - ETL パイプラインのインターフェース（ETLResult の公開）を追加（src/kabusys/data/etl.py, pipeline.py）。
    - ETLResult は取得数・保存数・品質問題・エラー等を保持し、has_errors / has_quality_errors プロパティと to_dict を提供。
  - ETL の差分更新・バックフィル・品質チェック方針を実装（設計方針・定数定義）。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）を追加。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の場合の曜日ベースのフォールバック、DB 優先ルール、最大探索日数による保護を実装。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存する夜間バッチ処理を実装（バックフィル、健全性チェック含む）。
  - jquants_client / quality 等のクライアント連携を想定した設計。

- リサーチ（src/kabusys/research/*）
  - ファクター計算（factor_research.py）
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。データ不足時は None を返す。
    - ボラティリティ/流動性: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - バリュー: raw_financials から EPS/ROE を取得し PER/ROE を算出（EPS=0/欠損は None）。
    - DuckDB を用いた SQL ベース実装。全関数は prices_daily / raw_financials のみ参照。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）の fwd リターンを取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を実装（十分なサンプルがない場合は None）。
    - ランク変換ユーティリティ（rank）および統計サマリー（factor_summary）を追加。
    - 外部依存を持たず標準ライブラリのみで実装。

- ロギング・安全設計
  - 多数の場所でログ出力（info/debug/warning/exception）を追加し、異常時の詳細を記録。
  - DB 書き込み失敗時の ROLLBACK とその失敗時の警告ログを実装。
  - ルックアヘッドバイアス防止のため日付取得方法に注意（datetime.today() などを直接参照しない設計方針を明示）。

Changed
- 該当なし（初回リリース）。

Fixed
- 該当なし（初回リリース）。

Deprecated
- 該当なし。

Removed
- 該当なし。

Security
- OpenAI API キー未設定時は明示的に ValueError を送出して誤使用を防止（各 AI モジュール）。
- 環境変数の自動上書きをデフォルトで抑止し、OS 環境変数を保護する仕組みを提供。

Notes / Known limitations
- OpenAI 呼び出しは gpt-4o-mini を想定しており、API レスポンス形式は JSON モードに依存する。
- DuckDB 固有の挙動（executemany の空リスト制約やリスト型バインドの互換性等）に配慮した実装になっている。
- 一部外部クライアント（jquants_client等）は本実装ではモジュール参照のみで具体的実装は外部に依存する。
- 本リリースでは PBR・配当利回りなど一部ファクターは未実装（calc_value の注記参照）。

各モジュールの詳細な使用方法は該当ソースファイルの docstring を参照してください。