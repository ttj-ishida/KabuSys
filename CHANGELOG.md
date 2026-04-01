# Changelog

すべての重要な変更は "Keep a Changelog" の方針に従って記載しています。  
このプロジェクトではセマンティックバージョニングを採用しています。

## [Unreleased]

- （未リリースの変更はここに記載）

## [0.1.0] - 2026-04-01

初期公開リリース。以下の主要機能・モジュールを実装しました。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョン定義（__version__ = "0.1.0"）と公開サブモジュール一覧を追加。

- 環境設定管理（kabusys.config）
  - プロジェクトルート探索機能を実装（.git または pyproject.toml を基準に上位ディレクトリを探索）。
  - .env/.env.local 自動読み込み機能を追加（OS 環境変数優先、.env.local は .env を上書き）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env 行パーサを実装:
    - export プレフィックス対応（export KEY=val）。
    - シングル／ダブルクォート対応（エスケープ処理を考慮して閉じクォートを正しく解析）。
    - 非クォート値に対するインラインコメント判定（# の前がスペース／タブのときのみコメント扱い）。
  - 環境変数の上書き制御（override / protected）をサポート。OS 環境変数を保護する仕組みを導入。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 監視しきい値 / システム環境（development/paper_trading/live）などのプロパティを用意。環境変数未設定や不正値に対する明示的なエラーを出す設計。

- AI（ニュース NLP / レジーム判定）
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON Mode）で銘柄毎のセンチメントスコアを算出して ai_scores テーブルへ保存する処理を実装。
    - バッチサイズ、1銘柄あたりの最大記事数・文字数を制限することでトークン肥大化を抑制。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフによるリトライ。失敗時は該当チャンクをスキップして継続するフェイルセーフ設計。
    - レスポンスの厳密バリデーション（JSON 抽出、results リスト構造、コード照合、スコア数値性、クリップ）を実装。
    - DuckDB の executemany に関する互換性対策（空パラメータ回避）、および部分失敗時に既存スコアを保護する DELETE→INSERT の置換戦略。
    - 単体テストのために OpenAI 呼び出し部分（_call_openai_api）を差し替え可能。
  - kabusys.ai.regime_detector:
    - ETF 1321（225 連動 ETF）の 200 日移動平均乖離とニュース由来のマクロセンチメントを重み合成（70% / 30%）して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする機能を実装。
    - LLM 呼び出しは gpt-4o-mini（JSON 出力）を使用。API 障害時は macro_sentiment=0.0 にフォールバックして継続。
    - DuckDB クエリはルックアヘッドを防ぐ条件（date < target_date 等）を採用。
    - API 呼び出しの再試行・5xx 判定や JSON パース失敗時のロギング/フォールバックを実装。
    - テスト用に呼び出し部分を差し替え可能に設計。

- データ / ETL / カレンダー管理（kabusys.data）
  - calendar_management:
    - market_calendar テーブルを用いた営業日判定ユーティリティを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した判定ロジック。
    - 夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants API から差分取得 → 保存（ON CONFLICT 相当）→ バックフィル/健全性チェックを行う。
    - 最大探索日数やバックフィル、健全性（将来日付異常）などの保護措置を導入。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL 結果の集約、品質問題／エラーの列挙、辞書変換メソッドを備える）。
    - データ差分取得、idempotent な保存、品質チェックの流れを想定した ETL の設計（パラメータ・デフォルト設定を含む）。
    - jquants_client 経由の取得処理と品質チェック連携を想定（実装は jquants_client / quality モジュールに依存）。

- Research（ファクター計算 / 特徴量探索）
  - research.factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER / ROE）の計算関数を実装。全て DuckDB の prices_daily / raw_financials を使用して計算する設計。
    - データ不足時の None 設定や、結果を (date, code) キーの dict リストで返すインターフェースを提供。
    - パフォーマンスのためスキャン範囲にバッファを設け、SQL ウィンドウ関数で計算。
  - research.feature_exploration:
    - 将来リターン計算（任意ホライズン）、Spearman のランク相関（IC）計算、ランク変換ユーティリティ、ファクター統計サマリー関数を実装。
    - pandas 等に依存せず純粋 Python + DuckDB で実装。引数チェックや例外時の明示的な挙動を定義。

- その他
  - data.etl: pipeline.ETLResult を再エクスポート。
  - 各所で DuckDB トランザクションを用いた冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK フォールバックを実装。
  - ロギング（情報・警告・例外）を豊富に配置し運用観点での可観測性を向上。

### Changed
- （この初版リリースでは過去のバージョンからの変更履歴はありません — 初回実装）

### Fixed
- （初回リリースのため既知の修正履歴はありません）

### Notes / Known limitations
- OpenAI API を利用する機能（news_nlp / regime_detector）は API キー（OPENAI_API_KEY）を必要とします。api_key 引数で注入可能。
- LLM 呼び出しは gpt-4o-mini の JSON mode を前提としており、出力形式が期待に沿わない場合は部分的にスキップされる設計です（安全のため失敗時に例外を投げずフェイルセーフでゼロやスキップ）。
- DuckDB のバージョンや executemany の挙動に依存する箇所があるため、運用環境では DuckDB の互換性確認を推奨します。
- 現時点で PBR・配当利回り等、一部バリューファクターは未実装（将来的に拡張予定）。

--- 

本 CHANGELOG はコードベースの実装内容から推測して作成しています。リリースノートとして不足・誤りがある場合はお知らせください。