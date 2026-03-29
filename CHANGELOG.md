# Changelog

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
リリースはセマンティックバージョニングに従います。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-29
最初の公開リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージの初期化
  - kabusys パッケージの __version__ = "0.1.0" を追加。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に登録。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から探索して検出。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーを実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートを考慮した値の取り扱い（バックスラッシュエスケープ対応）。
    - コメント処理（クォートなし時は # の前が空白/タブならコメントと判断）。
  - 設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須設定として取得（未設定時は ValueError）。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等のデフォルト提供。
    - KABUSYS_ENV / LOG_LEVEL の値検証とユーティリティプロパティ（is_live / is_paper / is_dev）。

- データ関連ユーティリティ (src/kabusys/data/)
  - calendar_management.py
    - 市場カレンダー管理（market_calendar テーブルの参照/更新、営業日判定、next/prev/get_trading_days、is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック。
    - calendar_update_job: J-Quants API からの差分取得と冪等保存（バックフィル、健全性チェックを含む）。
  - pipeline.py / etl.py
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラー情報を保持）。
    - ETL パイプラインヘルパー（最終取得日チェック、差分取得、品質チェックの枠組み）。
    - etl モジュールで ETLResult を公開（再エクスポート）。

- リサーチ機能 (src/kabusys/research/)
  - factor_research.py
    - Momentum / Volatility / Value 等のファクター計算実装:
      - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を計算。
      - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
      - calc_value: PER, ROE を raw_financials と prices_daily から計算。
    - DuckDB を用いた SQL 中心の実装。
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターンを計算（複数ホライズン対応）。
    - calc_ic: スピアマン順位相関（IC）を計算。
    - rank: 平均ランク処理（同順位は平均ランク）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
  - research パッケージの __all__ を設定。

- AI（自然言語処理）機能 (src/kabusys/ai/)
  - news_nlp.py
    - raw_news を銘柄ごとに集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄ごとのセンチメント ai_score を生成。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window として実装。
    - 1チャンク最大 20 銘柄、記事トリム（最大記事数・文字数）機能を実装。
    - API 呼び出しの堅牢化: 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ。
    - レスポンス検証と復元ロジック（JSON モードでも前後ノイズが生じた場合の {} 抽出）。
    - DuckDB の executemany に関する互換性考慮（空リスト処理回避）。
    - API 呼び出しを差し替え可能（テスト用に _call_openai_api を patch 可能）。
  - regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull / neutral / bear）を算出する score_regime を実装。
    - マクロニュース抽出（キーワードフィルタ）、OpenAI 呼び出し、リトライ、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - レジーム判定結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）し、DB 書込み失敗時はロールバック。
    - ルックアヘッドバイアス回避を明示した設計（datetime.today() を参照しない、クエリは date < target_date を採用）。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### セキュリティ (Security)
- なし（初回リリース）

### 実装上の注意点（ドキュメント的に重要）
- ルックアヘッドバイアス防止
  - AI 周り・リサーチ関数は内部で datetime.today() / date.today() を参照せず、引数として与える target_date に基づいて処理します。バッチ/バックテストでの再現性と公正性を重視。
- フェイルセーフ設計
  - OpenAI API の失敗やレスポンスパース失敗は例外を投げずに安全なデフォルト（スコア 0.0、該当銘柄スキップ等）で継続するよう設計されています。これにより外部 API の不安定さが全体の停止に繋がらないようにしています。
- DuckDB 互換性
  - executemany に空リストを渡すと問題になるため、空チェックを行ってから実行します。
- テスト容易性
  - AI 呼び出し箇所（_kabusys.ai.news_nlp._call_openai_api、kabusys.ai.regime_detector._call_openai_api）をテストでモック可能な設計にしています。
- DB 書き込みの冪等性
  - market_regime / ai_scores 等の書き込みは既存行削除 → 挿入の形式で冪等性を確保し、トランザクション（BEGIN/COMMIT/ROLLBACK）で整合性を保持します。

---

貢献・バグ報告・改善提案は issue を通してください。