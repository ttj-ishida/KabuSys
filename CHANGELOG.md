Keep a Changelog に準拠した CHANGELOG.md（日本語）
※この CHANGELOG は提示されたコードベースの内容から推測して作成しています。

All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠します。

Unreleased
----------

（現在未リリースの変更はここに記載）

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ初回公開: kabusys 0.1.0
  - パッケージメタ情報: __version__ = "0.1.0"。公開モジュールとして data, strategy, execution, monitoring をエクスポート。

- 環境設定 / ロード機能（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出ロジック: __file__ から親ディレクトリを探索し .git または pyproject.toml を基準に判定（CWD に依存しない）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理（クォートありはコメント無視、クォートなしは直前に空白/タブがある # をコメントと見なす）に対応。
  - _load_env_file に override と protected（OS 環境変数保護）オプションを実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス 等の設定プロパティを安全に取得可能（必須項目は未設定時に ValueError）。KABUSYS_ENV / LOG_LEVEL に対するバリデーションと利便性プロパティ（is_live, is_paper, is_dev）を実装。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp モジュール
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメントスコア（-1.0〜1.0）を取得して ai_scores テーブルへ保存する処理を実装。
    - ニュースウィンドウ: JST 基準で「前日 15:00 ～ 当日 08:30」（内部は UTC naive に変換）を採用。calc_news_window を公開。
    - バッチ処理: 一度に最大 _BATCH_SIZE=20 銘柄を API に送信。1 銘柄あたり最大 _MAX_ARTICLES_PER_STOCK=10 記事、_MAX_CHARS_PER_STOCK=3000 文字でトリム。
    - リトライ戦略: 429（RateLimit）・接続断・タイムアウト・5xx サーバーエラーは指数バックオフで最大 _MAX_RETRIES 回までリトライ。その他エラー時はそのチャンクをスキップして継続（フェイルセーフ）。
    - レスポンス検証: JSON パース、"results" 配列の存在、code と score の型チェック、未知コードの無視、スコアを ±1.0 にクリップ。JSON mode の前後テキスト混入ケースに対する復元ロジックも実装。
    - DuckDB への書き込みは部分置換（DELETE → INSERT）で行い、部分失敗時に既存のスコアを保持する実装。DuckDB executemany の空リスト制約を考慮して条件付きで executemany を呼ぶ。
    - テスト容易性: OpenAI 呼び出しを _call_openai_api として分離し、unit test でパッチ可能。

  - regime_detector モジュール
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースに対する LLM センチメント（重み 30%）を合成して日次の market_regime を判定（ラベル: "bull"/"neutral"/"bear"）。
    - MA 計算は target_date より前のデータのみを使用し、ルックアヘッドバイアスを排除。
    - マクロニュースは news_nlp のウィンドウ集計関数 calc_news_window を利用して抽出。LLM は gpt-4o-mini を使用し、JSON の {"macro_sentiment": -1.0..1.0} を期待。
    - API エラー／パース失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。リトライロジックを実装。
    - レジームスコア合成式・閾値・重みなどは定数化。DB への書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）で行う。
    - テスト容易性: OpenAI 呼び出しを内部関数で分離。

- Research（ファクター計算）モジュール（kabusys.research）
  - factor_research モジュール: calc_momentum / calc_volatility / calc_value を実装。
    - Momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）。データ不足時は None を返す。
    - Volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算。
    - Value: raw_financials から直近の（target_date 以前）財務データを取得して PER, ROE を計算（EPS=0 や欠損は None）。
    - DuckDB の SQL とウィンドウ関数を活用し、高速に一括計算。
    - 全関数は prices_daily / raw_financials のみを参照し、本番口座や発注 API にはアクセスしない設計。
  - feature_exploration モジュール: calc_forward_returns / calc_ic / factor_summary / rank を実装。
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一クエリで取得。引数検証あり。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。十分なデータ点がない場合は None を返す。
    - factor_summary: count/mean/std/min/max/median を計算するシンプルな統計サマリ。
    - rank: 同順位は平均ランク（ties は平均ランク割当）を実装。丸め誤差を抑えるため round(..., 12) を使用。
  - kabusys.research パッケージは kabusys.data.stats の zscore_normalize を再エクスポート。

- Data（データパイプライン）モジュール（kabusys.data）
  - calendar_management モジュール
    - JPX 市場カレンダー管理: market_calendar テーブルを使った営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（土日非営業）を利用。DB 登録あり → DB 値優先、未登録日は曜日フォールバックで一貫性を保つ設計。
    - calendar_update_job を提供し、J-Quants API からの差分取得 → 保存（save_market_calendar）を行う。バックフィル（直近 _BACKFILL_DAYS の再取得）、健全性チェック（過度に未来の日付はスキップ）を実装。
    - DuckDB の日付型取り扱いヘルパーとテーブル存在チェックユーティリティを提供。
  - pipeline / etl モジュール
    - ETL パイプライン向けの ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。ETL 実行結果・品質問題・エラーの集約、辞書変換ユーティリティを提供。
    - データ差分取得・保存・品質チェックの指針を実装（jquants_client と quality モジュールを利用することを想定）。
    - DuckDB における最大日付取得、テーブル存在チェックなどの内部ユーティリティを提供。
    - ETL の設計では backfill_days による再取得、品質チェックは収集継続（致命的であっても上位で判断）、id_token 注入によるテスト容易化など、実運用を意識した設計。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY から解決。未設定時は明示的に ValueError を発生させて誤操作を防止。
- .env 自動ロード時、既存の OS 環境変数は protected として上書きを防止。

Notes / Implementation details
- ルックアヘッドバイアス防止: 多くの機能（news scoring / regime scoring / factor 計算 等）は datetime.today() / date.today() を直接参照せず、target_date 引数に基づいて計算する設計。
- DuckDB 互換性: executemany に空リストを渡せないバージョン（DuckDB 0.10 など）を考慮したガードを入れている箇所がある。
- OpenAI 呼び出しは各モジュールで独立して実装（_call_openai_api をモジュールごとに分離）し、モジュール間でプライベート関数を共有しないことで結合度を低くしている。
- ロギング: 各処理で適切に logger.debug/info/warning/exception を出力するよう実装。警告や例外時の挙動（フェイルセーフか例外伝播か）はモジュール設計方針に従う。

Acknowledgements
- この CHANGELOG は提供されたソースコードを基に推測して作成しています。実際のリリースノートや変更履歴はプロジェクトのリリースポリシーに従って調整してください。