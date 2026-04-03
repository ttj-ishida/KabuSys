# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは「Keep a Changelog」形式に準拠しており、セマンティックバージョニングに従います。

- リリースノートの対象はソースツリーの内容から推測して作成しています（手動編集や追加の履歴は含まれません）。
- バージョンはパッケージの __version__（src/kabusys/__init__.py）を参照しています。

## [Unreleased]

## [0.1.0] - 2026-04-03

初回公開リリース。日本株自動売買プラットフォーム「KabuSys」のコアライブラリを提供します。
主な機能、設計方針、注意点は以下のとおりです。

### 追加 (Added)
- パッケージ基本構成
  - kabusys パッケージを導入。公開 API として data, strategy, execution, monitoring を __all__ に定義。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定値を自動ロード（プロジェクトルートの検出に .git / pyproject.toml を使用）。
  - .env/.env.local の読み込み順序と override ロジックを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
  - 必須環境変数チェック（_require）および Settings クラスを提供。主要な設定:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY（APIキー）、LINE_CHANNEL_ACCESS_TOKEN 等
  - 各種デフォルトパスを提供（DuckDB, SQLite, PID/KILL フラグなど）。
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL のバリデーション。

- AI モジュール (src/kabusys/ai)
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてニュースセンチメントを銘柄単位に評価。
    - バッチ処理（最大 20 銘柄/チャンク）、トリム（記事数・文字数上限）、リトライと指数バックオフ実装。
    - レスポンスの厳格なバリデーション（JSON 抽出、results 配列、code/score 検査）とスコアのクリップ（±1.0）。
    - 成功した銘柄のみ ai_scores テーブルへ置換的に書き込み（DELETE → INSERT）。部分失敗時に既存スコアを保護する実装。
    - 時間ウィンドウは JST 基準（前日 15:00 〜 当日 08:30）を UTC に変換して処理。ルックアヘッドバイアス対策済み。

  - regime_detector.score_regime
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、ニュース NLU（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - OpenAI（gpt-4o-mini）でマクロセンチメントを算出（マクロキーワードでタイトルを抽出）。
    - API エラー時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフ動作。
    - 計算結果を market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- データプラットフォーム (src/kabusys/data)
  - calendar_management
    - JPX マーケットカレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar テーブルがない場合は曜日ベース（平日のみ営業日）にフォールバック。
    - 夜間バッチ calendar_update_job を提供（J-Quants API から差分取得、バックフィル、健全性チェック）。
  - pipeline / etl
    - ETLResult データクラスを公開（ETL の取得・保存件数、品質チェック結果、エラー収集を保持）。
    - ETL パイプライン設計に基づく差分更新・品質チェック・idempotent 保存の方針を実装するための基盤コード（jquants_client 依存）。
  - jquants_client 呼び出しを前提にした差分取得・保存の設計。

- リサーチ / ファクター (src/kabusys/research)
  - factor_research
    - Momentum: 1M/3M/6M リターン、ma200 乖離（ma200_dev）。
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - Value: PER（EPS が 0/NULL の場合は None）、ROE（raw_financials より取得）。
    - DuckDB を用いた SQL ベースの計算で、結果を (date, code) 形式の dict リストで返却。
  - feature_exploration
    - calc_forward_returns: 将来リターン（horizons デフォルト [1,5,21]）を計算。
    - calc_ic: スピアマンランク相関（IC）を計算。
    - factor_summary / rank: 統計要約・ランク変換を提供。
  - データ依存: prices_daily / raw_financials テーブルを使用。外部 API へはアクセスしない実装。

### 変更 (Changed)
- 全体設計方針として「ルックアヘッドバイアス回避」を徹底
  - datetime.today() / date.today() を主要処理内部で参照せず、呼び出し側が target_date を渡す設計。
  - DB クエリでは target_date 未満 / 排他条件等で将来データの参照を避ける実装が反映。

- OpenAI 呼び出しに関する振る舞い
  - JSON Mode を利用し厳密な JSON レスポンスを期待するが、余計な前後テキスト混入時に中括弧を抽出して復元する耐性を実装。
  - news_nlp と regime_detector で内部の _call_openai_api は意図的に別実装に分離（モジュール結合の低減、テスト差し替え容易化）。

- DuckDB 周りの互換性対応
  - executemany に空リストを渡せない DuckDB (0.10 系) の制限を考慮し、空チェックを行ってから executemany を呼ぶ実装。

### 修正 (Fixed)
- APIエラー・ネットワーク障害時のフェイルセーフとリトライ
  - RateLimitError / APIConnectionError / APITimeoutError / APIError（5xx）に対する指数バックオフでのリトライを主要箇所で実装。
  - リトライ全消費時は警告ログを出し、代替値（0.0）で継続する等、処理の停止を避ける安全装置を導入。

- DB 書き込み時の冪等性確保
  - market_regime / ai_scores などで、対象日の既存行を削除してから挿入することで冪等保存を実現。
  - ロールバックの失敗時にログ出力を行う保険処理を追加。

### ドキュメント・設計注記 (Documentation)
- 各モジュールに詳細な docstring を付与。処理フロー・設計方針・例外ハンドリングの意図を明文化。
- news_nlp / regime_detector / pipeline / calendar_management 等で処理フローを冒頭にまとめて明示。

### 既知の制限 (Known issues / Limitations)
- OpenAI API（gpt-4o-mini）への依存があるため、APIキー（OPENAI_API_KEY）およびネットワークアクセスが必須。
- jquants_client（Data / ETL）が実装済みであることを前提としている（外部モジュールへの依存）。
- 一部の操作は DuckDB スキーマ（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials, news_symbols 等）を前提としている。スキーマ整備が必要。
- strategy / execution / monitoring の具体的な実装は当リリースではパッケージ公開の形で名前空間が準備されているものの、詳細な発注ロジックや監視エージェントの完全実装は将来の追加を想定。

### 互換性 (Compatibility)
- DuckDB を主要なローカルデータストアとして利用。DuckDB バージョン差異により一部バインド方法（リストバインド vs executemany）の対応が必要となる可能性あり。
- Python 3.10+（型注釈に | を使用）を想定。

### セキュリティ (Security)
- 環境変数に API キーやパスワードを保持する方式を採用。運用では SECRET 管理・アクセス制御を推奨。
- 自動 .env 読み込みはデフォルトで有効だが、テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止可能。

---

作成にあたってソースコード内の docstring / コメントと命名規則から機能と設計意図を推測して記載しています。実際のリリースノートを作成する際は、追加で以下を記載することを推奨します:
- 実際に導入した外部依存（ライブラリとそのバージョン）
- 必須環境変数一覧と推奨設定例（.env.example）
- DB スキーマ / テーブル定義（最小限のセットアップ手順）
- マイグレーション手順（今後のバージョンでスキーマ変更がある場合）

必要であれば、上記補足情報をコードベースから抽出して CHANGES に追記します。どのレベルの詳細を追加したいか教えてください。