# CHANGELOG

すべての重要な変更点を記載します。フォーマットは「Keep a Changelog」に準拠しています。

注: バージョンとリリース日はソースコードから推測して作成しています（package __version__ = "0.1.0"）。実運用では適宜日付・内容を更新してください。

## [Unreleased]

- 今後のリリースに向けた保留事項やマイナー改善・ドキュメント追記などをここに記載します。

## [0.1.0] - 2026-04-09

初回公開リリース（推測）。日本株自動売買システム「KabuSys」のコア機能群を実装。

### 追加 (Added)

- パッケージ基盤
  - パッケージ名: kabusys。トップレベルの公開モジュール: data, strategy, execution, monitoring。
  - バージョン情報: __version__ = "0.1.0"。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイル自動読み込み機能を実装（プロジェクトルート判定 .git / pyproject.toml をベースに探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - export KEY=val 形式やクォート・エスケープ・インラインコメントに対応したパーサを実装。
  - OS 環境変数を保護する protected オプションを用意。
  - Settings クラスを提供し、以下の設定をプロパティとして公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
    - PAPER_FILL_MODE（paper trading の fill モード: instant/partial/never/reject を検証）
    - PID/KILL flag 関連パスとクリア動作設定
    - CPU/MEMORY/DISK の閾値（監視用）
    - KABUSYS_ENV（development/paper_trading/live の検証）および LOG_LEVEL 検証
    - is_live / is_paper / is_dev ヘルパー

- データプラットフォーム (kabusys.data)
  - ETL パイプライン基盤 (kabusys.data.pipeline)
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラー一覧などを保持）。
    - 差分更新・バックフィル・品質チェックの設計に基づくパイプライン方針を反映。
    - DuckDB を用いた処理を想定。
  - ETL の公開インターフェース再エクスポート (kabusys.data.etl -> ETLResult)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを利用した営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 未取得時は曜日（平日=営業日）ベースのフォールバックを実装。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等に保存する夜間ジョブ（バックフィル・健全性チェックあり）。
    - 最大探索日数 (_MAX_SEARCH_DAYS) による無限ループ防止。

  - DuckDB 互換性考慮
    - executemany に空リストを渡さないガード（DuckDB 0.10 の挙動を考慮）。

- 研究・ファクター計算 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、atr_pct、avg_turnover、volume_ratio を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新財務データを target_date 以前から取得）。
    - 設計は DuckDB 上で SQL + Python による自己完結実装（外部 API へのアクセスは無し）。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得するクエリ実装。
    - calc_ic: スピアマン（ランク）相関による IC 計算（コード結合・None 除外・有効レコード閾値あり）。
    - rank: 同順位に対して平均ランクを返す実装（丸めによる tie 対策あり）。
    - factor_summary: 指定列の count/mean/std/min/max/median を返す統計サマリ。

- AI / ニュース解析 (kabusys.ai)
  - news_nlp モジュール:
    - score_news: raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI の gpt-4o-mini（JSON Mode）でセンチメントを取得して ai_scores テーブルへ書き込む。
    - 設計: バッチ処理（最大 20 銘柄 / コール）、1 銘柄あたり最大記事数・文字数でトリム、429/ネットワーク/5xx に対して指数バックオフリトライ、レスポンスの厳密バリデーション（JSON 抽出/結果検証）、スコア ±1 にクリップ。
    - calc_news_window: JST ベースのニュース収集ウィンドウ（前日15:00～当日08:30 JST に対応する UTC time window）を提供。
    - API 呼び出しのラッパー関数を用意し、テスト時には patch で差し替え可能。
    - JSON パース失敗時はギリギリの復元（最外の {} を抽出）を試みるフォールバックを実装。
  - regime_detector モジュール:
    - score_regime: ETF 1321（日経225連動型）の 200 日 MA 乖離（重み70%）と news_nlp によるマクロセンチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュースは raw_news からキーワードフィルタで抽出（キーワードリストを実装）。
    - OpenAI 呼び出しは独自実装とし、API エラー時は macro_sentiment=0.0 で続行（フェイルセーフ）。
    - ロジックはルックアヘッドバイアス回避を意識（date < target_date 等の排他条件を使用、datetime.today() を直接参照しない）。

- OpenAI / モデル仕様
  - gpt-4o-mini を標準モデルとして利用し、response_format={"type": "json_object"} を使用する前提の実装。
  - API キーは api_key 引数または環境変数 OPENAI_API_KEY から解決する設計。未設定時は ValueError を送出。

- 監視・運用
  - PID / kill flag 用のパス設定を Settings で公開。
  - リソース閾値（CPU / メモリ / ディスク）を Settings で構成可能。

### 変更 (Changed)

- （初版のため過去バージョンからの変更はなし）設計・実装における安全策や互換性注記をコード内ドキュメントに反映。
  - DuckDB の executemany 空リスト制約や API エラーの分類（status_code に基づく 5xx 判定）を実装に反映。
  - モジュールの結合を低く保つ（AI モジュール間で private helper を共有しない設計）。

### 既知の挙動 / 注意点 (Known issues / Notes)

- OpenAI 呼び出し失敗時の挙動:
  - news_nlp / regime_detector ともに、429・接続断・タイムアウト・5xx はリトライする。リトライ消費後は該当銘柄や macro_sentiment をスキップ（0.0）し処理継続する。
  - news_nlp はレスポンスのバリデーションに失敗した場合、そのチャンクをスキップして進行する。部分取得の保護のため、ai_scores への書き込みは取得できたコードのみを置換する（DELETE → INSERT）。
- 時刻・タイムゾーン:
  - raw_news.datetime は UTC を前提としている。ニュースウィンドウ計算は JST を基準に UTC に変換して扱う（calc_news_window を使用）。
- ルックアヘッドバイアス対策:
  - AI およびリサーチ関数は内部で datetime.today() / date.today() を参照せず、必ず target_date を引数で受け取る設計。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings のプロパティアクセス時に必須（未設定なら ValueError）。OpenAI の機能を使用するには OPENAI_API_KEY が必要。
- DuckDB 依存性:
  - 実行時には DuckDB が必要。DuckDB バージョン差異に起因する挙動（例: list 型バインドの挙動）を考慮して実装している。
- セキュリティ/運用:
  - .env 自動ロード機能は便利だが、実運用時のシークレット管理には environment variable の直接設定や秘密管理システムの利用を推奨。
  - .env の上書きルールと protected の概念により OS 環境変数の意図しない上書きを防止。

### 修正 (Fixed)

- （初版のため過去バージョンからの修正はなし）

### 削除 (Removed)

- 特になし

### セキュリティ (Security)

- 環境変数の自動ロードはデフォルトで有効。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD でオフにできる点を運用者に通知すること。
- API キー・シークレットは Settings の必須チェックで早期に検出されるが、ログ出力等で漏洩しないよう取り扱い注意。

---

今後の改善候補（例）
- OpenAI 呼び出し部分の抽象化インターフェース化（モック容易性向上・複数モデル対応）。
- エラー監視・メトリクス収集の強化（Prometheus 等）。
- news_nlp のスコア挙動のテストカバレッジ拡充（レスポンスノイズやトークン制限を想定したケース）。
- J-Quants / kabu API クライアントのより詳細なラッパーとリトライ戦略の統一化。

（以上）