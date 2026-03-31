CHANGELOG
=========

すべての重要な変更は常にこのファイルに記録します。

フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。
最新リリースは下記の通りです。

[0.1.0] - 2026-03-31
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基礎機能群を追加。
- パッケージ公開情報:
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - エクスポート: data, strategy, execution, monitoring を公開。
- 設定管理 (src/kabusys/config.py):
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を探索）。
  - 読み込み順序: OS環境変数 > .env.local > .env。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ: export KEY=val 形式、クォート内のバックスラッシュエスケープ、行コメントの処理などをサポート。
  - 上書き制御: override フラグと protected セット（OS 環境変数保護）を実装。
  - Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の必須取得ヘルパー。
    - KABU_API_BASE_URL のデフォルト (http://localhost:18080/kabusapi)。
    - DBパスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
    - KABUSYS_ENV 検証 (development, paper_trading, live) と LOG_LEVEL 検証 (DEBUG/INFO/WARNING/ERROR/CRITICAL)。
    - is_live / is_paper / is_dev の補助プロパティ。
- AI モジュール (src/kabusys/ai):
  - ニュース・NLP スコアリング (src/kabusys/ai/news_nlp.py):
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI (gpt-4o-mini) の JSON モードでセンチメントを取得。
    - チャンク処理: 1 API コール当たり最大 20 銘柄（_BATCH_SIZE=20）。
    - 1銘柄内は最大 10 記事、最大 3000 文字でトリム。
    - タイムウィンドウ: JST 前日15:00〜当日08:30（DB比較用に UTC 無タイムゾーンで算出）。
    - レスポンスの厳密なバリデーションと ±1.0 のクリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - 部分成功を許容する安全な DB 書き込み (DELETE → INSERT、対象コードのみ置換)。
    - テスト用に _call_openai_api をモック可能。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py):
    - ETF 1321 の 200 日移動平均乖離 (重み 70%) とマクロニュース LLM センチメント (重み 30%) を合成し、日次でレジーム (bull/neutral/bear) を判定。
    - MA 計算は target_date 未満のデータのみ使用しルックアヘッドバイアスを回避。
    - マクロニュースは news_nlp の calc_news_window を利用して対象記事を抽出。
    - OpenAI 呼び出しのリトライ・フォールバック実装（API失敗時は macro_sentiment=0.0）。
    - 結果を market_regime テーブルへ冪等的に書き込む (BEGIN / DELETE / INSERT / COMMIT + ROLLBACK 保護)。
    - テスト用に _call_openai_api を差し替え可能。
- データプラットフォーム (src/kabusys/data):
  - カレンダー管理 (src/kabusys/data/calendar_management.py):
    - JPX カレンダーの夜間バッチ更新処理 calendar_update_job を実装（J-Quants クライアント経由で差分取得 → 保存）。
    - バックフィル (直近 _BACKFILL_DAYS 日間を再取得)、先読み (_CALENDAR_LOOKAHEAD_DAYS=90)、健全性チェック (_SANITY_MAX_FUTURE_DAYS) を実装。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB にカレンダーがない場合は曜日（週末）ベースでフォールバックする一貫した挙動。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) により無限ループを防止。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py):
    - 差分更新・保存・品質チェックのワークフロー設計に沿った ETLResult dataclass を追加（ETL 実行結果の集約）。
    - _get_max_date / _table_exists 等のユーティリティを実装。
    - デフォルトのバックフィル日数・最小データ日を定義。
    - 品質チェックは重大度を返して呼び出し元に判断を委ねる（Fail-Fast ではない）。
    - etl モジュールは ETLResult を再エクスポート。
  - jquants_client 連携を想定した実装（calendar_management と pipeline で利用）。
- Research モジュール (src/kabusys/research):
  - ファクター計算 (src/kabusys/research/factor_research.py):
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - Volatility / Liquidity: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率等。
    - Value: PER、ROE（raw_financials から最新レコードを取得して計算）。
    - DuckDB の SQL ウィンドウ関数を活用し、欠損/データ不足時は None を返す挙動。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py):
    - 将来リターン計算 (calc_forward_returns)：任意ホライズン（デフォルト [1,5,21]）に対応、引数検証あり。
    - IC（Information Coefficient）計算 (calc_ic)：Spearman（ランク相関）を実装。3 銘柄未満で None を返す。
    - ランク関数 (rank)：同順位は平均ランクにし、丸めで ties を安定化。
    - 統計サマリー (factor_summary)：count/mean/std/min/max/median を計算。
  - research パッケージの __all__ で主要関数を公開。
- データユーティリティ:
  - zscore_normalize を kabusys.data.stats より再エクスポート（research/__init__.py）。

Changed
- 設計方針・安全性に重点を置いた実装:
  - すべての AI / ニュース / レジーム計算モジュールは datetime.today()/date.today() を直接参照せず、外部から target_date を受け取ることでルックアヘッドバイアスを排除。
  - OpenAI 呼び出しは JSON モードを利用し、レスポンスのバリデーションやパースエラー時のフェールセーフ処理を徹底。
  - DB 書き込みは冪等性を重視（DELETE → INSERT の構成）、トランザクション/ROLLBACK の保護を実装。
  - DuckDB のバージョン差異に配慮した実装（executemany に空リストを与えない等の互換性処理）。
- ロギング: 各モジュールで詳細な debug/info/warning ログを追加し、運用時の観測性を向上。

Fixed
- API エラー処理の改善:
  - OpenAI SDK の APIError に対して status_code の有無を安全に扱うロジックを追加し、5xx はリトライ対象、その他はフォールバックするように修正。
- JSON パースの堅牢化:
  - JSON mode でも余計な前後テキストが混入するケースを考慮し、最外の {} を抽出して復元するロジックを追加（news_nlp._validate_and_extract）。

Security
- 環境変数の取り扱い:
  - Settings._require により必須トークンの未設定時に明確なエラーを出力。
  - .env の自動ロード時に OS 環境変数を protected として上書きを防止（.env.local は override=True だが protected を尊重）。

Notes / Implementation details
- OpenAI モデルは gpt-4o-mini を使用する想定（_MODEL 定数）。
- ニュース窓口の UTC 変換は calc_news_window にて実装（JST 前日15:00〜当日08:30 を UTC 換算）。
- AI スコア・レジームスコアはそれぞれ ±1.0 にクリップして保存。
- テスト容易性のため、OpenAI 呼び出し箇所は個別関数化して unittest.mock.patch により差し替え可能。
- DuckDB 接続を前提とした純粋な SQL/標準ライブラリベースの実装で、外部依存（pandas 等）は意図的に排除。

既知の制約 / 今後の課題
- PBR・配当利回りなどのバリューファクターは未実装。
- news_nlp の出力が完全に正しい JSON で返らないケースがあり得るため、パースロジックは保守的に実装しているが実運用でさらなるチューニングが必要になる可能性あり。
- DuckDB のバージョン差異に起因するバインド挙動は今後のリリースでさらにテスト・改善予定。

履歴の追加・修正について
- 次回以降のリリースからは Unreleased セクションを用いて開発中の変更を逐次記録してください。