# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買・データ基盤のコア機能を提供します。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py によりパッケージのエクスポートを定義（data, strategy, execution, monitoring）。
  - バージョン: 0.1.0

- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env/.env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - EXPORT 形式やクォート・エスケープ・インラインコメント等に対応した .env パーサ実装。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグをサポート。
    - 環境変数取得ユーティリティ Settings クラスを提供（必須変数チェック _require、デフォルト値、型変換、値検証）。
    - 設定例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL。

- ニュースNLP（AI）スコアリング
  - src/kabusys/ai/news_nlp.py
    - raw_news および news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へバッチ送信し、センチメントスコアを ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（JST 基準）: 前日 15:00 JST 〜 当日 08:30 JST を対象にする calc_news_window 実装。
    - バッチ処理: _BATCH_SIZE（デフォルト 20）で複数銘柄を一括処理、1銘柄当たり記事数・文字数制限を実装（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - OpenAI 呼び出しは JSON Mode を使用し、レスポンスを厳密にバリデート（results 配列・code/score 構造検査）。
    - リトライ（429, ネットワーク, タイムアウト, 5xx）に対する指数バックオフを実装（_MAX_RETRIES, _RETRY_BASE_SECONDS）。
    - レスポンスパース失敗や API 障害時はフェイルセーフでそのチャンクをスキップし、他銘柄への影響を最小化。
    - DuckDB への書き込みは冪等（DELETE → INSERT）かつトランザクション管理（BEGIN/COMMIT/ROLLBACK）。DuckDB executemany の空リスト問題に対処。
    - 公開 API: score_news(conn, target_date, api_key=None) — 書き込んだ銘柄数を返す。

- 市場レジーム判定（AI + テクニカル融合）
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp.calc_news_window と raw_news からフィルタ（マクロキーワードリストを定義）。
    - OpenAI 呼び出しは独立実装（モジュール間のプライベート関数共有を避ける）。
    - レトライ、エラーハンドリング、API 失敗時のマクロスコアフォールバック（0.0）を実装。
    - 結果は market_regime テーブルへ冪等書き込み（DELETE → INSERT をトランザクション内で実行）。
    - 公開 API: score_regime(conn, target_date, api_key=None) — 正常時 1 を返す。

- 研究（Research）モジュール
  - src/kabusys/research/__init__.py により主要関数を公開。
  - src/kabusys/research/factor_research.py
    - モメンタムファクター calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None を返す）。
    - ボラティリティ/流動性 calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（データ不足扱いあり）。
    - バリューファクター calc_value: raw_financials の最新財務データと当日の株価から PER/ROE を算出。
    - 実装は DuckDB の SQL を活用し、外部 API にはアクセスしない。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来終値リターンを計算。
    - IC（Information Coefficient）calc_ic: スピアマンのランク相関でファクター有効性を評価（有効サンプル数要件あり）。
    - ランク変換 rank: 同順位は平均ランク処理（丸め処理で ties の扱いを安定化）。
    - 統計サマリー factor_summary: count/mean/std/min/max/median を計算。

- データプラットフォーム（Data）
  - src/kabusys/data/calendar_management.py
    - market_calendar の取得・活用に基づく営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB の market_calendar が未登録または値が NULL の場合は曜日ベース（土日を非営業日）でフォールバックする設計。
    - calendar_update_job: J-Quants API（jquants_client）から差分取得して market_calendar を冪等更新、バックフィルと健全性チェックを実装。

  - src/kabusys/data/pipeline.py
    - ETLResult データクラスを導入し、ETL の取得/保存/品質チェック結果・エラー情報を集約。
    - テーブル最終日取得ユーティリティ、差分取得やバックフィル方針を実装。
    - jquants_client と quality モジュールを組合わせた ETL ワークフロー設計に沿う実装方針。

  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート。

- その他ユーティリティ / 設計上の注意点
  - DuckDB を主要なローカル OLAP ストアとして利用し、SQL と Python の組合せで高速に集計処理を行う設計。
  - 全ての「日」計算で datetime.today()/date.today() の乱用を避け、ターゲット日引数ベースでルックアヘッドバイアスを防止。
  - トランザクション保護（BEGIN/COMMIT/ROLLBACK）とログ出力により障害時の解析を容易に。
  - OpenAI 呼び出し部分はテスト用に差し替え可能（モジュール内 _call_openai_api を patch 可能に実装）。
  - 多数の防御的実装（入力検証、値のクリップ、フェイルセーフなフォールバック、詳細なログメッセージ）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは関数引数で注入可能かつ環境変数 OPENAI_API_KEY から取得する実装で、直接ハードコーディングはなし。  
- .env 自動ロード時、既存の OS 環境変数は protected として上書きを防止する挙動を持つ。

### Breaking Changes
- （初回リリースのため該当なし）

---

開発者向けメモ:
- テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して .env 自動読み込みを無効化してください。
- OpenAI 関連のユニットテストでは、各モジュールの _call_openai_api をモックすることで外部 API 依存を排除できます。