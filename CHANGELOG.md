# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-03-31

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py: パッケージ説明と __version__ = "0.1.0"、公開サブパッケージ一覧 (__all__) を定義。

- 設定・環境変数管理機能
  - src/kabusys/config.py
    - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト向け）。
    - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、インラインコメントの取り扱いなどを考慮。
    - 環境変数保護: OS の既存環境変数は protected として上書き防止（.env.local の override オプションを適用する際も考慮）。
    - Settings クラスを公開（settings インスタンス）。以下のプロパティを提供:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
      - KABUSYS_ENV 検証（development, paper_trading, live のみ許容）
      - LOG_LEVEL 検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）
      - is_live / is_paper / is_dev ヘルパー

- AI ニュース・レジーム判定機能
  - src/kabusys/ai/news_nlp.py
    - news 記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）を用いてセンチメント（-1.0〜1.0）を評価して ai_scores テーブルへ書き込む処理を実装。
    - 処理内容:
      - 対象ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST、内部は UTC naive datetime を使用）
      - 銘柄ごとに最新 N 件の記事を結合してトリム（最大記事数・最大文字数で制限）
      - 最大 BATCH_SIZE = 20 銘柄単位でバッチ送信
      - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ
      - レスポンスバリデーション（JSON 抽出、results 配列、code と score の扱い、スコアの数値化とクリップ）
      - DuckDB への冪等書き込み（DELETE → INSERT、空 params に対する DuckDB 0.10 の制約を回避）
    - フェイルセーフ: API 失敗やパース失敗時は該当チャンク/銘柄をスキップし、処理を継続（例外を投げない設計）。OpenAI API キー未設定時は ValueError を送出。

  - src/kabusys/ai/regime_detector.py
    - 日次の市場レジーム判定（bull / neutral / bear）を実装。
    - 手法:
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成
      - LLM は micro/macro ニュースを gpt-4o-mini に投げ、JSON で {"macro_sentiment": float} を期待
      - スコア合成後 clip(-1,1) → 閾値によりラベル化
      - 結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - 設計上の注意:
      - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない
      - LLM 呼び出し失敗時は macro_sentiment = 0.0 で継続（フェイルセーフ）
      - OpenAI API 呼び出し用のリトライ（429, 接続エラー, タイムアウト, 5xx）を実装

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value / Liquidity 等のファクター計算を実装。
    - 提供関数:
      - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日 MA 乖離率（データ不足時は None を返す）
      - calc_volatility(conn, target_date): 20日 ATR、ATR 比率、20日平均売買代金、出来高比率 など
      - calc_value(conn, target_date): PER（EPS が無効なら None）、ROE（raw_financials 参照）
    - DuckDB SQL を活用した実装で、prices_daily / raw_financials のみ参照。外部 API にアクセスしない。

  - src/kabusys/research/feature_exploration.py
    - 特徴量探索ユーティリティを実装:
      - calc_forward_returns(conn, target_date, horizons): 将来リターン計算（horizons デフォルト [1,5,21]）
      - calc_ic(factors, forwards, factor_col, return_col): スピアマンのランク相関（IC）計算、データ不足時は None を返す
      - rank(values): 同順位は平均ランクを使用するランク化ユーティリティ
      - factor_summary(records, columns): count/mean/std/min/max/median を計算
    - pandas 等の外部ライブラリに依存せず標準ライブラリ + DuckDB のみで実装。

  - src/kabusys/research/__init__.py で主要関数を再エクスポート（使いやすさ向上）。

- データプラットフォーム（Data）機能
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
      - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等更新（バックフィル・健全性チェック含む）
    - カレンダーデータがない場合は曜日ベース（平日のみ営業日）でフォールバックする一貫したロジックを採用。
    - 最大探索範囲 (_MAX_SEARCH_DAYS) により無限ループを防止。

  - src/kabusys/data/pipeline.py
    - ETL パイプラインのユーティリティと補助関数を実装:
      - ETLResult データクラスを定義（取得件数・保存件数・品質チェック問題・エラーメッセージ等を保持）
      - 差分更新ロジックの補助（テーブル存在確認・最大日付取得など）
      - デフォルトのバックフィル日数・カレンダー先読み等の定数を定義
    - ETL の設計方針として、品質チェックは結果を収集するが処理を止めない（呼び出し元で対応判断）。

  - src/kabusys/data/etl.py
    - ETLResult を再エクスポートして公開インターフェースを提供。

  - データクライアント連携
    - calendar_management, pipeline は kabusys.data.jquants_client（別モジュール）経由で J-Quants とのやり取りを想定（fetch/save の呼び出しを抽象化）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 実装上の注意点（ドキュメント的補足）
- OpenAI 関連
  - API 呼び出しは OpenAI SDK の Chat Completions を使用（モデル gpt-4o-mini、JSON Mode を利用）。
  - テスト時は _call_openai_api をパッチで差し替え可能（unittest.mock.patch を想定）。
  - レスポンスパースに失敗してもシステム全体を止めない（多くのケースでスコアを 0 またはスキップして継続）。

- DuckDB との相互作用
  - executemany に空リストを渡すとエラーになる DuckDB 0.10 の振る舞いを回避するため、明示的に空チェックを実施してから executemany を呼ぶ実装になっている。

- ルックアヘッドバイアス防止
  - すべての日次計算（ニュースウィンドウ、移動平均計算、ETL の対象日決定等）において、date.today()/datetime.today() を直接参照しない設計指針を採用。外部から target_date を与えることで過去データのみを参照する安全な処理を実現。

### Security
- 機密情報（API キー等）は Settings.require によるチェックで未設定時に明示的にエラーを出す。自動でログ出力等に流さないよう注意しているが、運用時は環境変数の管理に注意してください。

---

今後のリリースでは、以下のような追加・改善を予定しています（参考）
- strategy / execution / monitoring パッケージ内のトレード実行ロジックと監視機能の実装／公開
- テストカバレッジ・CI の整備、OpenAI レスポンスのより堅牢な検証・プロンプト改善
- J-Quants / kabu API クライアントの実装詳細とエラー処理の強化

もし CHANGELOG に追加してほしい項目や、記載内容の修正希望があれば教えてください。