Changelog
=========

すべての変更は Keep a Changelog の形式に準拠します。  
バージョン番号は src/kabusys/__init__.py の __version__ に基づきます。

[Unreleased]
------------

（現在差分なし）

[0.1.0] - 2026-04-02
-------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」のコア機能群を追加。
  - パッケージ基礎
    - パッケージ名/バージョン定義（kabusys v0.1.0）。
    - パッケージ公開対象モジュール一覧（data, strategy, execution, monitoring）。
  - 設定・環境変数管理（kabusys.config）
    - .env/.env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml で判定）。
    - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 環境変数取得用 Settings クラスを提供。J-Quants / kabuステーション / Slack / DB /監視/システム関連のプロパティ（型変換とバリデーションを含む）。
    - 必須環境変数未設定時は ValueError を送出する _require ヘルパー。
    - 既定値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU/MEM/DISK thresholds など。
  - AI（自然言語処理）モジュール（kabusys.ai）
    - news_nlp.score_news
      - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini、JSON mode）で銘柄別センチメントを算出して ai_scores テーブルに書き込む。
      - JST の時間ウィンドウ計算（前日15:00〜当日08:30）を calc_news_window で実装（UTC に変換）。
      - バッチ処理（最大 20 銘柄 / チャンク）、記事数/文字数トリム、レスポンスバリデーション、スコア ±1.0 クリップ。
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ（最大試行回数制御）。失敗はフェイルセーフでスキップし続行。
      - DuckDB への書き込みは冪等（該当 code の DELETE → INSERT）。DuckDB の executemany の空リスト制約に対応。
    - regime_detector.score_regime
      - ETF 1321 の過去 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
      - マクロセンチメントは news_nlp.calc_news_window で得たウィンドウのタイトルを抽出し、OpenAI に JSON 出力を要求して数値化。API失敗時は 0.0 をフォールバック。
      - レジームスコアの閾値設定（BULL/BEAR）、スコアクリップ、DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）とロールバック処理を実装。
      - テストしやすさのため OpenAI 呼び出しをラップし、テスト時は差し替え可能。
  - Data（データ処理）モジュール（kabusys.data）
    - calendar_management
      - JPX カレンダー（market_calendar）を管理するユーティリティ（営業日判定、次/前営業日、期間内営業日リスト、SQ判定）。
      - カレンダー未取得時は曜日ベース（平日のみ営業日）でフォールバックする設計。
      - calendar_update_job：J-Quants API から差分取得 → 冪等保存、バックフィル・健全性チェック（未来日付異常のスキップ）を実装。
    - pipeline / ETL
      - ETLResult データクラスを公開（ETL 実行結果の集約、品質チェック結果とエラーの収集）。
      - 差分更新、バックフィル、品質チェック方針（エラーは集約して呼び出し元が判断）を反映した設計。
    - jquants_client 連携を前提とした差分取得・保存フローの土台を用意（詳細クライアント実装は別モジュール）。
  - Research（研究用分析）モジュール（kabusys.research）
    - factor_research
      - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金／出来高比）、バリュー（PER、ROE）を DuckDB の prices_daily / raw_financials から計算する関数群（calc_momentum, calc_volatility, calc_value）。
      - データ不足時の None 扱い、SQL ベースの計算でルックアヘッドバイアスを避ける実装。
    - feature_exploration
      - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）に対応、ホライズン検証、まとめて1クエリ取得。
      - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を自前実装で評価（同順位は平均ランク）。
      - ランク変換ユーティリティ（rank）と統計サマリー（factor_summary）。
  - 例外処理・ロギング
    - 各モジュールで詳細なログ出力（info/debug/warning/exception）を実装。DB 書き込み失敗時のロールバック、API 呼び出し失敗のフォールバックを考慮。

Changed
- 該当なし（初回リリースのため変更履歴はなし）。

Fixed
- 該当なし（初回リリースのため修正履歴はなし）。

Notes / Migration / 必須環境変数
- OpenAI API
  - news_nlp / regime_detector は OpenAI（gpt-4o-mini）を使用。api_key を関数引数で注入可能。未設定の場合は環境変数 OPENAI_API_KEY を参照し、未設定だと ValueError を送出。
- 必須の環境変数（Settings で _require されるもの）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 既定値とファイルパス
  - DUCKDB_PATH の既定は data/kabusys.duckdb
  - SQLITE_PATH の既定は data/monitoring.db
  - PID_FILE_PATH の既定は data/execution.pid
- 自動 .env 読み込み
  - プロジェクトルート検出に .git または pyproject.toml を使用。配布後やテスト時に自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- フェイルセーフ設計
  - OpenAI API や外部 API の失敗は基本的にフェイルセーフ（スコア 0.0 やスキップ）で継続し、致命的な DB 書き込みエラーは上位へ伝播する設計。

Security
- 外部キー・トークンは環境変数経由で管理する想定。ソースコード内にハードコードするものはありません。

Acknowledgements / Notes
- DuckDB を主要なローカル DB として利用する設計（SQL を主体にデータ処理を記述）。  
- OpenAI 呼び出しはテスト時に差し替え可能なようにラップしてあり、ユニットテストの容易性を意識した設計。

今後の予定（例）
- strategy / execution / monitoring の具体的な実装追加（発注・実行ループ・監視アラート送信等）。
- jquants_client の完全実装および ETL の自動スケジューリング。
- モデル改善（プロンプトチューニング、レスポンスのより厳密な検証）。

--- 
上記はソースコード内の実装内容およびドキュメンテーション文字列から推測して作成した CHANGELOG です。補足・修正があれば反映します。