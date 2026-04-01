CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは Keep a Changelog の慣例に準拠しています。

[0.1.0] - 2026-04-01
-------------------

Added
- 初期リリース。kabusys パッケージの基本機能群を追加。
- パッケージメタ:
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - パッケージ公開用のサブモジュールエクスポート設定 (__all__ に data, strategy, execution, monitoring を含む)。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読取る Settings クラスを追加（settings インスタンスを公開）。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から探索して .env, .env.local を読み込む。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - 読み込み時に OS の既存環境変数（protected set）を保護するオプションを実装。
  - 必須環境変数取得ヘルパ _require を用意。未設定時は ValueError を送出。
  - Settings が提供する主要プロパティ:
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値（CPU/MEM/DISK）/ PID ファイルパス / 環境 (development|paper_trading|live) / ログレベル。
    - env / log_level の値検証（許容値チェック）と is_live / is_paper / is_dev の利便性プロパティ。
  - デフォルト値やパスの展開（Path.expanduser）に対応。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を使い、銘柄ごとにニュースを集約して OpenAI に一括送信しセンチメントを算出、ai_scores テーブルへ書き込み。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して取得（calc_news_window を提供）。
    - バッチ処理: 最大 20 銘柄/チャンク、1銘柄あたり記事最大 10 件・最大 3000 文字でトリム。
    - OpenAI（gpt-4o-mini, JSON Mode）呼び出しに対するリトライ（429 / ネットワーク断 / タイムアウト / 5xx）を実装。指数バックオフを採用。
    - レスポンスの厳格なバリデーション（JSON 抽出、results 配列、code/score 検証、未知コード無視、数値チェック）。
    - スコアは ±1.0 にクリップ。部分失敗時に既存スコアを消さないように ai_scores の置換は該当 code のみ DELETE → INSERT。
    - テスト用に _call_openai_api を patch できる設計。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で market_regime を算出・格納。
    - マクロニュース抽出は定義済みキーワード群に基づくフィルタリング（最大 20 記事）。
    - OpenAI 呼び出し（gpt-4o-mini）およびリトライ・フォールバック戦略を実装。API 失敗時は macro_sentiment=0.0 を使用して継続。
    - スコア合成はクリップ処理後に regime_label を決定（'bull'/'neutral'/'bear'）。DB 書き込みは冪等性を意識したトランザクション（BEGIN/DELETE/INSERT/COMMIT）処理。
    - テスト用に _call_openai_api を patch できる設計。
  - ニュース NLP とレジーム判定双方で「レスポンスパース失敗や API 異常は例外を投げずフォールバックする」フェイルセーフ設計。

- データプラットフォーム (src/kabusys/data)
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを導入（取得件数、保存件数、品質検査結果、エラー一覧などを格納）。
    - 差分更新・backfill・品質チェックを行う想定のパイプライン設計を反映（J-Quants クライアントとの連携）。
    - _table_exists / _get_max_date 等の内部ユーティリティを実装（DuckDB 前提）。
    - etl モジュールは pipeline.ETLResult を再エクスポート。
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを用いた営業日判定ユーティリティ群:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダー情報がない場合は曜日（週末）ベースのフォールバックを行い、一貫性を維持。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存するジョブを実装。バックフィルや健全性チェック（将来日付の異常検知）を備える。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) により無限ループ防止。

- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン・200日 MA 乖離を計算（prices_daily の window を SQL で取得）。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。true_range 計算で NULL 伝播を厳密に制御。
    - calc_value: raw_financials の最新財務情報と当日の株価を組み合わせて PER / ROE を計算（EPS が 0 または NULL の場合は None）。
    - 設計方針: DuckDB 上で SQL + Python により完結、外部サービスへアクセスしない。
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）に対する将来リターンを LEAD で一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足（有効レコード < 3）時は None を返す。
    - rank: 同順位は平均ランクで処理（round を用いて ties 検出の安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
  - research パッケージの __init__ で主要関数を再エクスポート。

Changed
- （初回リリースのため変更履歴はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Security
- 環境変数（API キー等）は Settings 経由で取得し、未設定時は明確に例外を出す（OpenAI, Slack, kabu 等の必須キーについて）。.env 自動ロード時には既存 OS 環境変数を保護する仕組みを導入。

Notes / 本リリースの設計上の重要ポイント
- ルックアヘッドバイアス回避:
  - news・regime・research のすべての処理で datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を受け取る設計になっています（テスト容易性とデータリーク防止）。
- OpenAI 呼び出し:
  - gpt-4o-mini を使用し JSON Mode を想定。レスポンスパースの堅牢化・リトライ・バックオフ・部分失敗のフェイルセーフを実装。
  - テスト容易性のため各モジュールの内部 API 呼び出し関数を patch 可能にしている（ユニットテストでの差替えを考慮）。
- DuckDB 前提:
  - 多くの処理は DuckDB 接続（DuckDBPyConnection）を前提としており、SQL 内にウィンドウ関数等を使用。DuckDB のバージョン依存（executemany の空リスト取り扱い等）に注意。
- DB 書き込みは冪等性を意識:
  - market_regime / ai_scores / calendar 等への書き込みは DELETE → INSERT や ON CONFLICT の方針で既存データの保護と再実行耐性を考慮。
- ロギング:
  - 異常系では警告や情報ログを多用してフォールバック動作を明示する設計。

Requirements / 前提
- DuckDB Python バインディング
- openai Python SDK（OpenAI クライアント）および有効な OPENAI_API_KEY
- J-Quants クライアント（kabusys.data.jquants_client として想定された実装）
- （運用）.env による機密情報管理または環境変数設定

既知の制約 / TODO（初期リリース段階の注意点）
- 一部の品質チェック / ETL の具体的なデータ品質ルールは quality モジュールに依存しており、環境によっては追加実装が必要。
- PBR・配当利回りなどのバリューファクターは未実装（calc_value で明記）。
- DuckDB のバージョン差異に起因する挙動（executemany の空パラメータ等）に注意して運用・テストを行ってください。

---

将来的なリリースでは、バグ修正、性能改善、追加ファクター、GUI/CLI ツール、監視・アラートの強化などを予定しています。