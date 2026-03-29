Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。リリースは初版（0.1.0）としてコードベースの内容から推測して記載しています。必要に応じて日付や細部を調整してください。

----------------------------------------------------------------------
CHANGELOG
======================================================================

すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

Unreleased
----------------------------------------------------------------------
（未リリースの変更はここに記載）

[0.1.0] - 2026-03-29
----------------------------------------------------------------------
Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py によりパッケージ名とバージョンを定義（__version__ = "0.1.0"）。
    - パブリックサブパッケージ一覧に data, strategy, execution, monitoring を想定。

- 設定/環境変数管理（src/kabusys/config.py）
  - .env/.env.local ファイルまたは OS 環境変数から設定をロードする自動ロード機能を実装。
    - ロード順: OS 環境変数 > .env.local (> .env)
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
  - .env パース機能を実装（コメント、export 形式、クォート・エスケープ対応、インラインコメント処理など）。
  - 既存 OS 環境変数を保護する protected セットを使用して .env の上書き挙動を制御。
  - 必須設定取得ユーティリティ _require を提供（未設定時は ValueError を送出）。
  - 標準的な設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）, LOG_LEVEL（DEBUG..CRITICAL の検証）
    - is_live / is_paper / is_dev のブールヘルパー

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols テーブルからターゲット日のニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST 相当）を集約して銘柄ごとのテキストを作成。
  - OpenAI（gpt-4o-mini）JSON mode を用いたバッチスコアリングを実装。
    - バッチサイズ、トークン肥大化対策（1銘柄あたり最大記事数／最大文字数）を設定。
    - 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。
    - レスポンスの堅牢なバリデーション（JSON パース補完、results キー・型検査、未知コードの無視、数値への正規化、±1.0 クリップ）。
    - テスト容易性のため _call_openai_api を patch して差し替え可能。
  - ai_scores テーブルへ冪等的に部分更新（対象コードのみ DELETE → INSERT）するロジックを用意。
  - API キー未設定時は ValueError を送出。API エラー時はスキップし処理継続（フェイルセーフ）。

- レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する機能を提供。
    - ma200_ratio の計算は target_date 未満のデータのみ使用しルックアヘッドバイアスを防止。
    - マクロニュースは news_nlp.calc_news_window で算出したウィンドウからキーワードフィルタで抽出（最大記事数あり）。
    - OpenAI 呼び出しは JSON mode、リトライ・フェイルセーフ・レスポンスパースの堅牢化あり。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書込失敗時は ROLLBACK 後に例外を伝播。
  - API キー未設定時は ValueError を送出。API 失敗時は macro_sentiment = 0.0 にフォールバックして処理を続行。

- データ関連（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar）を使った営業日判定ユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録値優先、未登録日は曜日ベース（土日）でフォールバックする一貫したロジック。
    - next/prev の探索は _MAX_SEARCH_DAYS による上限を設けて無限ループを防止。
    - calendar_update_job を実装し J-Quants API から差分取得→save を行う（バックフィル・健全性チェックを実装）。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - 差分更新 / 保存 / 品質チェック（quality モジュール連携）を想定した ETLResult データクラスを実装（src/kabusys/data/etl.py から再エクスポート）。
    - デフォルトのバックフィル概念、_MIN_DATA_DATE、カレンダー先読み等を実装。
    - DuckDB の互換性考慮（executemany に空リストを渡さない等）に関する注意が組み込まれている。

- リサーチ機能（src/kabusys/research/*）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算（足りない場合は None）。DuckDB SQL ベース実装。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比等を計算。true_range の NULL 伝播制御あり。
    - calc_value: raw_financials から最新財務を取得して PER/ROE を計算（EPS=0/欠損は None）。
  - feature_exploration モジュール:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算（DuckDB LEAD を利用）。
    - calc_ic: スピアマンランク相関（IC）を計算。3 銘柄未満は None。
    - rank: 同順位は平均ランクにするランク化ユーティリティ（丸めによる ties 対策あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - src/kabusys/research/__init__.py で zscore_normalize（kabusys.data.stats 由来）を含む主要 API をエクスポート。

Changed
- 初回リリースにつき該当なし。

Deprecated
- 初回リリースにつき該当なし。

Removed
- 初回リリースにつき該当なし。

Fixed
- 初回リリースにつき該当なし。

Security
- 環境変数からの API キー取得を採用。コード内に API キー等をハードコードしない設計。
- .env の自動ロードは必要に応じて無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Implementation choices（重要な設計上の注意）
- ルックアヘッドバイアス対策:
  - AI モジュール・リサーチモジュールは datetime.today()/date.today() を内部参照せず、明示的な target_date を受け取る設計。
  - DB クエリは target_date 未満 / 排他条件で将来データを参照しないように実装。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定、JSON mode を利用。429/ネットワーク/タイムアウト/5xx に対してリトライとバックオフを行う。
  - テストのために _call_openai_api を差し替え可能に実装（unittest.mock.patch を想定）。
- DuckDB 互換性:
  - executemany に空リストを渡すと失敗するバージョンの問題を回避するため、空チェックを行ってから executemany を呼ぶ。
- DB 書き込みの冪等性:
  - ai_scores / market_regime / market_calendar 等への書き込みは既存レコードを削除してから挿入することで冪等化を図っている（部分失敗時に既存データを保護する設計）。
- ログ・エラー動作:
  - API 失敗時は基本的に例外を上げずフォールバック（0.0 など）して処理継続することで、ETL / バッチの堅牢性を重視。
  - ただし API キー未設定などの致命的な環境不備は ValueError を投げる。

Required environment variables（主な必須設定）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- OPENAI_API_KEY（AI 関連機能を使う場合）

----------------------------------------------------------------------
今後の参考（提案）
- strategy / execution / monitoring モジュールの実装詳細（発注ロジック・モニタリング）が未提示。実装時は取引実行に関する安全性（注文キャンセル・重複防止等）を明確化することを推奨。
- 単体テスト・統合テストのサンプル、CI での環境変数取扱い方針（シークレット管理）のドキュメント化を追加すると安全性が向上します。

----------------------------------------------------------------------

必要であれば、この CHANGELOG を英語に翻訳したり、実際のリリース日や追加の変更履歴（例えば bugfix や performance 改善）を追記して更新することも可能です。