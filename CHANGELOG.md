CHANGELOG
=========
すべての注目すべき変更を記録します。これは Keep a Changelog 準拠の形式です。

注：
- 初回リリースの内容はリポジトリ内のコードから推測して作成しています。
- 日付はこの出力時点（2026-03-29）を使用しています。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-29
-------------------
Added
- パッケージ基盤
  - 初版リリース: kabusys パッケージを追加。トップレベルの __version__ を "0.1.0" として定義。
  - パッケージの公開 API (__all__) に data, strategy, execution, monitoring を設定。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートは .git または pyproject.toml を基準に探索（__file__ からの親探索で CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを実装:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの考慮。
    - 無効行（空行・コメント・= 無し）は無視。
  - 環境変数参照ユーティリティ Settings を提供（プロパティ経由で値を取得）。
    - J-Quants / kabuステーション / Slack / DB パスなど主要設定をプロパティ化。
    - 必須変数未設定時は ValueError を送出。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）。
    - duckdb / sqlite のデフォルトパス設定、Path.expanduser に対応。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX マーケットカレンダー管理と夜間バッチ更新ジョブ（calendar_update_job）を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar が未取得のときは曜日（平日のみ）をフォールバックとして使用。DB 登録ありなら DB 値優先。
    - 最大探索範囲制限やバックフィル、健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラス（ETL 実行結果の集約）を実装。
    - 差分取得・バックフィル・品質チェックを想定した ETL パイプライン基盤（pipeline モジュールの公開インターフェースと設計方針）。
    - DuckDB 存在チェックや最新日付取得ユーティリティを実装。
  - etl モジュールを通じて ETLResult を再エクスポート。

- 研究（kabusys.research）
  - factor_research:
    - ファクター計算関数を実装: calc_momentum（1M/3M/6M リターン、MA200乖離）、calc_volatility（ATR/平均売買代金/出来高比率）、calc_value（PER/ROE）。
    - DuckDB を使った SQL ベースの計算（prices_daily / raw_financials のみ参照）。欠損やデータ不足時の None 処理を考慮。
  - feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターンを一括取得）、calc_ic（Spearman ランクの IC 計算）、rank（同順位は平均ランクで処理）、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等の外部依存を使わずに純 Python / DuckDB で実装。
  - research パッケージで zscore_normalize を data.stats から再エクスポートし、ファクター解析に必要なユーティリティを集約。

- AI モジュール（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を基に銘柄毎にニュースを集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントスコアを取得して ai_scores テーブルへ書き込む処理を実装。
    - チャンク（最大 20 銘柄）単位でのバッチ呼び出し、1 銘柄あたりの記事数・文字数上限、JSON レスポンスのバリデーション、スコアの ±1.0 クリップを実装。
    - リトライ（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフ、API 失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）。
    - DuckDB の executemany に空リストが渡せない点を考慮した安全な DELETE/INSERT ロジック。
    - calc_news_window ユーティリティで JST ベースのニュースウィンドウ（前日 15:00 ～ 当日 08:30 JST）を UTC naive datetime で提供。
  - regime_detector:
    - ETF 1321（日経225連動）200 日移動平均乖離（重量 70%）とニュース由来のマクロセンチメント（重量 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする処理を実装。
    - マクロ記事抽出（キーワードフィルタ）、OpenAI 呼び出し、レスポンスの JSON パース、スコア合成、閾値判定、DB トランザクション処理を実装。
    - API 失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
  - AI 関連共通設計:
    - OpenAI クライアントは引数または環境変数 OPENAI_API_KEY で解決。未設定時は ValueError。
    - モジュール間でプライベートな _call_openai_api を共有せず、各モジュール内で独立実装（疎結合）。
    - datetime.today()/date.today() を直接参照せず、target_date を明示的に渡すことでルックアヘッドバイアスを防止。

- 実装上の堅牢化・運用面の配慮
  - 多くの API 呼び出しでリトライとログ記録を実装（RateLimit, Timeout, APIError の扱いを明確化）。
  - DuckDB とのやり取りでの互換性配慮（空の executemany 回避、日付変換ユーティリティ）。
  - DB 書き込みは冪等性を意識した実装（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK の使用とエラーハンドリング）。
  - ログ出力や警告を多用し、失敗時にも安全に継続する設計（フェイルセーフ）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

注意事項 / 必要な環境変数
- OpenAI: OPENAI_API_KEY（API を使う機能を呼ぶ際に必須）
- J-Quants 用: JQUANTS_REFRESH_TOKEN
- kabuステーション 用: KABU_API_PASSWORD, optional KABU_API_BASE_URL
- Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DB: DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
- 動作に duckdb Python パッケージ、openai SDK（スクリプトは OpenAI クライアントの chat.completions.create を使用する想定）が必要

既知の設計上の注意点
- AI 呼び出しは gpt-4o-mini と JSON mode 想定。API の挙動やレスポンス形式の変化には注意。
- DuckDB のバージョン差異（executemany の挙動等）に配慮した実装を行っているが、環境依存の挙動が出る可能性あり。
- 各処理は target_date を外部から渡す前提（テスト容易性・ルックアヘッド防止）。自動で「今日」を使う実装は存在しない。

今後の想定
- strategy / execution / monitoring モジュールの具体的なアルゴリズム・発注ロジックの実装（現状はパッケージエクスポートのみ宣言）。
- テストカバレッジの充実、CI ワークフローの整備、外部 API 依存部のモック化サポート強化。