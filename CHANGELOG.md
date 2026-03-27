# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトはセマンティックバージョニングに従います。  

## [0.1.0] - 2026-03-27

初回リリース。

### 追加
- パッケージ基本情報
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - __all__ に data, strategy, execution, monitoring を公開（将来の拡張を想定）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数を自動読み込み（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動読み込みを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env 行パーサ実装（コメント、export 形式、クォート・エスケープ対応）。
  - Settings クラスを提供し、以下のプロパティで設定値を取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL（検証）
    - is_live / is_paper / is_dev のヘルパー

- AI モジュール (src/kabusys/ai)
  - ニュース解析・スコアリング: score_news を公開（src/kabusys/ai/news_nlp.py）。
    - OpenAI (gpt-4o-mini) を用いたニュースセンチメント解析。
    - 対象時間ウィンドウ計算（前日15:00 JST ～ 当日08:30 JST に対応、UTC に変換して DB 参照）。
    - 銘柄ごとに記事を集約し、1銘柄につき最大記事数・文字数でトリム。
    - バッチ処理（1回最大 20 銘柄）で API 呼び出し。
    - API エラー（429/ネットワーク/タイムアウト/5xx）は指数バックオフでリトライ。
    - レスポンスのバリデーション（JSON 抽出、results リスト、code と score の検証）。
    - スコアは ±1.0 にクリップ。取得成功分のみ ai_scores テーブルへ置換（DELETE → INSERT、部分失敗で既存スコアを保護）。
    - テスト用フック: _call_openai_api を unittest.mock.patch で差し替え可能。

  - 市場レジーム判定: score_regime を公開（src/kabusys/ai/regime_detector.py）。
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - ニュースウィンドウは news_nlp.calc_news_window を利用。
    - OpenAI 呼び出しは独自実装。API 失敗時は macro_sentiment = 0.0 でフォールバック（フェイルセーフ）。
    - 計算結果は market_regime テーブルに冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- データモジュール (src/kabusys/data)
  - ETL パイプラインの公開インターフェースとして ETLResult を再エクスポート（src/kabusys/data/etl.py）。
  - pipeline モジュール（src/kabusys/data/pipeline.py）:
    - 差分取得・保存・品質チェックを想定した ETLResult データクラスを実装。
    - DuckDB テーブルの最大日付取得やテーブル存在チェック等のユーティリティを提供。
    - 市場カレンダーの先読み / バックフィル、品質チェックの扱いに関する方針を文書化。
  - カレンダー管理（src/kabusys/data/calendar_management.py）:
    - market_calendar テーブルの管理、営業日判定ロジックを実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にデータがない場合は曜日ベース（土日除外）のフォールバックを行う一貫した挙動。
    - calendar_update_job を実装し、J-Quants API から差分取得 → 市場カレンダー保存（fetch/save は jquants_client 経由）。
    - バックフィル、健全性チェック、最大探索日数（_MAX_SEARCH_DAYS）等の安全対策を導入。

- 研究（Research）モジュール (src/kabusys/research)
  - factor_research モジュール（src/kabusys/research/factor_research.py）:
    - モメンタム、ボラティリティ、バリュー等の定量ファクター計算関数を実装:
      - calc_momentum: 1M/3M/6M リターン、ma200_dev（200日 MA 乖離）
      - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率
      - calc_value: PER、ROE（raw_financials から最新財務を取得）
    - DuckDB の SQL ウィンドウ関数を活用し、必要行数不足時は None を返す（データ不足保護）。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）:
    - calc_forward_returns: 将来リターン（任意ホライズン）を一括で取得する効率的なクエリ。
    - calc_ic: スピアマンランク相関（IC）を計算。サンプル数不足時は None。
    - rank: 同順位は平均ランクを割り当てるランク関数（浮動小数の丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを計算。
  - research.__init__ で主要関数を再公開。

### 仕様・設計上の重要点（注意点）
- ルックアヘッドバイアス防止
  - 多くの関数（score_news, score_regime, ETL 等）は内部で datetime.today() / date.today() を参照せず、明示的に渡された target_date のみを基準に処理する設計。
  - prices_daily クエリでは target_date 未満や半開区間を利用するなど、未来データ漏洩対策を行っている。

- OpenAI / LLM 呼び出し
  - gpt-4o-mini を想定し JSON Mode を使って厳密な JSON を期待するプロンプトを用意。
  - API エラー（429/ネットワーク/タイムアウト/5xx）は指数バックオフでリトライ。上限リトライを超えた場合はフォールバック（スコア 0.0 や処理スキップ）することで堅牢性を確保。
  - テスト容易性のため _call_openai_api をパッチしてレスポンスを差し替え可能。

- データベース（DuckDB）依存
  - 多数の処理が DuckDB に保存されたテーブル（prices_daily, raw_news, ai_scores, market_regime, news_symbols, raw_financials, market_calendar 等）を前提としている。
  - DuckDB 0.10 の executemany の制約（空リスト不可）を考慮した実装になっている（空リストのときは DB 操作をスキップ）。

- 環境変数と自動ロードの挙動
  - .env/.env.local を自動ロードするが、OS 環境変数は保護され、.env.local は .env を上書きする。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD が用意されている。
  - Settings.require 相当のプロパティは必須環境変数が未設定の場合に ValueError を発生させる。

### 修正 / 不具合対応
- 初回リリースのため無し。

### 非推奨
- 初回リリースのため無し。

### セキュリティ
- 環境変数（API キー等）は Settings 経由で参照する設計。OpenAI API キーは api_key 引数で注入可能（テストや一時的な上書きに利用）。
- .env 読み込み処理はファイル読み込みエラー時に警告を出して継続するため、誤ったファイル権限等が原因でクラッシュしない設計。

---

注: 本 CHANGELOG はソースコードの内容から推測して作成したものであり、実際の配布物やドキュメントに合わせて適宜更新してください。