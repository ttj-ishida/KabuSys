# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベース（バージョン 0.1.0）から推測して作成した初回リリース向けの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース

### Added
- パッケージ基盤
  - パッケージエントリポイント (src/kabusys/__init__.py) を追加。公開モジュール: data, strategy, execution, monitoring。
  - バージョン番号を `__version__ = "0.1.0"` として定義。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機構を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
  - .env の行パーサーを実装し、export プレフィックス、シングル・ダブルクォート、バックスラッシュエスケープ、インラインコメント（条件付き）に対応。
  - 環境変数の必須チェック (`_require`) を導入。典型的な設定項目をプロパティとして定義（J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベル 等）。
  - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の許容値検証）。

- データプラットフォーム（DuckDB ベース）
  - ETL パイプライン型および結果型 (ETLResult) を公開 (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)。
  - 市場カレンダー管理モジュールを追加（src/kabusys/data/calendar_management.py）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ヘルパー。
    - calendar_update_job により J-Quants からの差分取得 → idempotent 保存処理（ON CONFLICT相当）を実装。
    - カレンダーデータ未取得時の曜日ベースフォールバック、バックフィル、健全性チェック実装。

- リサーチ機能 (src/kabusys/research)
  - factor_research モジュールを追加:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離等を計算。
    - calc_volatility: 20日 ATR / 相対ATR、平均売買代金、出来高比率を計算。
    - calc_value: PER / ROE を raw_financials と prices_daily から算出。
  - feature_exploration モジュールを追加:
    - calc_forward_returns: 任意ホライズンの将来リターン算出（horizons 検証あり）。
    - calc_ic: スピアマンランク相関（IC）計算。
    - factor_summary: 複数カラムの基本統計量集計。
    - rank: 同順位は平均ランクとするランク付け実装。
  - いずれの関数も DuckDB 接続を受け取り、外部 API に依存しない設計。

- ニュース NLP / AI (src/kabusys/ai)
  - news_nlp モジュール (src/kabusys/ai/news_nlp.py):
    - raw_news と news_symbols から銘柄単位で記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を使ってセンチメントを取得。
    - バッチ処理（最大 20 銘柄／呼び出し）、1 銘柄当たり記事数・文字数の上限、レスポンス検証、スコアの ±1.0 クリップを実装。
    - リトライポリシー（429, ネットワーク断, タイムアウト, 5xx）と指数バックオフを実装。失敗時は該当チャンクをスキップして処理継続。
    - DuckDB 互換性に配慮し、executemany に空リストを渡さない実装と部分置換（DELETE → INSERT）で冪等性を確保。
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算（UTC 変換）を提供。
    - score_news: 公開 API。OpenAI API キーは引数または環境変数 OPENAI_API_KEY で解決。ルックアヘッドバイアスに配慮。
    - テスト用に OpenAI 呼び出しを patch で差し替え可能（_call_openai_api を分離）。

  - regime_detector モジュール (src/kabusys/ai/regime_detector.py):
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、市場レジーム（bull / neutral / bear）を日次評価。
    - マクロニュース検索用キーワードリストを内蔵し、タイトル検索で記事を抽出（最大 20 件）。
    - OpenAI 呼び出し、JSON レスポンスパース、リトライ（429/ネットワーク/タイムアウト/5xx）を実装。API 失敗時は macro_sentiment=0.0（フェイルセーフ）。
    - score_regime: 公開 API。DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - テスト可能性のため OpenAI 呼び出しをモジュール内で独自実装（news_nlp と共有しない設計）。

- データ品質・ETL 設計
  - ETLResult に品質問題・エラー情報を格納する仕組みを提供し、品質チェック（quality モジュール想定）と組合せる想定。
  - 差分取得、バックフィル、カレンダーヘルパーを組み合わせた ETL 設計（pipeline モジュールを参照するインターフェース）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- API キー等の必須環境変数は Settings 経由で取得し、未設定時に ValueError を送出して明示する（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY など）。
- .env の自動ロードはデフォルトで有効だが、`KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能。OS 環境変数は読み込み時に protected として上書きを防止。

### Notes / Implementation details / Known behaviours
- 全モジュールでルックアヘッドバイアスを避ける設計（datetime.today()/date.today() を直接参照しない処理や、SQL の date < target_date 条件など）。
- raw_news.datetime は UTC で保存されている前提で処理（news ウィンドウの計算は JST → UTC に変換）。
- OpenAI 呼び出しは gpt-4o-mini を想定し、JSON Mode（response_format={"type": "json_object"}）で厳密な JSON 出力を期待する。レスポンスにノイズが混入した場合の復元処理や検証ロジックを備える。
- テスト容易性のため、OpenAI 呼び出し部分はモジュール内関数を patch して差し替え可能（ユニットテスト向けのフックを考慮）。
- DuckDB のバージョン互換性（executemany に空リストを渡せない制約など）を考慮した実装。
- research モジュールは外部ライブラリ（pandas 等）に依存しない純粋な SQL / 標準ライブラリ実装を目指す。
- エラー時のフェイルセーフは可能な限り設計（例えば LLM の失敗時は中立スコアを採用して処理継続）。

---

今後のリリースにおいては、下記のような追加・改善が想定されます（例）:
- strategy / execution / monitoring モジュールの実装と公開 API の完成
- J-Quants / kabu API クライアント実装の詳細化と統合テスト
- モデル（LLM）切替やローカル評価のためのバックエンド抽象化
- パフォーマンス最適化（大規模データのバッチ処理、並列化等）
- より詳細な品質チェック（quality モジュールの実装とルール整備）

（以上）