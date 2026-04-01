# CHANGELOG

すべての変更は「Keep a Changelog」形式に準拠し、セマンティックバージョニング（MAJOR.MINOR.PATCH）に従います。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-01
初回リリース。日本株自動売買システムのコアライブラリを公開します。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージのエントリポイントを追加（__version__ = 0.1.0）。
  - 公開モジュール一覧: data, strategy, execution, monitoring。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルと環境変数から設定を読み込む自動ローダーを実装（プロジェクトルートを .git / pyproject.toml で探索）。
  - .env パースの堅牢化：
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理などに対応。
    - 上書き制御（override）と保護キーセット（protected）を実装。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを追加し、アプリ設定をプロパティ経由で取得（必須キー確認、既定値、型変換、値検証を実装）。
    - 対応設定例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, Slack チャンネル, DB パス (DuckDB/SQLite)、監視閾値、環境（development/paper_trading/live）、ログレベル検証 など。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を入力に OpenAI（gpt-4o-mini）の JSON Mode を利用して銘柄ごとのセンチメント ai_score を生成し、ai_scores テーブルへ書き込み。
  - 機能:
    - タイムウィンドウ計算（JST 基準で前日 15:00 〜 当日 08:30 の記事を対象）。
    - 銘柄ごとに記事を集約（最大記事数・最大文字数でトリム）。
    - チャンクバッチ（最大 20 銘柄）で API 呼び出し。
    - レスポンスのバリデーション（JSON 抽出、results フォーマット、code/score 検証）。
    - スコアを ±1.0 にクリップして保存。
  - フェイルセーフ / 耐障害性:
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ付きリトライ。
    - API 失敗やパースエラー時は例外を上げず該当チャンクをスキップして他データを保護。
    - DuckDB の executemany 空リスト問題への対策（空の場合は呼ばない）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull / neutral / bear）を算出し market_regime テーブルへ冪等書き込み。
  - 設計上の特徴:
    - ルックアヘッドバイアス回避（datetime.today()/date.today() を参照せず、prices_daily は target_date 未満のデータを使用）。
    - LLM 呼び出しのリトライ・エラー処理（API 失敗時は macro_sentiment=0.0 にフォールバック）。
    - OpenAI クライアントの疎結合設計（内部 _call_openai_api は news_nlp と別実装でテスト差し替えが可能）。
    - スコア計算時のクリップ、ラベル付与、DB トランザクション（BEGIN/DELETE/INSERT/COMMIT）およびロールバック処理。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（calendar_management）:
    - market_calendar テーブルの利用による営業日判定 API（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 未登録日の曜日ベースフォールバック、最大探索日数制限、バックフィル・健全性チェック。
    - calendar_update_job により J-Quants から差分取得して冪等保存（バックフィル考慮、例外安全）。
  - ETL パイプライン（pipeline）:
    - ETLResult dataclass を公開（取得・保存件数、品質チェック問題、エラー集計等を保持）。
    - 差分更新・バックフィル・品質チェックを想定した設計（jquants_client と quality モジュールとの連携）。
  - ETL ユーティリティ再エクスポート（data.etl -> ETLResult）。

- 研究用モジュール（kabusys.research）
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER/ROE）を DuckDB の prices_daily/raw_financials を用いて計算。
    - データ不足時の None 扱い、営業日スキャンバッファ等の設計考慮。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン、入力検証）、IC（Spearman ランク相関）計算、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等外部依存なしで標準ライブラリ + DuckDB による実装。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーは明示的に引数で注入可能。また環境変数 OPENAI_API_KEY を利用。キー未指定時は ValueError を発生させ、誤動作を防止。

注記:
- 多くの箇所で「ルックアヘッドバイアスを防ぐ」「DB 書き込みは冪等性を重視」「API 呼び出しはリトライとフェイルセーフを併用」などの設計方針を採用しています。
- DuckDB 固有の挙動（executemany の空リスト不可など）への対策が各所に実装されています。

--------------------------------------------------------------------------------
この CHANGELOG はコードの注釈・実装内容から推測して作成しています。実際のリリースノート作成時には追加の変更点や既知の問題、マイグレーション手順などを追記してください。