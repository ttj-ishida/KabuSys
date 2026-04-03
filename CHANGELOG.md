CHANGELOG
=========
すべての注目すべき変更を記録します。これは Keep a Changelog の形式に準拠しています。  
リリースはセマンティックバージョニングに従います。

フォーマットについての詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（なし）

0.1.0 - 2026-04-03
-----------------
Added
- パッケージ基盤
  - kabusys パッケージの初期バージョンを追加。パッケージの公開 API を __all__ で定義（data, strategy, execution, monitoring）。
  - バージョン番号を __version__ = "0.1.0" として設定。

- 環境設定 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロード機能: プロジェクトルート（.git または pyproject.toml を探索）を検出し、.env → .env.local の順で読み込む（.env.local は上書き）。
  - 自動ロード無効化オプション: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env のパーサ強化:
    - 行頭の "export " に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォートなしの行でのインラインコメント判定（直前が空白/タブの場合に '#' をコメントとみなす）。
  - 認証情報/パス等のプロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN, データベースパス等）。
  - 環境・ログレベルの検証（KABUSYS_ENV の許容値, LOG_LEVEL の許容値）。
  - 監視用しきい値（CPU/MEMORY/DISK）や PID/KILL フラグの設定をプロパティとして提供。

- データ層 (kabusys.data)
  - ETL 結果を表す dataclass を公開（kabusys.data.pipeline.ETLResult / kabusys.data.etl での再エクスポート）。
  - ETL パイプライン基盤（kabusys.data.pipeline）を実装: 差分更新・保存・品質チェック設計に対応するユーティリティ（ETLResult、テーブル存在チェック、最終日付取得等の基礎機能）。
  - マーケットカレンダー管理（kabusys.data.calendar_management）を実装:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - market_calendar データが無い場合は曜日（土日）ベースでフォールバックする一貫した挙動。
    - calendar_update_job を実装し、J-Quants 経由で差分取得して market_calendar を冪等保存（バックフィル、健全性チェック含む）。
    - 最大探索範囲 (_MAX_SEARCH_DAYS) による無限ループ防止。

  - DuckDB 周りの互換性配慮:
    - executemany に空リストを渡せない DuckDB の制約を考慮した安全な書き込みロジック（空チェックを行ってから executemany）。

- 研究 (kabusys.research)
  - ファクター計算モジュール（kabusys.research.factor_research）を実装:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials と組み合わせた PER / ROE を計算（EPS が 0/欠損の場合は None）。
    - 各関数は DuckDB 上の SQL を用いて日付ウィンドウを限定して効率的に計算。
  - 特徴量探索モジュール（kabusys.research.feature_exploration）を実装:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（有効レコードが 3 件未満の場合は None を返す）。
    - rank: 同順位は平均ランクを割り当てるランク関数（丸めによる ties 判定の安定化有り）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

- AI / NLP (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）を実装:
    - calc_news_window: JST 基準でニュース集計ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算（UTC に変換した naive datetime を返す）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約し、記事テキストをトリム（記事数および文字数の上限あり）。
    - OpenAI（gpt-4o-mini）を JSON mode でバッチ呼び出しし、最大 _BATCH_SIZE（20）銘柄ずつ処理。
    - 429・ネットワーク断・タイムアウト・5xx に対するエクスポネンシャルバックオフのリトライ実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results リスト、コードの照合、数値性、有限性）と ±1.0 クリップ。
    - 成果は ai_scores テーブルへ部分置換（対象 code の DELETE → INSERT）して部分失敗時の既存スコア保護。
    - API キー注入可能（api_key 引数）でテスト容易性を確保。未設定時は ValueError を送出。

  - レジーム判定（kabusys.ai.regime_detector）を実装:
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロ経済ニュースの LLM センチメントを重み付け（MA 70% / Macro 30%）して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは raw_news からマクロキーワードでフィルタしてタイトルを LLM に渡す（最大記事数制限あり）。
    - LLM 呼び出しのリトライ・バックオフ、API 失敗時は macro_sentiment = 0.0（フェイルセーフ）。
    - レジームスコア合成後、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI クライアント生成時に api_key を注入可能。未設定時は ValueError を送出。

- ロギング・堅牢性
  - 各モジュールで詳細なログを出力（info/debug/warning/exception）。
  - DB 書き込み失敗時はトランザクションの ROLLBACK を試行し、失敗した場合は警告をログに記録。
  - ルックアヘッドバイアス防止方針を採用（datetime.today()/date.today() を直接参照しない設計を意識した実装箇所あり）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 機密情報の取得は環境変数経由を推奨（Settings でトークン／パスワードを環境変数から取得）。OpenAI API キーや外部 API トークンは明示的に渡す設計を採用。

Notes / Implementation details
- DuckDB を内部データベースに想定。関数は DuckDB 接続（DuckDBPyConnection）を受け取り SQL と Python を組み合わせて計算/書き込みを行う。
- OpenAI 呼び出しは gpt-4o-mini を使用し、JSON mode を利用して厳密な JSON レスポンスを期待する。ただし実運用上の不確実性（前後テキスト混入など）に備えた復元ロジックを持つ。
- 外部 API 呼び出しの回復性（リトライ / バックオフ）、および部分失敗時の既存データ保護（書き込み対象の絞り込み）に配慮。

今後の予定（例）
- strategy / execution / monitoring モジュールの実装とテストカバレッジ拡充。
- ai モデルの入れ替えやローカルモデル対応、評価メトリクスの追加。
- ETL の監査ログ強化・スケジューリング連携。

以上。必要に応じてリリース日や項目の粒度を調整できます。どの程度の詳細（コミット単位や担当など）を含めるか指示があれば追記します。