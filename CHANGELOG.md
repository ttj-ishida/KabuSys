# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の慣例に沿って記載しています。

最新: Unreleased は特にありません — 初期リリースを以下にまとめます。

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買システム「KabuSys」のコア機能を含む最初の公開バージョン。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報: src/kabusys/__init__.py にてバージョン "0.1.0" を定義。公開モジュールは data, strategy, execution, monitoring を想定。

- 環境設定/ロード機能（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能を実装（読み込み順: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して行い、CWD に依存しない実装。
  - .env のパースは export 形式、クォート内のエスケープ、コメント処理（クォートあり/なしでの取り扱い）に対応。
  - 自動読み込みを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供（J-Quants, kabu API, Slack, DB パス, 監視閾値, 環境（development/paper_trading/live）, ログレベルの検証などのプロパティを持つ）。
  - 必須環境変数検出時の明確なエラーメッセージを実装（_require）。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）でセンチメントを算出し、ai_scores テーブルへ書き込む。
  - ニュース収集ウィンドウ（JST 基準で前日 15:00 〜 当日 08:30）を calc_news_window() で計算。
  - 1 銘柄あたりの最大記事数・文字数を制限してトークン肥大化に対応（バッチ処理、_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
  - バッチ送信（最大 20 銘柄）・JSON Mode を利用したレスポンス検証とスコアクリッピング（±1.0）。
  - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。致命的な失敗時も処理を継続（フェイルセーフ）。
  - DuckDB への書き込みは冪等的に行う（DELETE → INSERT、部分失敗時に他銘柄の既存スコアを保護）。
  - テスト容易性のため OpenAI 呼び出し点をパッチ差し替え可能（_call_openai_api）。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルへ書き込む。
  - MA 計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを防止。
  - マクロニュースは raw_news からキーワードフィルタ（日本・米国等の経済ワード）で抽出し、LLM による -1.0〜1.0 のスコアを取得。
  - 合成スコアは重み付け（MA 70%、マクロ 30%）で算出し閾値で bull/neutral/bear を判定。
  - DB 書き込みはトランザクションで冪等（BEGIN / DELETE / INSERT / COMMIT）。OpenAI API 呼び出しの失敗時はマクロスコアを 0.0 にフォールバック。

- データ基盤：カレンダー管理（src/kabusys/data/calendar_management.py）
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日判定ユーティリティを提供。
  - market_calendar テーブルがない/未登録の場合は曜日ベース（平日のみ営業）でのフォールバックを採用。
  - 最大探索日数・先読み・バックフィル・健全性チェックの定数を定義し安全性を確保。
  - calendar_update_job: J-Quants API（jquants_client 経由）から差分取得し market_calendar を冪等的に更新。バックフィル実装とエラーハンドリングを備える。

- データ基盤：ETL パイプライン（src/kabusys/data/pipeline.py, etl.py）
  - ETLResult dataclass を導入し ETL 実行結果（取得数・保存数・品質問題・エラー）を構造化して返却。
  - 差分更新、バックフィル、品質チェック（quality モジュール想定）を設計方針として実装。
  - jquants_client を用いた安全な保存（Idempotent）を想定。
  - etl モジュールから ETLResult を再エクスポート（src/kabusys/data/etl.py）。

- リサーチ機能（src/kabusys/research/*）
  - factor_research:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離などのモメンタム系ファクターを計算。
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR、平均売買代金、出来高比などを算出。
    - calc_value(conn, target_date): raw_financials から EPS/ROE を使って PER/ROE を計算（PBR・配当利回りは未実装）。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons): 将来リターン（翌日/翌週/翌月等）を計算（LEAD を用いた単一クエリ実装）。
    - calc_ic(factor_records, forward_records, ...): スピアマンランク相関（IC）を計算。
    - factor_summary(records, columns): 各ファクターの基本統計量（count/mean/std/min/max/median）を算出。
    - rank(values): 同順位は平均ランクとするランク付け関数。
  - いずれの関数も DuckDB の prices_daily / raw_financials 等のテーブルのみ参照し、本番口座や発注 API へはアクセスしない設計。

- パッケージのエクスポート整理
  - src/kabusys/ai/__init__.py で score_news を公開。
  - src/kabusys/research/__init__.py で主要関数を公開。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の制約・注記 (Notes)
- OpenAI 依存:
  - ai モジュールは OpenAI（openai パッケージ）を利用。API キーは OPENAI_API_KEY 環境変数、または関数引数で提供する必要あり。未設定時は ValueError を送出。
  - API 呼び出し点はテスト容易性のため明示的に切り替え可能（_call_openai_api を patch）。
- データベース依存:
  - 多くの処理が DuckDB 想定（DuckDBPyConnection）。期待されるテーブル例: prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials。
  - DuckDB の executemany に関する制約（空リスト不可）を考慮した実装が含まれる。
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（使用機能に応じて）。
  - デフォルト値: KABUSYS の DB パス等はデフォルトを持つ（例: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db" 等）。
  - 設定値は Settings クラスで検証（KABUSYS_ENV, LOG_LEVEL の有効値チェック）。
- 設計上の留意点:
  - ルックアヘッドバイアス防止: date.today()/datetime.today() を直接参照しない実装方針が各 AI / Research モジュールで取られている（target_date を明示的に受ける）。
  - DB 書き込みは基本的に冪等化（DELETE→INSERT、ON CONFLICT を想定）されている。
  - フォールバック挙動（カレンダーがない場合は曜日ベース）が意図的に組み込まれている。

### 必要な外部要件
- DuckDB（python duckdb パッケージ）
- openai パッケージ（OpenAI API クライアント）
- J-Quants 関連クライアント（jquants_client モジュールが必要。実装は別途）
- ログ出力のための標準 logging 設定

---

今後のリリースでは、strategy / execution / monitoring の具体的な注文発注ロジック、監視エージェント、運用向け改善（例: トランザクション周りの堅牢化、追加の品質チェックルール、より詳細なメトリクス出力）を追記していく予定です。