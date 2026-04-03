# Changelog

すべての注目すべき変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0

※このファイルは、リポジトリ内コードからの機能・設計の抜粋に基づいて作成した推測的な変更履歴です。

## [0.1.0] - 2026-04-03

初回リリース。日本株自動売買・データプラットフォームのコア機能を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"、__all__ 定義）。
  - モジュール階層（data, research, ai, monitoring, execution, strategy 等のエントリポイント）を公開。

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途）。
    - プロジェクトルートの検出は .git または pyproject.toml を基準にしており、CWD に依存しない方式。
  - .env パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
  - 環境変数上書き制御（override フラグ）と OS 環境変数保護（protected set）。
  - Settings クラスを提供し、アプリケーションで必要な設定をプロパティ経由で取得（J-Quants / kabu ステーション / LINE / DB パス / 監視閾値 / ログレベル 等）。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値を限定、無効値は ValueError）。
    - デフォルトの DB パス（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）など。

- AI モジュール（OpenAI 統合）
  - ニュースセンチメント（銘柄単位）計算モジュール `kabusys.ai.news_nlp`
    - raw_news と news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへ保存。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換。calc_news_window 実装）。
    - バッチ処理（最大 20 銘柄 / コール）、1 銘柄あたりの最大記事数・最大文字数制限（トリム）。
    - JSON Mode を前提としたレスポンス処理と堅牢なバリデーション（results キー、code/score 検証、スコアの ±1.0 クリップ）。
    - エラー耐性: 429・ネットワーク断・タイムアウト・5xx は指数バックオフで再試行。その他はスキップして継続。API 呼び出し部はテストで差し替え可能（_call_openai_api を patch 可能）。
    - DuckDB に対する書き込みは「取得成功した銘柄のみを置換（DELETE → INSERT）」することで部分失敗時の既存データ保護。
    - DuckDB の executemany 空リスト制約に対応した実装上の注意（空リスト時には実行しない）。
  - 市場レジーム判定モジュール `kabusys.ai.regime_detector`
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - マクロニュースは raw_news からマクロキーワードで抽出し、OpenAI（gpt-4o-mini）で JSON レスポンスを期待してスコア化。
    - レジームスコア合成は clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1) を採用。閾値によるラベル付け（BULL/BEAR/NEUTRAL）。
    - API 失敗時は macro_sentiment = 0.0（フェイルセーフ）。DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）を行い、失敗時は ROLLBACK。
    - API 呼び出しは news_nlp と独立した実装でモジュール間の結合を低減。OpenAI API キーは引数または OPENAI_API_KEY 環境変数から解決。

- データプラットフォーム (`kabusys.data`)
  - マーケットカレンダー管理 (`calendar_management`)
    - market_calendar テーブルを使用した営業日判定関数群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データがない場合は曜日ベースのフォールバック（週末を非営業日扱い）。DB にある場合は DB 値を優先。未登録日はフォールバックで一貫した結果を返す。
    - calendar_update_job を実装（J-Quants client を用いて差分取得、バックフィル、健全性チェック、冪等保存）。
    - 探索範囲制限（最大検索期間 _MAX_SEARCH_DAYS）やバックフィル、未来日付の健全性チェックを実装。
  - ETL パイプライン (`pipeline`, `etl`)
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラーを集約）。
    - 差分更新、保存（jquants_client の save_* を利用して冪等保存）、品質チェック（quality モジュール）を想定したインターフェースを実装。
    - デフォルトのバックフィル日数、カレンダー先読みなどの設定を定義。
    - ETL 実行結果の辞書化（to_dict）で品質問題をシリアライズ可能。

- リサーチ機能 (`kabusys.research`)
  - ファクター計算 (`factor_research`)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB SQL を利用して計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の挙動（所定行数未満は None）やスキャン範囲バッファを設計。
    - 出力は date, code を含む辞書リスト形式。
  - 特徴量探索 (`feature_exploration`)
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - calc_forward_returns は任意ホライズンを受け付け、入力検証（正の整数かつ <= 252）を行う。
    - calc_ic は Spearman（ランク）相関を手動で計算し、データ不足（有効レコード < 3）時は None を返す。
    - rank は同順位の平均ランクを返す実装（浮動小数の丸めによる tie を軽減）。
    - factor_summary は count/mean/std/min/max/median を計算し、None 値を除外。

### 変更 (Changed)
- 設計原則の明確化
  - 主要な分析・スコアリング処理はルックアヘッドバイアス回避のために date.today() や datetime.today() を直接参照しない設計を採用（すべて target_date を明示受け渡し）。
  - OpenAI 呼び出しに関するテスト容易性を考慮し、内部呼び出しを patch 可能にしている（ユニットテスト用フック）。

### 修正 (Fixed)
- 実装上の耐障害性を強化
  - OpenAI API の各種エラー（429, ネットワーク断, タイムアウト, 5xx 等）に対して再試行とフォールバックを追加し、処理継続性を確保。
  - DuckDB 固有の制約（executemany に空リストを渡せない）に対応した分岐を追加。

### 注意点 / 互換性 (Notes)
- DuckDB に依存する SQL 実装が多いため、実行環境の DuckDB バージョンにより挙動が影響を受ける可能性がある（特に配列バインドや executemany 周り）。
- OpenAI API（gpt-4o-mini）を利用するため、API キーの設定（api_key 引数または環境変数 OPENAI_API_KEY）が必須。
- .env パーシングはかなり寛容だが、特殊ケースのパース結果は .env.example を参照して検証することを推奨。
- calendar_update_job / ETL などのジョブは外部 API（J-Quants クライアント）に依存しており、API 例外時はログ出力のうえ 0 を返すフェイルセーフ挙動をとる。

---

以上がこのコードベースから推測した初回リリース（0.1.0）の主な変更点・実装内容です。必要であれば、各機能ごとにもう少し詳細な説明（例: 各関数の戻り値例、SQL の抜粋説明、設定名の一覧など）を追加できます。どのレベルの詳細を望みますか？