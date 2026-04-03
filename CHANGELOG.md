# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-03

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - パッケージの公開 API を整理（data, strategy, execution, monitoring を __all__ に公開）。

- 設定・環境管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントに対応。
    - ファイル読み込み失敗時は警告を発行してフォールバック。
    - 既存 OS 環境変数を保護する `protected` 機構を実装（.env.local の override 時など）。
  - Settings クラスを実装し、アプリケーション設定をプロパティで提供。
    - J-Quants / kabuStation / LINE / DB / 監視設定などの主要設定を取得するプロパティを用意。
    - 一部必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は未設定時に ValueError を送出。
    - KABUSYS_ENV, LOG_LEVEL の値検証（許容値のチェック）を実装。
    - DB パス・PID/kill flag パス・閾値（CPU/メモリ/ディスク）などのデフォルトを提供。

- データプラットフォーム (src/kabusys/data)
  - calendar_management
    - JPX カレンダー管理モジュールを実装。
    - market_calendar の有無に応じた振る舞い（DB 登録値優先、未登録日は曜日ベースのフォールバック）を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の営業日判定ユーティリティを提供。
    - 夜間バッチ更新 job (calendar_update_job) を実装し、J-Quants から差分取得 → 冪等保存（ON CONFLICT を想定）を実現。
    - 最大探索日数上限（_MAX_SEARCH_DAYS）やバックフィル・健全性チェックを実装して無限ループや極端な異常を防止。
  - pipeline / ETL
    - ETL パイプライン向けの ETLResult データクラスを実装。
      - ETL の取得/保存件数、品質チェック結果、エラー概要の収集機能を提供。
      - has_errors / has_quality_errors / to_dict 等のユーティリティメソッドを実装。
    - ETL の設計方針（差分更新、バックフィル、品質チェックの扱い、id_token 注入など）をコードに反映。
  - etl モジュールで ETLResult を再エクスポート（public API）。

- AI（自然言語処理） (src/kabusys/ai)
  - news_nlp モジュール
    - raw_news + news_symbols をソースに、銘柄ごとのニュースセンチメントを OpenAI（gpt-4o-mini, JSON mode）で評価する処理を実装。
    - タイムウィンドウ（JST 基準）計算（calc_news_window）。
    - 銘柄ごとに記事を集約し（最大記事数・文字数でトリム）、最大 20 銘柄ずつのバッチ送信を行う設計。
    - レスポンスのバリデーションを厳格化（JSON 抽出、"results" の検証、コード照合、数値変換、有限性チェック）。
    - スコアは ±1.0 にクリップ。API エラーやパース失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - 429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフでリトライ（最大回数制御）。
    - DuckDB の executemany の空リスト制約への対処（空のときは実行をスキップ）。
  - regime_detector モジュール
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）と、マクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは raw_news からマクロキーワードで抽出し、OpenAI により JSON レスポンスで macro_sentiment を取得。
    - レジームスコアの合成・クリップ・閾値判定を実装。
    - market_regime テーブルへの冪等書き込み（BEGIN → DELETE → INSERT → COMMIT）とロールバック処理を実装。
    - API 呼び出し失敗時は macro_sentiment=0.0 のフェイルセーフ、API 呼び出し単体のリトライ/バックオフを実装。
    - モジュールはルックアヘッドバイアスを避ける設計（date.today()/datetime.today() を参照しない、クエリは date < target_date など）。

- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research
    - モメンタム (calc_momentum): 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
      - データ不足（200 行未満）の場合は None を返す。
    - ボラティリティ/流動性 (calc_volatility): 20日 ATR（true range の扱いに注意）、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - バリュー (calc_value): raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0 または欠損の場合は None）。
    - DuckDB を活用した SQL ベース計算で外部 API へのアクセスは行わない設計。
  - feature_exploration
    - 将来リターン calc_forward_returns を実装（任意ホライズン対応、horizons の検証）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関）。
    - ランク変換ユーティリティ rank（同順位は平均ランク、丸め誤差対策あり）。
    - factor_summary：各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージで主要関数を再エクスポート（研究用 API を簡潔に提供）。

- その他
  - 全体的に DuckDB を中心とした設計（DuckDB 接続を引数に取る関数が主）。
  - ロギングを多用し、重要な分岐・警告・情報を出力することで障害対応を容易に。
  - ルックアヘッドバイアス対策を多くのモジュール設計に反映（time.now を直接参照しない等）。
  - OpenAI クライアント呼び出しは各モジュールで独立実装し、テスト時のパッチ差し替えを想定（private helper をモジュール内に保持）。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。ただし以下の互換性考慮を反映：
  - DuckDB の executemany に空リストを渡せない点への対処を実装（空の場合はスキップ）。
  - OpenAI SDK の例外型差異（status_code の取り扱い）に対する安全な判定処理を導入。

### 既知の制約 / 注意事項 (Notes)
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を発生させる。
- AI モジュールは gpt-4o-mini、JSON Mode を前提にプロンプト設計しているため、モデルやレスポンスフォーマットが変わると調整が必要。
- calendar_update_job / ETL 周りは外部 J-Quants クライアント（jquants_client）に依存するため、本体の動作にはクライアント実装が必要。
- 初期リリースでは PBR・配当利回りなど一部バリューファクターは未実装。

### ブレイキングチェンジ (Breaking Changes)
- 初版リリースのため該当なし。今後のバージョンで API 変更を行う場合は明示します。

---

将来のリリースではユニットテスト、ドキュメント（Usage examples）、CI/CD 設定、さらに詳細な品質チェックと可観測性の向上（メトリクス、トレース）を計画しています。ご要望や不具合報告は issue を立ててください。