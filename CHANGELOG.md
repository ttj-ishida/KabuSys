# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のパッケージバージョン: 0.1.0 (初期リリース)

## [0.1.0] - 2026-04-09

### 追加 (Added)
- パッケージ初期リリースとして以下の主要機能を追加。
- パッケージ公開情報
  - パッケージメタ: kabusys の __version__ = 0.1.0、公開サブモジュール: data, strategy, execution, monitoring（パッケージのエントリポイントを定義）。
- 環境設定管理 (kabusys.config)
  - .env ファイルと環境変数から設定を自動読み込み（OS 環境変数 > .env.local > .env の優先順位）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープを正しく処理。
    - インラインコメントの扱い（クォート有無に応じた挙動）。
  - .env 読み込み時の上書き制御（override）と OS 環境変数の保護（protected キーセット）。
  - Settings クラスで各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / システム設定等）。
  - 設定値バリデーション:
    - KABUSYS_ENV（development, paper_trading, live のみ有効）。
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のみ有効）。
    - PAPER_FILL_MODE（instant/partial/never/reject のみ有効）。
  - パスは Path オブジェクトで返す（expanduser を適用）。
- AI モジュール (kabusys.ai)
  - news_nlp:
    - score_news(conn, target_date, api_key=None)：raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（ai_scores）を算出・書き込み。
    - ニュースタイムウィンドウ計算（calc_news_window）：JST の「前日 15:00 ～ 当日 08:30」を UTC に変換して扱う。
    - バッチ処理: 1 API コールにつき最大 20 銘柄（_BATCH_SIZE）、1 銘柄あたり記事数・文字数上限でトリム。
    - JSON Mode を利用しレスポンスを厳密に検証・パース（余分な前後テキストの復元処理あり）。
    - リトライ：429 / ネットワーク断 / タイムアウト / 5xx で指数バックオフリトライ。
    - フェイルセーフ：API 失敗やパース失敗時は当該チャンクをスキップし、全体処理を継続。
    - DB 書き込みは冪等性を考慮（DELETE → INSERT、部分失敗時に既存スコアを保護）。
    - テスト容易性: _call_openai_api を patch して差し替え可能。
  - regime_detector:
    - score_regime(conn, target_date, api_key=None)：ETF 1321（日経225連動）の 200 日 MA 乖離（重み70%）とマクロセンチメント（重み30%）を合成して market_regime テーブルに書き込む。
    - ma200_ratio の計算は target_date 未満のデータのみを使用してルックアヘッドを防止。
    - マクロニュース取得は news_nlp.calc_news_window を利用。
    - OpenAI 呼び出しは独立実装（モジュール結合を避ける）。
    - API エラー時は macro_sentiment を 0.0 として継続（フェイルセーフ）。
    - DB 書き込み時はトランザクション（BEGIN / DELETE / INSERT / COMMIT）を用い、失敗時は ROLLBACK を試行。
- データプラットフォーム (kabusys.data)
  - calendar_management:
    - 市場カレンダー管理（market_calendar）と営業日判定ユーティリティを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar が未取得のケースは曜日ベース（平日を営業日）でフォールバックする設計。
    - calendar_update_job: J-Quants API からの差分取得と market_calendar への冪等保存（バックフィルや健全性チェック実装）。
  - ETL パイプライン:
    - pipeline.ETLResult: ETL 実行結果を保持する dataclass を公開（kabusys.data.etl で再エクスポート）。
    - ETL 設計方針: 差分更新・バックフィル・品質チェック（quality モジュール）を想定した処理フローを備える。
  - jquants_client を用いたデータ取得 / 保存の想定インターフェースに連携（calendar と ETL で使用）。
- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum(conn, target_date)：mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）を計算。
    - calc_volatility(conn, target_date)：atr_20 / atr_pct / avg_turnover / volume_ratio 等のボラティリティ・流動性指標を計算。
    - calc_value(conn, target_date)：raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0/欠損の場合は None）。
    - 全関数は prices_daily / raw_financials のみに依存し、ルックアヘッドバイアスを避ける（target_date 引数必須）。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=None)：指定ホライズンの将来リターンを一括取得（複数ホライズンへ対応）。
    - calc_ic(factor_records, forward_records, factor_col, return_col)：Spearman ランク相関（IC）を計算。十分なサンプルがない場合は None を返す。
    - rank(values)：同順位は平均ランクを採る安定したランク関数を実装（丸めによる ties 回避）。
    - factor_summary(records, columns)：各ファクター列の count/mean/std/min/max/median を計算。
  - パッケージ __init__ で主要関数を再エクスポート（研究用途の利便性向上）。
- 依存関係（明示）
  - DuckDB をデータベース操作に利用。
  - OpenAI SDK（OpenAI クライアント）を LLM 呼び出しに利用。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### 削除 (Removed)
- （初期リリースのため該当なし）

### 非推奨 (Deprecated)
- （初期リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーの取り扱いは直接引数で注入可能（api_key 引数）か環境変数 OPENAI_API_KEY を参照する方式。キー管理・利用はユーザー側で適切に行ってください。

---

注意事項 / 設計上の重要点（ドキュメント的補足）
- ルックアヘッドバイアス回避: AI のスコアリングやファクター計算はすべて明示的な target_date を受け取り、内部で datetime.today() / date.today() を参照しない実装方針です。バッチ処理やバックテストでの再現性を重視しています。
- フェイルセーフ: LLM 呼び出しや外部 API の失敗は全体処理を止めない設計（デフォルトスコアやチャンクスキップ）になっています。致命的な DB 書き込みエラーは上位に伝播します。
- テスト容易性: AI 呼び出し部分は内部の _call_openai_api を patch することでモック化できるよう配慮しています。
- DB 書き込みの冪等性: calendar / ai_scores / market_regime への書き込みは既存行を上書き・削除してから INSERT するなど冪等性を考慮しています。トランザクション（BEGIN/COMMIT/ROLLBACK）を使用。

お問い合わせや不具合報告はリポジトリの Issue をご利用ください。