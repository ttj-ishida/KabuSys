CHANGELOG
=========

すべての変更点は「Keep a Changelog」形式に準拠して記載しています。  
日付はリリース日（ローカル開発の初期リリース想定）です。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-03
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ公開用のトップレベル定義を追加（src/kabusys/__init__.py）。
    - __version__ = "0.1.0"
    - __all__ に data, strategy, execution, monitoring を含める。

- 環境設定・ローディング機能（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能を実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して決定（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env のパースで export プレフィックス、クォート文字、エスケープ、インラインコメント等に対応。
    - 既存 OS 環境変数を保護するため protected キーセットを導入し、override 挙動を制御。
  - Settings クラスを提供し、環境変数から各種設定を取得
    - J-Quants / kabuステーション / LINE / DB パス（DuckDB/SQLite）/監視設定（PID/KILL フラグ/閾値）/システム環境（env, log_level）等をプロパティとして公開。
    - 必須環境変数未設定時は明確な ValueError を投げる（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - KABUSYS_ENV の検証（development/paper_trading/live のみ許容）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

- AI モジュール（src/kabusys/ai/）
  - ニュースNLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄毎に記事を結合して OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信。
    - バッチサイズ、1銘柄あたり記事数・文字数上限、ウィンドウ計算（JST基準 → UTC比較用）を実装。
    - 429/ネットワーク断/タイムアウト/5xx は指数バックオフでリトライ、その他はスキップのフェイルセーフ設計。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code と score の検証、スコアのクリップ）。
    - 成功分のみ ai_scores テーブルへ冪等的に置換（DELETE → INSERT）して部分失敗時に既存スコアを保護。
    - API キーは関数引数で注入可能（テスト容易性）、未設定時は環境変数 OPENAI_API_KEY を参照してエラーを送出。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はキーワードベース（日本語・英語のマクロ用キーワードリスト）でタイトルを取得し、OpenAI に JSON 出力を要求。
    - LLM 呼び出しは専用の内部実装を持ち、リトライ（RateLimit, 接続, タイムアウト, 5xx）とバックオフ処理を実装。失敗時は macro_sentiment=0.0 でフォールバック。
    - レジームスコアの合成と閾値によるラベリング、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - ルックアヘッドバイアス回避のため target_date 未満のデータのみを参照し、date.today() を直接参照しない設計。

- Research モジュール（src/kabusys/research/）
  - factor_research.py
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離を計算（欠損時は None）。
    - ボラティリティ/流動性: 20 日 ATR、相対ATR、20 日平均売買代金、出来高比率を計算。
    - バリュー: raw_financials から直近報告を参照し PER（EPS が有効な場合）、ROE を計算。
    - DuckDB を用いた SQL ベース実装。計算結果は (date, code) をキーとする dict のリストで返却。
  - feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズンの検証、horizons の検証あり）。
    - IC（Information Coefficient）計算（Spearman のランク相関）calc_ic。
    - ランク変換ユーティリティ rank（同順位を平均ランクで扱う）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。
    - パンダス等外部依存を避けた純標準ライブラリ実装。

- Data モジュール（src/kabusys/data/）
  - calendar_management.py
    - market_calendar テーブルを扱うユーティリティ群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（平日=営業日）。
    - 次/前営業日の探索で最大探索幅を設定して無限ループを防止。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等更新。バックフィル日数・健全性チェックを実装。
    - jquants_client へのインタフェース経由での取得/保存を想定。
  - pipeline.py / ETLResult（src/kabusys/data/pipeline.py, etl.py）
    - ETLResult データクラスを公開（ETL 実行結果の集約、品質問題・エラー一覧を保持）。
    - ETL パイプライン設計方針（差分取得、backfill、品質チェック継続、id_token 注入可能）を実装方針として反映。
    - DuckDB のテーブル存在チェックや最大日付取得などのユーティリティを整備。

Changed
- 設計上の注意（全体）
  - ルックアヘッドバイアス防止のため、各処理は target_date を明示的に受け取り、datetime.today()/date.today() の直接参照を避ける（テスト可能性とバックテスト整合性向上）。
  - OpenAI への呼び出しとレスポンスパースは各モジュールで独立実装（モジュール間で内部関数を共有しない設計）してテスト容易性と結合度低減を図る。
  - API 呼び出し失敗は基本的に例外で上位処理を止めない（フェイルセーフ）、ただし必須パラメータ未設定時は ValueError を投げる。

Fixed
- N/A（初回リリース）

Security
- 環境変数読み込み時、既存 OS 環境変数は保護される（protected set）ため、.env による上書きからシステム環境変数を守る実装。
- 必須の秘密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY）は明示的に要求し、未設定時はエラーを発生させる。

Compatibility
- DuckDB を利用するため、DuckDB 接続オブジェクト（DuckDBPyConnection）が必要。
- OpenAI の Python SDK（OpenAI クライアント）を利用。モデル指定は gpt-4o-mini（JSON Mode）を想定。
- Python 3.10+ を想定（型注釈の union | 演算子等）。

Migration notes
- 既存の .env 運用者は .env/.env.local の読み込み優先順位に注意してください（OS 環境変数 > .env.local > .env）。
- 自動ロードを無効化したいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Acknowledgements / Notes
- 各モジュール内に多くの設計コメントとフェイルセーフ処理が含まれており、テスト用に API 呼び出しポイントをモック差し替え可能な構造になっています（例: kabusys.ai.news_nlp._call_openai_api のパッチ）。
- 今後のリリースで以下が想定されます:
  - monitoring / execution / strategy の具体的実装の追加（現在は __all__ で公開されているが実装の分割・拡張の余地あり）。
  - より詳細な品質チェックルールの追加と UI/ダッシュボード連携。