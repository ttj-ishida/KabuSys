# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
形式は「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-31
初回リリース — 日本株自動売買システムの基盤機能を実装。

### 追加
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - パッケージ公開用 __all__ に data / strategy / execution / monitoring を定義（将来の拡張を想定）。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定読み込みを自動化。
  - 自動ロード優先順位: OS 環境変数 > .env.local > .env。
  - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
  - .env パーサは以下をサポート:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式の対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしの行は inline コメント（直前が空白/タブ の '#'）を適切に除去
  - .env 読み込み挙動:
    - override=False: 未設定のキーのみセット
    - override=True: protected（起動時のOS環境変数）に含まれない限り上書き
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
  - Settings クラスを提供し、主要設定プロパティを環境変数から取得:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - 任意/デフォルト: KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）、DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）
    - 環境種別検証: KABUSYS_ENV は development / paper_trading / live のみ許容
    - LOG_LEVEL 検証: DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容
    - ヘルパー: is_live / is_paper / is_dev プロパティ

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp: ニュース記事を LLM（gpt-4o-mini）に投げセンチメントを算出し ai_scores テーブルへ保存する機能を実装。
    - タイムウィンドウ: target_date の前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）
    - 記事集約: news_symbols 結合により銘柄ごとに最大 _MAX_ARTICLES_PER_STOCK（デフォルト10）件、かつ _MAX_CHARS_PER_STOCK（デフォルト3000文字）でトリム
    - バッチ処理: 1 API 呼び出しで最大 _BATCH_SIZE（20）銘柄処理
    - レスポンスは JSON Mode を期待し、厳密な構造 {"results": [{"code":"XXXX","score":0.0}, ...]} を要求
    - リトライ: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ（最大回数は定数で管理）
    - バリデーション: JSON パース、results の存在、各要素の code/score 型チェック、未知コードの無視、スコアを ±1.0 にクリップ
    - 書き込み: 成功した銘柄のみを DELETE → INSERT の冪等操作で置換（部分失敗時に既存データを保護）
    - パブリック関数: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。api_key が与えられない場合は環境変数 OPENAI_API_KEY を参照。
  - regime_detector: ETF（1321）200日移動平均乖離とマクロニュース（LLMセンチメント）を重み付け合成し日次の市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ保存。
    - MA とニュース比重: MA 70%、マクロ 30%、スコア合成後クリップ（-1..1）
    - マクロニュース抽出はキーワードベース（複数の日本語/英語キーワードを定義）
    - OpenAI 呼び出しは JSON mode を使用し、失敗時は macro_sentiment=0.0 にフォールバック（例外を上げず継続）
    - 冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施
    - パブリック関数: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。api_key 未指定かつ環境変数未設定の場合は ValueError を送出。

- 研究用機能（kabusys.research）
  - factor_research:
    - calc_momentum(conn, target_date)：1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算
    - calc_volatility(conn, target_date)：20日 ATR、ATR 比率、20日平均売買代金、出来高比率等を計算
    - calc_value(conn, target_date)：raw_financials から最新財務データを取得し PER・ROE を計算（EPS 0/欠損時は None）
    - 各関数は prices_daily / raw_financials を参照し、結果を (date, code) ベースの dict リストで返す
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=None)：将来リターン（デフォルト [1,5,21]）を計算（営業日換算）
    - calc_ic(factor_records, forward_records, factor_col, return_col)：スピアマンランク相関（IC）を計算（データ不足時は None）
    - rank(values)：平均ランク（同順位は平均ランク）を返すユーティリティ
    - factor_summary(records, columns)：各ファクター列の count/mean/std/min/max/median を計算
  - research.__init__ で主要関数をエクスポート

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar テーブルを参照/更新するユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - DB 登録有無に応じたフォールバック（DB の値優先、未登録日は曜日ベースで判定）
    - calendar_update_job(conn, lookahead_days=90)：J-Quants から差分取得して market_calendar を冪等保存。バックフィル・健全性チェック（将来日付の異常検知）を実装
  - pipeline / etl:
    - ETLResult データクラスを提供（取得数 / 保存数 / 品質チェック結果 / エラー一覧 を格納）
    - ETL パイプラインの基盤ユーティリティ（差分取得・最終日取得ヘルパ等）を実装
    - _get_max_date / _table_exists 等の内部ユーティリティを実装
  - data パッケージで ETLResult を再エクスポート

- DuckDB を主要なローカルデータストアとして前提（多くのモジュールが DuckDB 接続を引数に取る）
- OpenAI Python SDK を使用する設計（OpenAI クライアント注入 or 環境変数 OPENAI_API_KEY を参照）

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 破壊的変更
- （初回リリースのため該当なし）

### 既知の挙動 / 注意事項
- AI 関連処理は OpenAI API キー（OPENAI_API_KEY）を必要とする。key 未設定時は score_news / score_regime は ValueError を送出する。
- LLM 呼び出し失敗時はフェイルセーフとして部分的にスコアをスキップまたはゼロにフォールバックし、処理全体を停止しない設計。
- 各モジュールは DuckDB の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）を前提としている。テーブル構造が揃っていない場合はエラーが発生する可能性がある。
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされる。CI/テスト環境等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用して明示的に無効化可能。

### セキュリティ
- 環境変数に機密情報（API トークン）を期待する設計。機密情報は OS 環境変数で管理することを推奨。
- .env ファイル読み込み時に OS 環境変数を保護するため protected set を用いた上書き制御を実装。

---

今後の予定（例）
- strategy / execution / monitoring の具体実装と統合テストを追加
- テストカバレッジの拡充（特に LLM 呼び出しのモック・部分失敗ハンドリング）
- ドキュメント（API リファレンス、DB スキーマ、運用手順）の整備

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートや運用手順はプロジェクト方針に合わせて適宜更新してください。）