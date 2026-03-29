# Changelog

すべての重要な変更点をこのファイルに記録します。本ファイルは「Keep a Changelog」仕様に準拠します。

注: 日付や説明はソースコードから推測して作成しています。

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買プラットフォームのコアライブラリを実装。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージメタ情報（バージョン v0.1.0）と公開モジュール群を定義。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定をロードする自動ローダーを実装。
    - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を読み込む（配布後も動作する探索実装）。
    - export 形式、クォート内のエスケープ、インラインコメント等に対応した堅牢な .env パーサーを実装。
    - OS 環境変数の上書きを防ぐ protected セットや KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能を提供。
    - 必須変数取得ヘルパー（_require）と Settings クラスを公開。主要な期待環境変数:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH / SQLITE_PATH のデフォルトパスを定義
      - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証

- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメントを取得して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（target_date の前日 15:00 JST 〜 当日 08:30 JST）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたり記事数・文字数のトリム、レスポンスの厳格なバリデーションを実装。
    - 429 / ネットワーク切断 / タイムアウト / 5xx を対象に指数バックオフでのリトライを実装。API 失敗時はスキップして継続（フェイルセーフ）。
    - テストしやすくするため OpenAI 呼び出し関数を差し替え可能に設計（unittest.mock.patch でのモックを想定）。

  - src/kabusys/ai/regime_detector.py
    - ETF (1321) の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルに冪等的に書き込む処理を実装。
    - DuckDB クエリでのルックアヘッドバイアス回避、LLM 呼び出し失敗時のフェイルセーフ（macro_sentiment=0.0）、OpenAI API の安全なリトライ/エラーハンドリングを実装。
    - マクロキーワードフィルタと JSON レスポンスパースロジックを提供。
    - テスト用フック（OpenAI 呼び出しを差し替え可能）を提供。

- データプラットフォーム（Data）モジュール
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダーの夜間更新ジョブ（calendar_update_job）と、営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - market_calendar が未取得の場合の曜日ベースのフォールバック、DB 登録優先の一貫した判定ロジック、探索上限での例外制御を含む堅牢な実装。
    - J-Quants クライアント経由でカレンダー差分取得と保存を行い、バックフィル・健全性チェックを実装。

  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETL パイプラインの基礎（差分取得、保存、品質チェックのフロー）を実装。
    - ETLResult データクラスを公開（src/kabusys/data/etl.py から再エクスポート）。
    - DuckDB のテーブル最大日付取得、テーブル存在チェック等のユーティリティ関数を実装。
    - 保存前後のバックフィルや品質問題の集約（Fail-Fast ではなく呼び出し元での判断を想定）。

- リサーチ（研究）モジュール
  - src/kabusys/research/factor_research.py
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER/ROE）等のファクター計算関数を実装。
    - DuckDB 上の prices_daily / raw_financials を用いた SQL ベース実装で、ルックアヘッドバイアスを避ける設計。
    - 出力は (date, code) をキーにした dict のリストとして返却。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Spearman ρ）計算（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等外部依存を用いず標準ライブラリと DuckDB のみで実装。

- データユーティリティ公開
  - src/kabusys/data/__init__.py, src/kabusys/etl.py（ETLResult を再エクスポート）

- テスト・運用に配慮した設計上のフックを多数追加
  - OpenAI 呼び出しの差し替えポイント（_call_openai_api）や KABUSYS_DISABLE_AUTO_ENV_LOAD によりテストしやすさを確保。

### Changed
- （初回リリースにつき該当なし）

### Fixed / Robustness
- .env パーサーの堅牢化
  - export 構文対応、クォート内バックスラッシュエスケープの解釈、インラインコメント判定ルールの改善により多様な .env フォーマットに対応（src/kabusys/config.py）。

- OpenAI 呼び出しのエラー耐性強化
  - RateLimit / 接続エラー / タイムアウト / 5xx をリトライ対象にする一方、致命的でないエラー（パース失敗や非5xx API エラー）はフェイルセーフで中立値（0.0）にフォールバックし処理継続を保証（src/kabusys/ai/news_nlp.py、src/kabusys/ai/regime_detector.py）。

- DB 書き込みの冪等性とトランザクション安全化
  - market_regime, ai_scores 等の書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等ロジックを採用し、例外時は ROLLBACK を試行・ログ出力して上位へ例外を伝播（src/kabusys/ai/regime_detector.py、src/kabusys/ai/news_nlp.py）。
  - DuckDB executemany に対する空パラメータの回避（空リストチェック）を追加して互換性を確保。

- ルックアヘッドバイアス対策
  - 日次判定・ウィンドウ計算で datetime.today() / date.today() を直接参照しない設計を徹底（AI スコアリング・レジーム判定・ファクター計算等）。

### Notes / Migration
- 必要な環境変数（主なもの）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
  - DUCKDB_PATH / SQLITE_PATH はデフォルトで data/kabusys.duckdb / data/monitoring.db を使用（必要に応じて環境変数で変更）。

- テスト時
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動 .env ロードを無効化可能。
  - OpenAI 呼び出し部分はモック差し替えを想定して設計しているためユニットテストが可能。

### Removed / Deprecated
- （初回リリースにつき該当なし）

---

今後の予定（推測）
- モデルの追加（新しい LLM / 設定）
- ストラテジー実行・発注モジュール（execution）、モニタリング（monitoring）などの拡充
- 品質チェックルールの拡張と UI/監査ログの改善

---
この CHANGELOG はソースコードの実装内容に基づいて推測して作成しています。必要に応じて運用チームで編集・追記してください。