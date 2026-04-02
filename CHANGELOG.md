# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
このファイルはリポジトリ内のソースコードから推測して作成した初期リリース向けの変更履歴です。

全般的な注意
- バージョンはパッケージ定義（src/kabusys/__init__.py の __version__）に合わせて 0.1.0 としています。
- OpenAI を使用する機能は環境変数 OPENAI_API_KEY（または関数引数）でキーを受け取ります。
- DuckDB を主要なローカル DB として利用する設計です（DuckDB 接続を引数に取る関数群）。

Unreleased
- （なし）

[0.1.0] - 2026-04-02
--------------------

Added
- パッケージ基盤
  - パッケージエントリ（src/kabusys/__init__.py）とバージョン 0.1.0 を追加。
  - pakage-level __all__ に data, strategy, execution, monitoring を公開。

- 環境設定と自動 .env ロード（src/kabusys/config.py）
  - .env / .env.local ファイルをプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを実装。
  - 読み込み優先順位: OS環境変数 > .env.local > .env（.env.local は override=True）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - .env パーサは export 句・シングル/ダブルクォート・エスケープ・インラインコメントを考慮している。
  - Settings クラスを提供し、主要設定値（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、Slack トークン/チャンネル、DB パス、監視閾値、環境/ログレベル判定など）をプロパティ経由で取得。値検証（KABUSYS_ENV / LOG_LEVEL の許容値）と便利プロパティ（is_live 等）を実装。

- AI（自然言語処理）機能（src/kabusys/ai/*）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄毎にニュースをまとめ、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄ごとのセンチメントスコアを算出。
    - バッチ処理（最大 20 銘柄）・トークン膨張対策（記事数上限・文字数トリム）・指数バックオフによるリトライ実装。
    - レスポンスの堅牢なバリデーションとパース（JSON の前後ノイズ対策含む）、スコアの ±1.0 クリップ。
    - DuckDB への冪等書き込み（対象コードのみ DELETE → INSERT）により部分失敗時のデータ保護。
    - calc_news_window 関数で JST ベースのニュース収集ウィンドウ（前日 15:00 ～ 当日 08:30 JST）を計算。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース LLM マクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - MA 計算は target_date 未満のみを使用しルックアヘッドを防止。ニュースは calc_news_window を利用。
    - OpenAI 呼び出しは JSON mode（厳密 JSON 出力期待）・リトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - ai パッケージ公開（src/kabusys/ai/__init__.py）で score_news を公開。

- データ基盤（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの取得／保存（J-Quants 経由）の夜間バッチ向けロジックを実装（calendar_update_job）。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を非営業日）として堅牢に動作。
    - 営業日判定ユーティリティ群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。探索範囲上限の設定により無限ループを防止。
    - バックフィル / 健全性チェック（最大未来日数の警告）を実装。
  - ETL パイプラインと結果型（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー一覧を格納、辞書化メソッドを提供）。
    - 差分取得・バックフィル・品質チェック（quality モジュール想定）・冪等保存の設計方針を反映。
    - etl.py で ETLResult を再エクスポート（公開インターフェース）。
  - jquants_client 連携ポイントを想定（calendar_management 等が利用）。

- 研究モジュール（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER、ROE）等を DuckDB を用いて計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 扱い、SQL ウィンドウ関数の利用、ログ出力により結果を返す設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic、Spearman の ρ に相当するランク相関）、ランキングユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装し、入力検証（horizons の妥当性等）を行う。
  - research パッケージ __init__ で主要関数を再公開。

Changed
- （初期リリースのため特に「Changed」はなし。設計上の決定事項やフェイルセーフ方針を各モジュール内に明記。）

Fixed
- （初期リリースのためなし）

Security
- .env 読み込み時に既存 OS 環境変数を保護するため protected セットを導入（.env の上書き制御）。
- OpenAI 呼び出しに関してはタイムアウトとリトライ制御を行い、API 失敗時は例外を暴露しないフェイルセーフ挙動（ただし必須 API キー未設定時は ValueError を送出）。

Notes / 開発者向け補足
- OpenAI を使う機能:
  - API キー: 関数引数 api_key を優先し、未指定時は環境変数 OPENAI_API_KEY を参照します。未設定時は ValueError が発生します。
- 環境変数名（主なもの）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL, KABUSYS_DISABLE_AUTO_ENV_LOAD
- DB 書き込みは可能な限り冪等性（DELETE→INSERT、ON CONFLICT 相当）を保つ設計になっています。部分失敗時に既存データを不必要に削除しないよう配慮されています。
- ルックアヘッドバイアス対策:
  - 各解析関数は内部で datetime.today()/date.today() を直接参照せず、必ず target_date を明示して計算します。
- DuckDB バインディングの互換性注意:
  - executemany に空リストを渡せないバージョン（DuckDB 0.10 等）を考慮した記述があります。

既知の制約 / 今後の改善候補
- OpenAI レスポンスの堅牢性向上（より詳細な検証、スキーマ検証など）。
- ETL の品質チェック結果に基づくアラート / 自動復旧フローの強化。
- 大量データ処理時のパフォーマンス検証（DuckDB クエリ最適化、インデックス等）。

以上がソースコードから推測して作成した CHANGELOG（初期リリース 0.1.0）です。追加で強調したい点や日付・リリースノートの修正希望があれば指示してください。