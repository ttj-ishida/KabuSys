# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

すべてのリリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-28

初期リリース。日本株自動売買システムのコアライブラリを公開。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイント src/kabusys/__init__.py を追加。__version__ = "0.1.0"、モジュール公開一覧を定義（data, strategy, execution, monitoring）。

- 環境・設定管理
  - src/kabusys/config.py:
    - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートを .git または pyproject.toml から検出する機能を実装（CWD 非依存）。
    - .env/.env.local の読み込み優先順位、既存 OS 環境変数を保護する protected 機構を実装。
    - .env の行パーサを実装（コメント、export プレフィックス、クォートとバックスラッシュエスケープ対応）。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供し、主要な必須設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）と検証（KABUSYS_ENV, LOG_LEVEL）を行う。
    - デフォルトのデータベースパス（duckdb, sqlite）の設定と Path 変換を提供。

- AI 関連
  - src/kabusys/ai/news_nlp.py:
    - ニュース記事に対する LLM（gpt-4o-mini）を用いたセンチメントスコアリング機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算（calc_news_window）。
    - news_symbols / raw_news を銘柄別に集約してバッチ（最大 20 銘柄）で OpenAI に投げる処理を実装。
    - 入力トリム（記事数・文字数制限）、JSON Mode を想定したレスポンス検証、score の ±1.0 クリップ、DuckDB への冪等的な書込み（DELETE → INSERT）を実装。
    - API エラー時のエクスポネンシャルバックオフリトライ、失敗時は当該チャンクをスキップするフェイルセーフ設計。
    - テスト用に内部の OpenAI 呼び出し関数を差し替え可能な設計（_call_openai_api を patch で差し替えられる）。
  - src/kabusys/ai/regime_detector.py:
    - ETF 1321（Nikkei 225 連動型）200日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能を実装。
    - ma200_ratio 計算（ルックアヘッドバイアス防止のため target_date 未満のデータのみ使用、データ不足時は中立化）。
    - マクロキーワードによる記事抽出、LLM（gpt-4o-mini）呼び出し、レスポンスの JSON パース、スコア合成、閾値によるラベル付けを実装。
    - 計算結果を market_regime テーブルへ冪等（BEGIN/DELETE/INSERT/COMMIT）で保存。
    - API 失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ挙動と、リトライ戦略を実装。

- データプラットフォーム関連
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダー管理（market_calendar）機能を実装。営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
    - DB にデータがない場合の曜日ベースフォールバック（平日＝営業日）を採用し、DB 登録値を優先する一貫した補完ロジックを実装。
    - calendar_update_job を実装し、J-Quants API（jquants_client）から差分取得して market_calendar を冪等的に保存する処理を提供。バックフィルと健全性チェックを含む。

  - src/kabusys/data/pipeline.py:
    - ETL パイプライン用ユーティリティと設計を実装（差分取得・保存・品質チェック）。
    - ETLResult dataclass を追加（取得数・保存数・品質問題・エラー等を集約）。
    - DuckDB に対する最大日付取得やテーブル存在チェックなどの内部ユーティリティを提供。
    - 市場カレンダー調整ヘルパー（_adjust_to_trading_day）等を実装。

  - src/kabusys/data/etl.py:
    - pipeline.ETLResult を再エクスポート（public API）。

  - src/kabusys/data/__init__.py:
    - data パッケージのエントリポイントを用意（将来拡張のためのプレースホルダ）。

  - jquants_client / quality など外部連携箇所は jquants_client を参照して差分取得・保存・検証を行う設計（実装は別モジュール想定）。

- リサーチ（研究向けユーティリティ）
  - src/kabusys/research/factor_research.py:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR）、Value（PER/ROE）など複数のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB SQL を活用し prices_daily / raw_financials のみを参照する安全設計。
    - 結果は (date, code) をキーとする dict のリストで返す。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）を実装。任意ホライズンの検証、ホライズンの入力検証あり。
    - IC（Information Coefficient）計算（Spearman ρ）を実装（calc_ic）。
    - ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
  - src/kabusys/research/__init__.py:
    - 主要な研究 API を再エクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### 変更 (Changed)
- 設計方針・実装上の注記（各モジュールに反映）
  - すべての AI / データ / リサーチ処理は datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス防止）。
  - DuckDB との互換性を考慮した実装（executemany に空リストを渡さない等のワークアラウンド）を適用。
  - OpenAI API 呼び出しに対する堅牢なエラーハンドリング（リトライ、5xx 判定、429/タイムアウト/ネットワーク断対応）を導入。
  - LLM レスポンスの冗長テキスト混入に備えた JSON 復元ロジックを追加（最外側の {} を抽出して再パース）。

### 修正 (Fixed)
- N/A（初期リリースのため既知のバグ修正はなし。ただし各モジュールに警告ログとフェイルセーフを追加し、実行時の頑健性を向上）。

### 注意点 / 移行ガイド (Notes / Migration)
- 環境変数
  - 以下は本機能を利用する際に必須または利用される環境変数です:
    - JQUANTS_REFRESH_TOKEN（必須、Settings.jquants_refresh_token）
    - KABU_API_PASSWORD（必須、Settings.kabu_api_password）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須、Slack 通知関連）
    - OPENAI_API_KEY（AI 機能を使う場合に必須。score_news / score_regime は引数で api_key を渡すことも可能）
    - KABUSYS_ENV: development / paper_trading / live のいずれか（デフォルト: development）
    - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
  - .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）から行われます。テストや特殊環境で自動読み込みを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI
  - gpt-4o-mini と JSON Mode を想定したプロンプト設計を行っています。API レスポンス仕様やモデルの挙動に依存するため、将来的なモデル変更時はプロンプト / レスポンス検証ロジックの見直しが必要です。
  - テスト容易性のため、内部の _call_openai_api 関数を unittest.mock.patch で差し替えてモックできます。

- DuckDB
  - executemany に空リストを渡せない（DuckDB のバージョン差）ことを考慮した実装になっています。DuckDB の互換性に関する注意点はコード内コメント参照。

- フェイルセーフ
  - LLM 呼び出し失敗時はゼロやスキップで継続する設計（サービス停止を防ぐ）。ただし失敗理由はログに残るため監視が推奨されます。

### 既知の制約 (Known limitations)
- 一部機能は jquants_client / quality / jquants API 実装に依存しており、それらのクライアント実装が必要です（このリリースでは参照のみ）。
- 現時点で PBR・配当利回り等の一部バリューファクターは未実装（calc_value は PER / ROE のみ）。
- news_nlp と regime_detector は gpt 系モデルの応答品質に依存します。長期運用時はモデル変更やプロンプトチューニングを検討してください。

---

今後のリリースでは、strategy / execution / monitoring モジュールの実装（自動売買ロジック、実際の発注ラッパー、監視・アラート機能）、テストカバレッジの強化、J-Quants クライアント実装の統合を予定しています。