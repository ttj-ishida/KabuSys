# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを使用します。

一覧:
- [Unreleased]
- [0.1.0] - 2026-03-31

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31

### Added
- 基本パッケージ初期実装
  - パッケージメタ情報: kabusys.__version__ = 0.1.0、公開サブパッケージとして data, strategy, execution, monitoring を定義。

- 環境変数 / 設定管理 (kabusys.config)
  - .env および .env.local を自動読み込みする仕組みを導入（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーの実装（コメント、export プレフィックス、シングル/ダブルクォートとエスケープ処理、インラインコメントの扱い等を考慮）。
  - Settings クラスを実装し、アプリケーションで使用する設定値を集中管理:
    - J-Quants / kabuステーション / Slack / DB（DuckDB/SQLite）パス / 監視閾値 / 環境（development/paper_trading/live） / ログレベル 等のプロパティを提供。
    - 必須キー未設定時に明示的な ValueError を送出する _require() を採用。
    - env, log_level に対する入力検証を実装（許容値チェック）。

- AI モジュール群
  - kabusys.ai.news_nlp
    - score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini, JSON Mode）で銘柄ごとのセンチメント（ai_score）を算出して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を calc_news_window として提供。
    - API 呼び出しのバッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、トークン膨張対策（記事数・文字数上限）、再試行（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）を実装。
    - レスポンス検証ロジック（JSON 抽出、results 配列と要素検証、スコア数値・有限性チェック、±1.0 でクリップ）。
    - DuckDB に対する idempotent な書き込み（DELETE → INSERT、executemany の空リスト回避）を実装。
    - フェイルセーフ設計: API 失敗やパース失敗は個別チャンクをスキップし、全体処理を継続。

  - kabusys.ai.regime_detector
    - score_regime: ETF 1321（TOPIX 日経225連動型 ETF）の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを組み合わせて市場レジーム（bull/neutral/bear）を日次判定し market_regime テーブルへ冪等書き込みする処理を実装。
    - マクロニュース抽出（キーワードベース）、LLM 呼び出し（JSON Mode）、リトライ/バックオフ、API エラー時のフォールバック（macro_sentiment=0.0）を実装。
    - ma200_ratio 計算はルックアヘッドバイアスを避けるため target_date 未満のデータのみ参照し、データ不足時は中立（1.0）を返す。
    - OpenAI クライアント呼び出しはモジュール単位で独立実装（モジュール結合を避ける設計）。

  - kabusys.ai.__init__
    - score_news を公開 API としてエクスポート。

- データプラットフォーム関連 (kabusys.data)
  - calendar_management
    - JPX マーケットカレンダー管理と営業日ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等のユーティリティを提供。
    - market_calendar が未取得の場合は曜日ベースでフォールバック（土日を非営業日扱い）。
    - calendar_update_job にて J-Quants から差分取得 → 冪等保存（ON CONFLICT 相当）を行うフローを実装。バックフィル、健全性チェック（future days の閾値）を含む。
    - DB に不整合（NULL 等）があった場合のログ出力とフォールバックを実装。

  - pipeline / etl
    - ETLResult dataclass を導入し、ETL 実行結果（取得数/保存数/品質問題/エラー等）を表現。
    - pipeline と etl の内部ユーティリティで DuckDB テーブル存在確認や最大日付取得などを実装（差分更新、backfill、品質チェックの想定設計を含む）。
    - data.etl で ETLResult を再エクスポート。

- 研究（Research）モジュール (kabusys.research)
  - factor_research
    - calc_momentum: 約1M/3M/6M リターン、200 日 MA 乖離の算出（prices_daily 参照、データ不足ハンドリング）。
    - calc_volatility: 20 日 ATR（true range の算出方法含む）、相対 ATR、20 日平均売買代金、出来高比率等の算出。
    - calc_value: raw_financials と prices_daily を組み合わせて PER, ROE を計算（最新財務レコードの取得ロジックを含む）。
    - DuckDB 上のウィンドウ関数や行数条件によりデータ不足時に None を返す堅牢な実装。
  - feature_exploration
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）での将来リターン計算。ホライズン検証（正の整数・閾値）あり。
    - calc_ic: スピアマンのランク相関を実装（欠損除外、十分サンプルがなければ None）。
    - rank: 同順位の平均ランク処理（丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ機能。
  - research.__init__ で主要関数をエクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY からも解決する設計。未設定時は明示的な例外を発生させる。

### Implementation / Design notes
- ルックアヘッドバイアス対策: 各種処理で datetime.today() / date.today() に依存せず、必ず外部から target_date を受け取る設計。
- DuckDB 互換性: executemany の空リスト回避や日付型ハンドリングのユーティリティを実装。
- 冪等性: DB 書き込みは可能な限り冪等（DELETE → INSERT、ON CONFLICT 相当）を意識して実装。
- フェイルセーフ: 外部 API 失敗は基本的にフェイルセーフ（スコア = 0 やチャンクスキップ）で処理継続する方針。
- ロギング: 各処理に詳細な logger メッセージを追加し、失敗時の診断を容易に。

---

注: 本 CHANGELOG はソースコードから推測して作成しています。実装の詳細や未掲載ファイル（例: jquants_client, quality, data.stats 等）の具体的な振る舞いに依存する部分は省略または要約されています。必要であれば特定モジュールごとにさらに詳細な変更点を生成します。