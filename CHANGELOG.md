# Changelog

すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog のフォーマットに従っています。  

注: 以下の履歴はリポジトリ内のソースコードから機能・設計意図を推測して作成した初期リリース向けの変更説明です。

## [0.1.0] - 2026-03-31

### 追加
- パッケージ初期リリース "kabusys" を追加。
  - パッケージ公開情報: src/kabusys/__init__.py にて __version__ = "0.1.0"。
  - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ でエクスポート。

- 環境設定管理
  - 環境変数・.env ファイルの自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を読み込む（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パーサは export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い等に対応。
    - OS 環境変数の上書きを防ぐ protected キーの概念を導入。
  - Settings クラスを提供し、アプリケーションで使う設定プロパティを明示（J-Quants トークン、kabu API、Slack、DB パス、環境モード、ログレベル等）。
    - KABUSYS_ENV と LOG_LEVEL の妥当性チェックを備える。
    - is_live / is_paper / is_dev のユーティリティプロパティを追加。

- AI（自然言語処理・レジーム判定）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）:
    - raw_news / news_symbols を集約し、銘柄ごとのニュースを結合して OpenAI（gpt-4o-mini）の JSON mode で一括評価。
    - バッチ処理（最大20銘柄）・記事数と文字数のトリム（上限設定）・レスポンスバリデーション・スコアの ±1.0 クリッピング。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライとフォールバック（失敗時は該当チャンクをスキップし継続）。
    - calc_news_window による JST ウィンドウ計算（前日15:00～当日08:30 JST に対応、UTC naive datetime で返却）。
    - パブリック API: score_news(conn, target_date, api_key=None) — ai_scores テーブルへ書き込み、成功した銘柄数を返す。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）:
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出しのリトライ・エラーハンドリング・JSON パース防御を実装。API 失敗時はマクロセンチメントを 0.0 とするフェイルセーフ。
    - DuckDB に対する冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理を実装。
    - パブリック API: score_regime(conn, target_date, api_key=None) — market_regime テーブルへ書き込み。

- データ処理・研究機能
  - データ ETL インターフェース（src/kabusys/data/pipeline.py / etl.py）:
    - ETLResult データクラスを実装し、ETL 実行結果（取得数、保存数、品質問題、エラー）を集約。
    - 差分更新、バックフィル、品質チェック方針に沿ったユーティリティ関数を提供（テーブル存在チェック、最大日付取得など）。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）:
    - market_calendar を基にした営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - J-Quants からのカレンダー差分取得および夜間更新ジョブ calendar_update_job を実装。バックフィルと健全性チェックあり。
    - カレンダーデータが不完全な場合の曜日ベースのフォールバックをサポート。
  - リサーチ用ファクター計算（src/kabusys/research/*）:
    - calc_momentum / calc_value / calc_volatility（prices_daily / raw_financials に基づく複数の定量ファクター）。
    - feature_exploration: calc_forward_returns（複数ホライズン対応）、calc_ic（スピアマン順位相関による IC）、factor_summary（統計サマリー）、rank（平均ランク対応）。
    - zscore_normalize は data.stats から再エクスポート。
    - 全体設計として DuckDB 接続のみを受け外部 API に依存しないことを明記。

### 変更（設計方針・安全機構）
- ルックアヘッドバイアス回避:
  - AI モジュール・リサーチモジュール等で datetime.today() / date.today() を直接参照せず、すべて呼び出し元から渡される target_date を基準に処理する設計を採用。
  - DB クエリでは target_date 未満 / 以前といった排他条件を明確化。
- DB 書き込みの冪等性確保:
  - ai_scores / market_regime 等の書き込みで DELETE→INSERT、トランザクション（BEGIN/COMMIT/ROLLBACK）を用いた冪等更新を行う。
  - 部分失敗時に既存データを不必要に削除しない（書き込みコードの絞り込み）。
- OpenAI 呼び出しの耐障害性向上:
  - JSON パース失敗や余分なテキスト混入に対する復元処理、数値検証、未知の銘柄コードの無視等を実装。
  - リトライは 429 / ネットワーク断 / タイムアウト / 5xx に限定し、その他はスキップして継続するフェイルセーフ挙動。
- .env パーサの堅牢化:
  - export プレフィックス対応、クォート内のエスケープ処理、インラインコメントの取り扱いなどを細かく処理。
  - ファイル読み込み失敗時は警告を出して処理を継続。

### 修正（挙動改善 / 安全対策）
- DuckDB 互換性配慮:
  - executemany に空リストを渡すと失敗する点への対処（空チェックを追加）。
  - list 型バインドの不安定さを避けるため DELETE を複数行で実行する方法を採用。
- ログ出力の充実:
  - 各処理で info/debug/warning を適切に出力し、失敗時に原因を追跡しやすくした。
  - ROLLBACK 失敗時の警告ログなど、安全性に関するログを追加。

### 未実装 / 注意点
- strategy, execution, monitoring パッケージの実装は（このリリース時点では）ソースコード外に明示されており、実装の詳細は今後のリリースで補足予定。
- PBR・配当利回りなど Value ファクターの一部は未実装で将来拡張予定。
- OpenAI API の使用には OPENAI_API_KEY が必要。score_news/score_regime は api_key 引数または環境変数 OPENAI_API_KEY を参照する。

### セキュリティ
- .env 自動ロード時に OS 環境変数を保護するための protected キーセットを導入（既存の環境変数を上書きしないデフォルト挙動）。
- 機密情報（各種トークン）は Settings の必須プロパティを通じて明示的に要求し、未設定時は ValueError を発生させる。

---

今後のリリースでは、運用用のモニタリング・自動売買ロジック（strategy / execution）、テストカバレッジやドキュメントの拡充、追加ファクターや品質チェック機能の強化を予定しています。