# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースの内容から推測して作成しています。

全般的な方針・注意
- 多くのモジュールで「ルックアヘッドバイアス防止」のため datetime.today()/date.today() を直接参照しない設計が採用されています。全ての関数は target_date を明示的に受け取り、その範囲内でのみデータを参照します。
- OpenAI（gpt-4o-mini）呼び出し箇所はテスト容易性のため内部呼び出し関数を patch できるように分離されています（unittest.mock.patch を想定）。
- DuckDB 周りの互換性考慮（executemany に空リストを渡さない等）やフェイルセーフ（APIエラー時にゼロやスキップで継続）など、堅牢性を重視した実装になっています。

## [Unreleased]
（現在のリポジトリは初期リリースの状態と想定）

## [0.1.0] - 2026-04-01
初期リリース（コードベースから推測）

### Added
- パッケージ基礎
  - kabusys パッケージ初期バージョンを追加（__version__ = "0.1.0"）。
  - モジュール公開インターフェースを整備（data, strategy, execution, monitoring 等を __all__ に含む）。

- 設定管理（kabusys.config）
  - .env ファイルと環境変数を扱う自動ロード機能を追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - 柔軟な .env パーサー実装（_parse_env_line）:
    - export KEY=val 形式のサポート、シングル／ダブルクォートとバックスラッシュエスケープ処理、インラインコメント扱いのロジックなど。
  - Settings クラスを公開（settings）:
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / システム環境（KABUSYS_ENV）等の環境変数取得と検証（必須変数未設定時は ValueError を送出）。
    - env / log_level の値検証（許容値チェック）や is_live / is_paper / is_dev のヘルパーを提供。

- AI 関連（kabusys.ai）
  - news_nlp モジュール（score_news）:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI にバッチ（最大 _BATCH_SIZE=20 銘柄）で送信しセンチメントを算出。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - リトライ戦略（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）。
    - レスポンスの堅牢なバリデーション（JSON パース回復処理、results フィールド検証、未知コードの無視、スコアの数値変換と ±1.0 でのクリップ）。
    - DuckDB との書き込みは「対象コードのみを DELETE → INSERT」して部分失敗時に既存スコアを保持する手順を採用。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能。
  - regime_detector モジュール（score_regime）:
    - ETF 1321 の 200 日移動平均乖離（MA）と、マクロ経済ニュースの LLM センチメントを重み合成（MA:70%、macro:30%）して市場レジーム（bull / neutral / bear）を日次で判定。
    - MA 計算は target_date 未満のデータのみを使用しルックアヘッドを防止。
    - マクロニュース抽出はタイトルベースでキーワードフィルタ（_MACRO_KEYWORDS）を使用。
    - OpenAI 呼び出しのリトライとフォールバック（失敗時は macro_sentiment=0.0）。
    - market_regime への冪等的書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - テストで差し替え可能な内部 API 呼び出し関数を提供。

- 研究用ユーティリティ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離などを計算（prices_daily を参照）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials から最新財務を取得して PER, ROE を計算（target_date 以前の最新レコードを使用）。
    - 各関数はデータ不足時に None を返す等の安全設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンの順位相関（IC）を算出（同順位は平均ランク）。
    - rank, factor_summary: ランク変換と統計サマリー（count/mean/std/min/max/median）を提供。
  - zscore_normalize は kabusys.data.stats から再エクスポートされる想定（__init__ で import）。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar テーブルを扱う営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
    - DB 登録データを優先しつつ未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得し、バックフィル（直近 _BACKFILL_DAYS）と健全性チェックを行って market_calendar を更新する夜間バッチ処理。
  - pipeline / etl:
    - ETLResult データクラスを追加（ETL 実行の集約結果、品質問題リスト、エラーリストを含む）。
    - pipeline モジュール（差分取得、保存、品質チェック）を想定したインターフェースとユーティリティ関数を実装。
    - 差分更新のための最小データ日（_MIN_DATA_DATE）やバックフィル設定等を含む。
    - jquants_client による保存処理と quality モジュールによる品質チェックを組み合わせる設計。

### Changed
- （初回リリースのため特別な「変更」は無し。上記は新規追加機能の一覧です。）

### Fixed / Notes
- DuckDB の互換性対応:
  - executemany に空リストを渡すと失敗するバージョン対策として、パラメータリストが空でないことを保ってから executemany を実行する実装を追加（news_nlp.score_news 等）。
- OpenAI レスポンスの堅牢処理:
  - JSON mode でも前後に雑多な文字列が混入するケースを考慮して最外の {} を抽出して JSON を復元する処理を追加（news_nlp._validate_and_extract）。
- フェイルセーフ方針:
  - AI API 障害時は処理を例外で止めず、ログ出力の上でゼロやスキップにフォールバックする設計（サービスの継続性優先）。
- テスト支援:
  - OpenAI 呼び出しを包んだ内部関数をモジュール内に分離し、ユニットテスト時に差し替えられるようにしている（_call_openai_api の patch を想定）。

### Security
- 自動的に .env を読み込む機能が有効化されているため、CI/実行環境での意図しない環境変数の読み込みを防ぐには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

---

使用例 / 備考（開発者向け）
- 環境設定:
  - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings のプロパティで検証）。
- AI スコアリング:
  - news_nlp.score_news(conn, target_date, api_key=None)  
  - regime_detector.score_regime(conn, target_date, api_key=None)  
  - どちらも api_key を省略した場合は環境変数 OPENAI_API_KEY を参照する。未設定時は ValueError を送出。
- テスト:
  - OpenAI API 呼び出し部分はモジュール内 private 関数を patch して差し替え可能（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。

もしリリースノートをさらに詳細化（例: 各関数のサンプル出力、既知の制限、互換性ポリシー、マイグレーション手順）したい場合は、どの領域（AI 部分 / データ ETL / 研究モジュール 等）を優先して深掘りするか教えてください。