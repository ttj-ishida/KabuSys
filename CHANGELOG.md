# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このファイルはコードベースから推測して作成した初期の変更履歴です。

## [Unreleased]

なし

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買プラットフォーム「KabuSys」の基盤機能を実装しました。
主要な機能、設計上の注意点、外部依存・環境変数についても記載しています。

### Added
- パッケージ基盤
  - パッケージメタ情報を公開（kabusys.__version__ = 0.1.0）。
  - パッケージトップで主要サブパッケージを公開: data, research, ai, execution, monitoring, strategy（__all__ を通じて整備）。

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動ロード機能実装（OS 環境変数優先、.env.local が .env を上書き）。
  - .env パーサ実装（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントの扱いなど）。
  - プロジェクトルート探索機能（.git または pyproject.toml を基準）を導入し、CWD に依存しない自動読み込みを実現。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供（テストなどで使用可能）。
  - Settings クラスを実装し、主要環境変数をプロパティで公開:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパス設定）
    - KABUSYS_ENV 値検証（development / paper_trading / live のいずれか）
    - LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- データプラットフォーム（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - 差分取得、保存、品質チェックを想定した ETLResult データクラスを追加（品質問題・エラーの集約）。
    - DuckDB を用いた最大日付取得・テーブル存在チェック等のユーティリティを実装。
  - calendar 管理（kabusys.data.calendar_management）
    - market_calendar を利用した営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job を実装（J-Quants API から差分取得し冪等保存、バックフィル、健全性チェック）。
  - ETL インターフェース（kabusys.data.etl）で ETLResult を再エクスポート。

- 研究用モジュール（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）
    - ボラティリティ／流動性（20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率）
    - バリュー（PER, ROE、raw_financials の最新財務データの結合）
    - DuckDB SQL を中心に実装し、(date, code) 単位の辞書リストを返す設計。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、ホライズン指定可能、デフォルト [1,5,21]）
    - IC（Information Coefficient）計算（Spearman ρ）
    - ランキングユーティリティ（rank）とファクター統計サマリー（factor_summary）
  - 研究ユーティリティとして zscore_normalize を data.stats から再エクスポート。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信しセンチメントを算出。
    - JSON Mode（厳密な JSON）で応答を期待し、レスポンスのバリデーション機能を実装（results 配列、code/score、数値チェック、既知コードのみ採用）。
    - バッチサイズやトークン肥大化対策（銘柄あたり最大記事数/最大文字数）を実装。
    - リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフ実装。部分失敗時にも既存スコアを保護するため、書き込みは取得スコアのコードに限定（DELETE→INSERT の冪等処理）。
    - calc_news_window によるニュース収集ウィンドウ（JST: 前日 15:00 ～ 当日 08:30）を実装。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - LLM 呼び出しは gpt-4o-mini を使用、JSON 応答をパースして macro_sentiment を取得。失敗時は 0.0（フェイルセーフ）。
    - レジーム判定用しきい値、スケーリング、ログ・冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
  - 両モジュールとも OpenAI クライアント呼び出し部分（内部 _call_openai_api）を差し替え可能に実装しテスト容易性を確保。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーが未設定の場合は明示的に ValueError を発生させ、呼び出し側が対応できるようにしています（news_nlp.score_news / regime_detector.score_regime）。
- .env 自動ロード時に OS 環境変数を保護（上書き禁止）する仕組みを実装。

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants 用）
  - KABU_API_PASSWORD（kabu ステーション API）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知機能を使う場合）
  - OPENAI_API_KEY（AI 機能を利用する場合。score_news / score_regime では必須）
- .env の自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください（値は任意、存在すれば無効化）。
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring 用): data/monitoring.db
- AI モデル: gpt-4o-mini を前提としたプロンプト・JSON Mode 実装になっています。将来的にモデルを切替える場合は response_format の扱いに注意してください。
- ルックアヘッドバイアス対策: 主要なモジュール（news_nlp, regime_detector, research）では datetime.today()/date.today() を直接参照せず、必ず target_date を明示的に渡す設計です。
- DuckDB の executemany の挙動に依存する箇所があるため（空リスト不可等）、挿入前に空チェックを行う実装になっています。

### テスト・拡張性
- OpenAI 呼び出し部は内部関数を patch 可能にしておりユニットテストで差し替えやすくしています。
- DB 書き込みは基本的にトランザクション（BEGIN/COMMIT/ROLLBACK）で行い、例外時はロールバックを試み、ロールバック自体の失敗もログに残すようにしています。

---

今後のバージョンでは以下を想定しています（実装は未定）:
- 発注・戦略実行関連（execution / strategy）モジュールの具体実装と監視・運用機能の追加
- データ品質チェック機能の詳細実装（quality モジュールの拡張）
- テレメトリ・モニタリングの強化（Slack 連携の拡張等）