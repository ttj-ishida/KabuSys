# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このリポジトリの初回リリースを記録します。

## [0.1.0] - 2026-04-02

### 追加
- パッケージ初期構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - エクスポート: data, strategy, execution, monitoring（monitoring は名前のみ公開、実装は今後）

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルおよび環境変数から設定を自動ロードする仕組みを実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索（配布後も動作）。
  - .env パーサは以下に対応:
    - コメント行、空行の無視
    - export KEY=val 形式の対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
    - クォート無し値でのインラインコメント判定（直前が空白/タブの場合のみ）
  - .env 読み込み時に OS 環境変数を保護する protected キーセットを導入し、.env.local で上書き可能な挙動を実現。
  - Settings クラスを提供。J-Quants / kabuステーション / Slack / DB / 監視 / システム設定等をプロパティで取得。未設定の必須環境変数は ValueError を送出。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値チェック）。
  - デフォルト値: KABUSYS_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、PID_FILE_PATH、しきい値（CPU/メモリ/ディスク）等。

- AI モジュール (src/kabusys/ai/*.py)
  - ニュース NLP (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini、JSON Mode）にバッチで問い合わせてセンチメントを算出し ai_scores テーブルへ書き込む。
    - タイムウィンドウ: JST 基準で前日 15:00 ～ 当日 08:30（DB 比較のため UTC に変換して使用）。
    - バッチ処理: 1 API 呼び出しあたり最大 20 銘柄（_BATCH_SIZE=20）。
    - 1 銘柄あたり最大記事数 _MAX_ARTICLES_PER_STOCK=10、最大文字数トリム _MAX_CHARS_PER_STOCK=3000。
    - リトライ/バックオフ: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ（最大回数設定）。
    - レスポンスバリデーション: JSON パース（不正な前後テキストの切り出し対応）、results リスト/各要素の code と score 検証、未知コードは無視、スコアを ±1.0 にクリップ。
    - DB 書き込みは冪等性を重視（対象コードのみ DELETE → INSERT）。DuckDB の executemany 空リスト制約への配慮あり。
    - テスト容易性: API 呼び出し部分は _call_openai_api を分離してパッチ可能に設計。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で market_regime を算出・保存。
    - MA 計算は target_date 未満のデータのみ使用しルックアヘッドバイアスを防止。
    - マクロニュース抽出は news_nlp.calc_news_window に基づくウィンドウでマクロキーワードでフィルタ。
    - OpenAI 呼び出し時はリトライ・バックオフを導入。API 失敗時は macro_sentiment=0.0 をフェイルセーフとして使用。
    - レジームスコアの閾値（bull/bear/neutral）およびスコア合成ロジックを実装。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT で冪等化。失敗時は ROLLBACK を試行して上位へ例外を伝播。

- データ処理 (src/kabusys/data/*.py)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを使った営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがある場合は DB 値を優先、未登録日は曜日ベース（週末除外）でフォールバック。最大探索範囲を制限して無限ループを回避。
    - 夜間バッチ calendar_update_job を実装。J-Quants API から差分取得し save_market_calendar を呼び出して保存、バックフィルと健全性チェックを実装。

  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを実装し ETL 実行結果の集約・辞書変換メソッドを提供（品質問題・エラー一覧の保持）。
    - 差分更新・バックフィル・品質チェックを想定した設計（jquants_client と quality モジュールを利用する仕様）。
    - data/etl は pipeline.ETLResult を再エクスポート。

  - ユーティリティ: DuckDB テーブル存在チェックなどの内部ユーティリティを提供。

- リサーチ機能 (src/kabusys/research/*.py)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum, Volatility, Value, Liquidity 等の定量ファクター計算を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日データ不足時は None）
      - calc_volatility: 20 日 ATR（atr_20）、相対ATR（atr_pct）、20 日平均売買代金、出来高比率
      - calc_value: raw_financials から直近財務データを取得して PER, ROE を計算（EPS 0/欠損時は None）
    - すべて DuckDB の SQL を用いた実装で、外部 API へはアクセスしない。

  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の妥当性チェックあり。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満の場合は None。
    - rank: 同順位は平均ランクを返すランク化ユーティリティ（丸め処理で ties の誤検出を抑制）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
    - これらは標準ライブラリと DuckDB のみで実装され、研究用途での独立実行を想定。

### 変更
- 初期リリースのため該当なし。

### 修正
- 初期リリースのため該当なし。

### 既知の注意点 / 設計上のポイント
- 多くの関数は内部で datetime.today()/date.today() を参照しないよう設計されており、外部から target_date を注入することが想定されている（ルックアヘッドバイアス防止）。
- OpenAI API 呼び出し部分はテストで差し替え可能（モック用フックあり）。
- DuckDB の executemany に対する空リスト制約に注意して実装（空時は実行をスキップ）。
- .env の自動読み込みはデフォルトで有効だが、CI/テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- 一部モジュール（例: monitoring）の実装は今後の追加を予定（現時点では公開名のみ）。

### セキュリティ
- 必須のシークレット（OpenAI API キー、SLACK_BOT_TOKEN、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）は Settings のプロパティで取得時に未設定なら ValueError を発生させる仕様。実運用時は環境変数または .env にて適切に管理してください。

--- 

この CHANGELOG はコードベースの実装内容から推測して作成しました。実際のコミット履歴やリリースノートがある場合はそちらを優先してください。