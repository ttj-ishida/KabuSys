# Changelog

すべての注目すべき変更は本ファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全般的な方針:
- バージョン管理は semver に従います（現リリースは 0.1.0）。
- 実装上の設計・フェールセーフに関する注意点（ルックアヘッドバイアス回避、DB の冪等書き込み、堅牢な API リトライ等）も追記します。

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - ルートパッケージとエクスポート:
    - src/kabusys/__init__.py にてバージョンと主要サブパッケージ（data, research, ai, ...）を公開。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを追加。
  - 自動 .env ロード機能:
    - プロジェクトルート（.git または pyproject.toml を探索）を起点に .env / .env.local を読み込み。
    - 読み込み順: OS 環境変数 > .env.local > .env。テスト用途に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export KEY=val 形式、クォート文字列（エスケープ対応）、インラインコメント処理などに対応。
  - 設定プロパティ例:
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID を必須として取得し未設定時に ValueError を送出。
    - KABUSYS_ENV の妥当性チェック（development / paper_trading / live）。
    - LOG_LEVEL の妥当性チェック（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - デフォルトのデータベースパス（DUCKDB_PATH, SQLITE_PATH）を Path 型で提供。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を使い、銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ書き込む機能を提供。
  - 主な特徴:
    - JST 時間ウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
    - 1銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）でプロンプト肥大化を防止。
    - 最大 _BATCH_SIZE（デフォルト20）でバッチ送信。
    - JSON Mode を利用して厳密な JSON を期待、かつ前後余計なテキストが混ざった場合の復元ロジックを実装。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ（初期 wait を指定、最大試行回数あり）。
    - レスポンスバリデーション: results 配列、code と score の存在チェック、未知コードの無視、スコアの浮動小数チェック、±1.0 のクリップ。
    - 部分成功時の DB 保護: 書き込みは対象コードのみ DELETE → INSERT で置換（DuckDB executemany の空リスト制約に配慮）。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出し market_regime に冪等書き込みする機能を追加。
  - 主な特徴:
    - ma200 の計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを排除。
    - マクロ記事抽出は news_nlp.calc_news_window のウィンドウに基づきマクロキーワードでフィルタ。
    - OpenAI 呼び出しは分離実装（news_nlp と共有せずモジュール結合を防止）。
    - API リトライ／エラーハンドリング（RateLimit, 接続エラー, タイムアウト, APIError の 5xx 判定）を実装。API 失敗時は macro_sentiment=0.0 として処理を継続するフェイルセーフ設計。
    - 最終的なスコアは clip(-1, 1) し閾値でラベリング。DB 書き込みは BEGIN/DELETE/INSERT/COMMIT を行い、例外時は ROLLBACK を試行。

- リサーチモジュール（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev を prices_daily から計算。
    - calc_volatility: 20日 ATR, 相対 ATR (atr_pct), 20日平均売買代金, 出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0/欠損時は None）。
    - 設計上、prices_daily/raw_financials のみ参照し外部 API にアクセスしない。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。十分な有効レコードがない場合は None を返す。
    - factor_summary / rank: 基本統計量と順位付けユーティリティを提供。
  - 研究用関数は外部ライブラリに依存せず、標準ライブラリ + DuckDB で完結。

- データプラットフォーム（src/kabusys/data/*）
  - calendar_management:
    - market_calendar を利用した営業日判定、次営業日/前営業日の検索、期間の営業日取得、SQ 日判定などを提供。
    - DB にデータがない場合は曜日ベースでフォールバック（週末を非営業日として扱う）。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等的に更新するジョブ（バックフィル、健全性チェックを実装）。
  - pipeline / etl:
    - ETLResult データクラスの追加（ETL 実行結果の集約、品質問題とエラーを収集）。
    - ETL の差分更新、backfill、品質チェック方針に準拠した骨格実装。
  - ETL 用ユーティリティ: テーブル存在チェック、最大日付取得、取引日調整ロジック等を提供。

- その他ユーティリティ・エクスポート
  - kabusys.data.etl で ETLResult を再エクスポート。
  - kabusys.ai.__init__ で score_news を公開。
  - kabusys.research.__init__ で主要な研究用関数を再エクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

Changed
- （初期リリースのため該当なし）

Fixed / Robustness improvements
- DuckDB の挙動差異（executemany に空リストを渡せない点）に対する防御処理を実装（空リストのときは executemany を呼ばない）。
- OpenAI レスポンスの JSON パース失敗時に備え、応答文字列から最外の波括弧を抜き出して復元しようとするフォールバック処理を追加（news_nlp）。
- API エラー処理の詳細化:
  - APIError の status_code を安全に取得し、5xx の場合はリトライ、それ以外は即時フェイルセーフ処理を行う（regime_detector / news_nlp）。
  - リトライ時の指数バックオフ実装とログ出力の整備。
- DB トランザクションの安全化: INSERT 前に既存行を DELETE することで冪等性を確保し、例外発生時は ROLLBACK を試みる（失敗時は警告ログ）。

Security
- API キーの扱い:
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY から解決。未解決の場合は ValueError を発生させ早期検出。
  - .env 自動ロード時に OS 環境変数を上書きしない（保護リストを導入）。必要な場合のみ .env.local で上書き可能。
- .env の読み取り時にファイルアクセスエラーが発生した場合は警告を出して安全にスキップ。

Notes / Implementation decisions
- ルックアヘッドバイアス対策:
  - news_nlp, regime_detector など日時に関連する処理は内部で datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を与える設計。
  - DB クエリでは target_date 未満（排他）や window の半開区間を徹底して使用。
- フェイルセーフ設計:
  - 外部 API（OpenAI, J-Quants 等）の障害時は極力処理を継続し、影響範囲を最小化。例えば macro_sentiment が取得できない場合は 0.0 で代替。
- ロギング:
  - 各主要処理で情報ログ / 警告ログ / 例外ログを整備し、運用観点での可観測性を強化。

Deprecated / Removed
- （初期リリースのため該当なし）

Security
- （該当するセキュリティ修正は上記「Security」を参照）

今後の予定（例示）
- モデル切替やプロンプト改良によるスコア品質改善。
- ai_score の履歴保存・メタデータ拡張。
- ETL の細かな品質チェック実装（quality モジュールの拡張）。
- 単体テスト・統合テストの充実と CI 統合。

---
このリリースはコードベースの内容から推測してまとめた CHANGELOG です。必要に応じて日付や記載内容を実際のリリース記録に合わせて調整してください。