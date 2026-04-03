CHANGELOG
=========
（このファイルは Keep a Changelog 準拠で記述しています）

Unreleased
----------
- なし

[0.1.0] - 2026-04-03
--------------------
初回リリース。以下の主要機能・実装を含みます。

Added
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys.__init__、バージョン 0.1.0）。
  - パッケージ公開 API 書き出し（data, strategy, execution, monitoring）。

- 環境設定 / ロード (.env)
  - .env ファイルまたは環境変数から設定を読み込む設定管理モジュールを追加（kabusys.config）。
  - プロジェクトルートを __file__ を基準に探索して .env / .env.local を自動読み込み。CWD に依存しない設計。
  - .env パーサを実装:
    - コメント行、export KEY=val 形式、シングル/ダブルクォート対応、クォート内のバックスラッシュエスケープに対応。
    - クォートなしの場合、'#' が直前にスペース/タブある場合のみコメント扱いにするなど細かい挙動。
  - 自動読み込みを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - OS 環境変数保護（.env の上書き制御／protected セット）。
  - Settings クラスを提供し、主要設定のプロパティ化：
    - J-Quants / kabuステーション / LINE / DB パス（duckdb/sqlite）/監視閾値/ログレベル/環境種別等を取得。
    - 必須項目取得時のエラーハンドリング（_require）。

- データ（DataPlatform 相当）
  - ETL 結果を表す ETLResult データクラスを追加（kabusys.data.pipeline）。取得・保存件数、品質問題、エラーの集約と辞書化 to_dict を提供。
  - ETL ユーティリティの公開インターフェース（kabusys.data.etl）で ETLResult を再エクスポート。
  - マーケットカレンダー管理モジュール（kabusys.data.calendar_management）を実装：
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティ。
    - market_calendar テーブルが存在しない場合の曜日ベースのフォールバック。
    - calendar_update_job により J-Quants から差分取得 → market_calendar へ冪等保存（jq クライアント経由）。バックフィル、健全性チェック付き。
    - 最大探索日数など無限ループ防止、DuckDB から返る日付の安全変換などの補助機能。

- AI（ニュースNLP・レジーム判定）
  - ニュースセンチメント解析（kabusys.ai.news_nlp）：
    - raw_news と news_symbols を集約し、銘柄毎に記事を連結して OpenAI（gpt-4o-mini）へバッチ送信して ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（JST 前日 15:00 〜 当日 08:30 相当）を calc_news_window として提供。
    - バッチサイズ、1銘柄あたりの最大記事数／文字数トリム等によるトークン肥大化対策を実装。
    - JSON mode を用いたレスポンス検証（厳密な JSON 検証 + 前後余分テキストからの {} 抽出対応）。
    - リトライ戦略（429・ネットワーク断・タイムアウト・5xx は指数バックオフで再試行）。その他のエラーはスキップして継続（フェイルセーフ）。
    - レスポンス検証に基づきスコアを ±1 にクリップし、部分成功時に既存スコアを保護するためコード絞り込みで DELETE → INSERT（トランザクション）を実行。
    - score_news API を公開（DuckDB 接続と target_date を受け取る）。

  - 市場レジーム判定（kabusys.ai.regime_detector）：
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp.calc_news_window を用いて抽出し、OpenAI でマクロセンチメントを評価（gpt-4o-mini, JSON mode）。記事が無ければ LLM 呼び出しをスキップして macro_sentiment=0.0。
    - LLM 呼び出し専用の堅牢なリトライ・バックオフ処理を実装。API 失敗時は 0.0 にフォールバックし処理継続。
    - レジームスコアの合成式と閾値によるラベリング、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時ROLLBACKと警告ログ）。

- リサーチ / ファクター計算
  - ファクター計算モジュール（kabusys.research.factor_research）：
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日 MA 乖離）を計算（データ不足時は None）。
    - Volatility/Liquidity: 20 日 ATR（atr_20, atr_pct）、20 日平均売買代金、出来高比率を計算。
    - Value: raw_financials から直近財務を取って PER / ROE を計算（EPS が 0 または NULL の場合は None）。
    - DuckDB 上の SQL とウィンドウ関数を活用した一貫した実装。
    - 関数は prices_daily / raw_financials のみを参照し、本番 API 等にはアクセスしない設計。

  - 特徴量探索（kabusys.research.feature_exploration）：
    - 将来リターン calc_forward_returns（任意ホライズン、ホライズン検証あり）。
    - IC（Information Coefficient）計算 calc_ic（Spearman ランク相関、有効レコード 3 未満は None）。
    - rank() ユーティリティ（同順位は平均ランク、丸め対策あり）。
    - factor_summary() により count/mean/std/min/max/median を算出。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーといった機密値は環境変数経由で取得。必須未設定時は明示的に ValueError を発生させる仕様（score_news / score_regime / Settings の必須プロパティ）。

Notes / 実装上の設計方針（重要）
- ルックアヘッドバイアス防止:
  - 各モジュール（ニュース集約、レジーム判定、ファクター計算等）は datetime.today() や date.today() を直接参照せず、呼び出し側から与えられる target_date のみを基準に動作するよう設計。
  - DB クエリでは date < target_date（排他）や半開区間を使って未来データ参照を防止。
- エラー処理とフェイルセーフ:
  - LLM/API の一時的失敗は指数バックオフでリトライし、最終的に失敗した場合はスコアを 0.0 や空辞書にフォールバックして処理を継続する仕様（システムの健全性優先）。
- トランザクション性:
  - market_regime や ai_scores への書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で実行、失敗時は ROLLBACK を試みる。
- DuckDB 互換性考慮:
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）への対処のため、書き込み前に params が空でないことをチェック。
- OpenAI 呼び出し:
  - gpt-4o-mini を利用し JSON Mode（response_format={"type": "json_object"}）で厳密な JSON を期待。
  - モジュール間で内部的な _call_openai_api を共有せず、各モジュールで独立実装して単体テスト容易性を高める（テスト時に patch して置換可能）。
- ロギング:
  - 各主要処理に INFO/DEBUG/WARNING/EXCEPTION ログを埋め込んで運用時のトラブルシュートを容易に。

開発者向け補足
- 主要な環境変数名（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL,
    LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID,
    DUCKDB_PATH, SQLITE_PATH,
    PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START,
    CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT,
    KABUSYS_ENV（development|paper_trading|live）, LOG_LEVEL
- テストの容易化:
  - OpenAI 呼び出し関数は各モジュールで専用関数として実装しているため、unittest.mock.patch により容易にモック化可能。

今後の予定（例）
- strategy / execution / monitoring モジュールの実装と統合テスト
- より多様なファクタ（PBR・配当利回り等）の追加
- Webhook・監視・運用向け CLI/サービス化

-----

（注）この CHANGELOG は提示されたコードを基に内容を推測して作成しています。実際のリリースノート作成時はリリース日・追加の変更点・マイグレーション手順等を合わせて正確に反映してください。