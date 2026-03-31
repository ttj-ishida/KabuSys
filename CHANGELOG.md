# Keep a Changelog — CHANGELOG.md（日本語）

すべての変更は Keep a Changelog の形式に従って記載します。  
バージョニングは SemVer を想定しています。

## [0.1.0] - 2026-03-31

初回リリース。以下の主要機能・モジュールを追加しました。

### 追加 (Added)
- パッケージメタ情報
  - pakage version を `kabusys.__version__ = "0.1.0"` として定義。
  - パッケージ公開 API を `__all__ = ["data", "strategy", "execution", "monitoring"]` で想定。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - プロジェクトルート特定は `.git` または `pyproject.toml` を起点に探索し、CWDに依存しない実装。
    - OS 環境（既存の os.environ）を保護する `protected` 機構を導入。
  - `.env` パーサーの強化:
    - `export KEY=val` 形式対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理。
    - インラインコメントやコメント扱いのルール（クォートの有無による判定）。
  - `Settings` クラスでアプリケーション設定をプロパティとして提供。
    - J-Quants / kabuステーション / Slack / DB パス / 環境切替（development/paper_trading/live）/ログレベル等の設定を取得。
    - 必須項目は `_require` により未設定時に ValueError を送出。

- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news と news_symbols をソースにして銘柄ごとのニュースセンチメントを算出し、`ai_scores` テーブルへ保存する機能を実装。
    - 処理設計:
      - JST 基準の時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC に変換してクエリ（calc_news_window）。
      - 銘柄ごとに最新 N 件（デフォルト最大 10 記事、文字数上限 3000）を集約して LLM に渡す。
      - バッチ処理（1 API 呼び出しで最大 20 銘柄）で OpenAI の gpt-4o-mini（JSON mode）を利用。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
      - レスポンスのバリデーション（JSON 抽出、results リスト、code の整合、数値チェック）とスコアの ±1.0 クリップ。
      - DuckDB の executemany の制約に配慮し、部分失敗時に既存データを保護するために DELETE（コードごと）→ INSERT の順で冪等書き込みを実施。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。API キー未設定時は ValueError。
    - テスト容易性: OpenAI 呼び出しをモック可能（_call_openai_api を patch）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して
      日次で market_regime テーブルへレジーム（bull/neutral/bear）を保存する機能を実装。
    - 処理設計:
      - DuckDB から過去データのみを参照（ルックアヘッドバイアス防止、target_date 未満のデータのみ使用）。
      - マクロニュースは news_nlp 側の calc_news_window で算出されたウィンドウから抽出し、OpenAI（gpt-4o-mini）でセンチメント評価。
      - OpenAI API の失敗は macro_sentiment = 0.0 にフォールバック（例外を上げず続行）。
      - レジームスコアは clip して閾値判定、DB へは BEGIN / DELETE / INSERT / COMMIT で冪等に保存。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。API キー未設定時は ValueError。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。
      - J-Quants API から差分取得し market_calendar テーブルへ冪等保存（save_market_calendar を jquants_client 経由で呼出し）。
      - バックフィル（日数）・先読み日数・健全性チェック（将来日付が過度に大きい場合はスキップ）を実装。
    - 営業日ユーティリティ関数:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
      - DB にデータがない・NULL が混在する場合は曜日ベースのフォールバック（週末を休業）を一貫して採用。
      - 探索は _MAX_SEARCH_DAYS（安全上の上限）で制限。
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを提供（取得数・保存数・品質問題・エラーの収集 / to_dict 変換等）。
    - 差分更新ロジック（最終取得日に基づく差分フェッチ、バックフィル）や品質チェックの呼び出し方針を想定。
    - DuckDB テーブルの存在チェックや最大日付取得ユーティリティを実装。

- 研究用モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum, Volatility, Value 等の定量ファクターを DuckDB の prices_daily / raw_financials テーブルから計算する関数を実装:
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None）。
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比。
      - calc_value: PER / ROE（raw_financials の最新レコードを利用）。
    - 設計方針として外部 API に依存せず、計算は SQL + Python で完結。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンランク相関（IC）を実装（有効レコードが 3 件未満の場合は None）。
    - rank: 同順位を平均ランクで扱うランク化ユーティリティ。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算する統計サマリ。

- ロギング / フェイルセーフ設計
  - 主要処理は失敗時に例外を上位へ伝播する場面と、API 失敗時にフェイルセーフ（スコア 0.0 にフォールバック）で継続する場面を明確に分離。
  - DuckDB のトランザクションで失敗時に ROLLBACK を試行し、ROLLBACK に失敗した場合は警告ログを出力する実装。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キー等の秘密情報は環境変数から取得する設計。必要なキーが未設定の場合は明示的にエラー（ValueError）を返すため、誤操作での秘密情報流出リスクは低減。

### 既知の制約 / 備考 (Notes & Known limitations)
- OpenAI を使用する処理（score_news / score_regime）は API キーが必須。キー未設定時は ValueError を送出する。
- DuckDB の挙動やバインド処理の違い（executemany で空リストを渡せない等）を考慮した実装になっているため、DuckDB の特定バージョンでの制約に依存する箇所がある。
- 時刻は基本的に naive な datetime / date（タイムゾーン混入を意図的に避ける）で扱う設計。news ウィンドウの計算は JST をベースに UTC 変換している。
- news_nlp / regime_detector の OpenAI 呼び出しはモジュール単位で独立しており、テスト時にはそれぞれの _call_openai_api をモックして差し替えることを想定。
- monitoring / execution / strategy 等のサブパッケージは __all__ に含まれているが、本リリースにおいては上記で列挙したコア機能に注力している。

---

今後のリリースでは、使いやすさ向上のための CLI、CI/テストカバレッジ強化、モニタリング周りの実装（Slack 通知等）、および strategy/execution の統合を予定しています。