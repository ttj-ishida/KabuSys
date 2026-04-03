CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-03
--------------------

Added
- 初回リリース。日本株自動売買／データ基盤／リサーチ用ユーティリティ群をまとめて公開。
- パッケージのメタ情報:
  - kabusys パッケージ初期バージョン 0.1.0 を設定。
  - モジュールエクスポート: data, strategy, execution, monitoring を公開。
- 環境設定管理 (kabusys.config):
  - .env/.env.local 自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を起点に探索。
  - .env パーサーは export 宣言、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応。
  - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスでアプリケーション設定を統一取得 (J-Quants / kabu API / LINE / DB パス /監視閾値 / 環境フラグ等)。
  - 環境変数チェック (必須変数の ValueError、KABUSYS_ENV / LOG_LEVEL の値検証) を実装。
- データプラットフォーム (kabusys.data):
  - calendar_management:
    - JPX マーケットカレンダー管理機能を追加。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar の未取得時は曜日ベースのフォールバックを行う設計。
    - calendar_update_job により J-Quants からの差分取得と冪等保存を実装（バックフィル・健全性チェック付き）。
  - pipeline / etl:
    - ETLResult データクラスを実装し ETL 結果の集約と辞書化を提供（品質問題・エラーの集約）。
    - ETL 処理の設計方針を満たすユーティリティ群（差分取得、バックフィル、品質チェック連携等）の基礎を実装。
  - ETL の DuckDB 連携用ユーティリティ（テーブル存在確認や最大日付取得など）を実装。
  - jquants_client 経由でのデータ取得／保存との連携を想定したインターフェースを用意。
- ニュースNLP / AI モジュール (kabusys.ai):
  - news_nlp:
    - OpenAI (gpt-4o-mini) を用いたニュース記事の銘柄別センチメント付与機能を実装（score_news）。
    - 前日15:00 JST ～ 当日08:30 JST のウィンドウ計算（UTC への変換）を提供（calc_news_window）。
    - 銘柄ごとに記事を集約し、トリム（記事数・文字数）してバッチ送信（最大20銘柄 / チャンク）。
    - JSON Mode を使ったレスポンス処理と堅牢なバリデーション（結果構造・型検証・未知コード無視・スコアの有限性検査）。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフ・リトライ、失敗時は該当チャンクをスキップして継続するフォールトトレラント設計。
    - DuckDB への書き込みは「取得済みコードのみ置換 (DELETE → INSERT)」の方式で部分失敗時の保護を実現。
  - regime_detector:
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム判定（bull/neutral/bear）を行う score_regime を実装。
    - news_nlp の時間ウィンドウ計算を利用し、マクロキーワードでフィルタしたタイトルを LLM に投げてマクロセンチメントを取得（記事なし / API 失敗は 0.0 フォールバック）。
    - OpenAI 呼び出しは専用の内部実装を持ち、モジュール間のプライベート関数共有を避ける設計。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
- リサーチ (kabusys.research):
  - factor_research:
    - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性指標（20日平均売買代金、出来高比率）、バリュー（PER, ROE）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB SQL を活用した効率的な集計・ウィンドウ関数利用の実装。
    - データ不足時の None ハンドリングとログ出力。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）を実装。複数ホライズン対応（デフォルト [1,5,21]）で入力検証あり。
    - IC（Information Coefficient、Spearman の ρ）計算（calc_ic）とランク付けユーティリティ（rank）。
    - ファクター統計サマリー（factor_summary）を実装。標本数や基本統計量（count/mean/std/min/max/median）を提供。
- 共通設計上の注意点（ドキュメント化・実装）:
  - ルックアヘッドバイアス防止: どのモジュールも内部で date.today() を参照しない設計（target_date を明示的に渡す）。
  - DuckDB を主要なストレージとして利用。
  - API キーや機密値の取り扱いは環境変数ベース（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）。
  - ロギングと堅牢な例外ハンドリングを重視（警告ログ・復帰戦略・トランザクションの ROLLBACK 処理等）。

Changed
- 該当なし（初回リリース）。

Fixed
- OpenAI レスポンスのパース耐性を強化:
  - JSON Mode を使用するが、前後に余計なテキストが混ざる場合を想定して最外側の { ... } を抽出するフォールバックを実装。
  - 数値以外の score を検出した際のログ出力とスキップ処理を実装。
- DuckDB の executemany に対する互換性対策:
  - executemany に空リストを渡さないガードを追加し、DuckDB 0.10 系との互換性を確保。
- .env パーサーの堅牢化:
  - export プレフィックス対応、引用符内のバックスラッシュエスケープ、インラインコメントの取り扱いを実装。
- API 呼び出しでのリトライ・バックオフロジックを全体的に整備（news_nlp と regime_detector で一貫性ある戦略）。

Security
- API キーの要求:
  - news_nlp.score_news / regime_detector.score_regime は OPENAI_API_KEY（引数または環境変数）を必須とし、未設定時に ValueError を送出。
- 環境読み込み:
  - OS 環境変数は .env による上書きを保護（protected set）し、必要に応じて自動ロードを無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Removed
- 該当なし（初回リリース）。

Notes / マイグレーション
- データベースの想定テーブル:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials などのテーブルを前提として処理するため、ETL 側でこれらのスキーマを用意してください。
- 環境変数の主要キー:
  - OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等を利用します。未設定の場合は Settings がデフォルトや例外を返します。
- DuckDB バージョン依存:
  - executemany の空リスト取り扱いなど、DuckDB のマイナーバージョン差分に対する互換性考慮を行っていますが、運用環境の DuckDB バージョンでの動作確認を推奨します。

ライセンスや貢献ガイドライン等は別途プロジェクトルートのファイルを参照してください。