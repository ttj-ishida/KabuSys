# Keep a Changelog 準拠 — CHANGELOG

すべての注目すべき変更をここに記載します。  
このファイルは Keep a Changelog の形式に従っています。意味的に推測した初期リリースの内容を日本語でまとめています。

全般的な設計方針（リリース全体に共通）
- DuckDB を内部データストアとして使用し、SQL＋Python の組合せでデータ処理を行う設計。
- 外部（実取引）API への不要なアクセスを避け、研究・集計ロジックは DB のみ参照する方針。
- ルックアヘッドバイアス防止のため、datetime.today()/date.today() を安易に参照しない実装。
- OpenAI 呼び出しは JSON Mode を用いた堅牢なレスポンス検証と、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
- API障害は基本的にフェイルセーフ（例: マクロセンチメントが取得できない場合は中立として続行）に設計。
- .env 自動読み込み機能と、テスト用に無効化する環境変数を提供。

## [0.1.0] - 2026-04-04
初期リリース

### 追加
- パッケージ基盤
  - kabusys パッケージ初期構成を追加。__version__ = "0.1.0"。
  - パブリックモジュール群のエクスポートを定義（data, strategy, execution, monitoring）。

- 設定・環境（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
  - .env パーサを実装（export 形式、シングル/ダブルクォート、エスケープ、コメント処理に対応）。
  - Settings クラスを実装し、アプリケーション設定をプロパティで提供。
    - J-Quants / kabu ステーション / LINE API / DB パス / 監視設定 / ログ・環境設定等を取得。
    - 必須環境変数の取得時は未設定で ValueError を発生させる _require を提供。
    - env/log_level のバリデーションを実装（許容値を制限）。

- AI モジュール（kabusys.ai）
  - news_nlp モジュール
    - raw_news と news_symbols からニュースを銘柄単位に集約し、OpenAI（gpt-4o-mini）で銘柄別センチメントを算出。
    - バッチ処理（最大 20 銘柄）、1銘柄あたりの記事数・文字数上限、JSON mode を用いた厳密なレスポンス検証を実装。
    - リトライ戦略（429・接続エラー・タイムアウト・5xx）とレスポンス検証（JSON 抽出、results 配列、コード照合、スコア数値化・クリップ）に対応。
    - ai_scores テーブルへ冪等的に書き込む（該当コードのみ DELETE → INSERT）。部分失敗時に既存スコアを保護。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
    - 公開関数: score_news(conn, target_date, api_key=None)
    - ニュースウィンドウ（JST）: 前日 15:00 ～ 当日 08:30（内部は UTC naive で扱う calc_news_window を提供）

  - regime_detector モジュール
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来の LLM マクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を決定。
    - prices_daily と raw_news からデータを取得、マクロニュースはキーワードでフィルタして最大 20 件まで LLM に投入。
    - OpenAI 呼び出しのリトライ・フェイルセーフ・JSON パース保護を実装。API 失敗時は macro_sentiment = 0.0 にフォールバック。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK を試行）。
    - 公開関数: score_regime(conn, target_date, api_key=None)

- Research（kabusys.research）
  - factor_research モジュール
    - モメンタム（1M/3M/6M のリターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER・ROE）等のファクター計算を実装。
    - DuckDB で効率的にウィンドウ関数を用いる SQL 実装。データ不足時は None を返す扱いを採用。
    - 公開関数: calc_momentum, calc_volatility, calc_value
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を提供。
    - IC はスピアマンのランク相関を自前で計算（ties は平均ランク処理）。
  - research パッケージは主要関数を __all__ で再エクスポート。

- Data プラットフォーム（kabusys.data）
  - calendar_management モジュール
    - JPX カレンダー管理、営業日判定ロジックと夜間バッチ更新（calendar_update_job）を実装。
    - market_calendar がない/不完全な場合の曜日ベースフォールバック、next/prev/get_trading_days の一貫性、最大探索日数による安全策を実装。
    - J-Quants クライアントを通じた取得・保存フロー（fetch_market_calendar / save_market_calendar）を想定。
  - pipeline / etl
    - ETLResult データクラスを定義（取得数・保存数・品質検査結果・エラー情報を含む）。
    - pipeline モジュール設計（差分取得、backfill、品質チェックの収集と継続処理）を実装方針として整備。
    - data.etl で ETLResult を再エクスポート。

### 変更（設計方針・実装上の注記）
- OpenAI 連携
  - gpt-4o-mini と JSON Mode を想定した実装。レスポンスが完全な JSON でなくても最外の {} を抽出して復元する保守性を持たせている。
  - ニュース NLP とレジーム判定で独立した _call_openai_api 実装を採用し、モジュール間でプライベート関数を共有しない設計（結合度低減）。
- DB 書き込み
  - 各種書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT を想定）し、部分失敗時に既存データを不必要に消さないよう配慮。
- フェイルセーフ
  - LLM/API の失敗はトレースログに残しつつ、処理を継続する（中立スコア/スキップ）実装で運用耐性を優先。

### 修正
- 初期リリースのため既知のバグ修正履歴はなし。

### セキュリティ
- 初期版の注意点:
  - OpenAI API キー等の機密情報は環境変数で管理。Settings._require により未設定時は明示的にエラー化する。
  - .env 読み込み時に既存 OS 環境変数を上書きしない既定挙動（override=False）を採用し、意図しない上書きを防止。
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意。

---

注記:
- 本 CHANGELOG は提供されたコードベースの構造・コメント・実装内容から推測して作成しています。実際のリリースノートや変更履歴として利用する場合は、実際のコミット履歴やリリース計画と照合してください。