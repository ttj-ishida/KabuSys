# CHANGELOG

すべての注目に値する変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在のバージョン: 0.1.0

## [Unreleased]
（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買・研究プラットフォームのコア機能を実装しました。

### 追加
- パッケージ基盤
  - kabusys Python パッケージの骨格を追加（src/kabusys/__init__.py）。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring をエクスポート。

- 設定管理（src/kabusys/config.py）
  - .env / .env.local / OS 環境変数からの設定自動読み込みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト用）。
    - プロジェクトルート検出は __file__ 基準で .git / pyproject.toml を探索（CWD 非依存）。
  - .env ファイルの堅牢なパーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
  - 環境変数の保護（読み込み時に既存 OS 環境変数を protected として上書き禁止）実装。
  - Settings クラスを提供:
    - J-Quants / kabu ステーション / Slack / DB パスなどのプロパティ（必須変数は未設定時に ValueError を送出）。
    - KABUSYS_ENV 値検証（development / paper_trading / live のみ許容）。
    - LOG_LEVEL 値検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - is_live / is_paper / is_dev ヘルパー。

- データプラットフォーム（src/kabusys/data/*）
  - カレンダー管理（calendar_management.py）
    - JPX カレンダーの扱い（market_calendar テーブル）とフォールバック（曜日ベース）を実装。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - 夜間バッチ calendar_update_job：J-Quants API から差分取得し冪等的に保存、バックフィル／健全性チェック実装。
  - ETL パイプライン（pipeline.py）
    - ETLResult データクラスを追加（ETL結果の集約、品質チェック情報、エラー管理を含む）。
    - 差分更新、バックフィル方針、品質チェック設計を反映。
  - etl モジュールは pipeline.ETLResult を再エクスポート（src/kabusys/data/etl.py）。

- AI（src/kabusys/ai/*）
  - ニュース NLP（news_nlp.py）
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを判定。
    - バッチ処理（最大20銘柄）、1銘柄あたりの記事上限／文字数トリム、JSON Mode を利用するプロンプト設計。
    - 再試行・指数バックオフ（429／ネットワーク断／タイムアウト／5xx 対応）。
    - レスポンスの厳密バリデーション（JSON 抽出・results 検証・未知コード無視・数値チェック）。
    - スコア ±1.0 にクリップ、ai_scores テーブルへ部分的に置換（DELETE → INSERT）して冪等性を確保。
    - calc_news_window（JST に基づくニュース集計ウィンドウ）を実装。
    - score_news API を公開（テスト用に _call_openai_api をパッチ可能）。
  - 市場レジーム判定（regime_detector.py）
    - ETF 1321 の200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し、市場レジーム（bull/neutral/bear）を日次判定。
    - マクロキーワードによる記事抽出、OpenAI 呼び出し（gpt-4o-mini）、再試行・バックオフ、フェイルセーフ（API失敗時 macro_sentiment=0.0）。
    - レジームスコアを market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能に設計。

- リサーチ（src/kabusys/research/*）
  - ファクター計算（factor_research.py）
    - Momentum（1M/3M/6M リターン, ma200乖離）、Volatility（20日 ATR 他）、Value（PER, ROE）を DuckDB SQL ベースで実装。
    - データ不足ハンドリング（一定行数未満で None を返す等）。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（任意ホライズン、上限チェック）、IC（Spearman／ランク相関）計算、ランク変換（同順位は平均ランク）、ファクター統計サマリーを実装。
    - pandas 等に依存せず標準ライブラリ + duckdb で実装。
  - research パッケージの公開 API に主要関数を追加（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize の再エクスポート等）。

- ロギング・設計上の配慮
  - すべての AI / ETL / calendar モジュールで詳細なログ出力（info/warning/debug）を追加。
  - ルックアヘッドバイアス防止の設計: datetime.today() / date.today() を直接参照しない関数設計を採用（target_date を明示的に受け取る）。
  - DuckDB を主要 DB 層として使用。executemany に空リストを渡せないバージョンへの互換性も考慮して条件分岐を実装。

### 修正
- .env パーサの堅牢化
  - クォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメント判定の改善により実運用の .env 記述に耐性を向上。
- DuckDB 互換性処理
  - executemany に空リストを渡せないケースへのガード（空チェック）を追加し、部分失敗時の既存データ保護を強化。
- OpenAI API エラーハンドリングの改良
  - APIError の status_code の有無に対応した安全な判定、5xx とそれ以外の扱いを明確化（リトライ対象の分離）。

### その他（ドキュメント・設計）
- 各モジュールに詳細な docstring / 処理フロー・設計方針を記載し、実装意図を明確化。
- テスト容易性のため、OpenAI 呼び出し等の内部関数を unittest.mock.patch で差し替え可能に設計。

### 既知の注意点 / 制約
- OpenAI API キー（OPENAI_API_KEY）は score_news と score_regime で必須。未設定時は ValueError を送出。
- Settings の一部プロパティ（JQUANTS_REFRESH_TOKEN、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、KABU_API_PASSWORD）は必須で、未設定だと例外になる。
- calendar_update_job などは J-Quants クライアント（jquants_client）に依存するため、外部 API の可用性に影響される。
- news_nlp と regime_detector は LLM レスポンスに依存するため、LLM の出力形式変更やモデル変更時にパースロジックの調整が必要。

## 廃止
- なし

## セキュリティ
- 機密情報（API キー・トークン）は環境変数経由で供給する設計。誤ってリポジトリに含めないよう注意。
- .env 読み込み時に OS 環境変数を意図せず上書きしないよう protected 機構を導入。

---

変更点や設計意図の詳細は各モジュールの docstring を参照してください。今後のリリースではテストカバレッジ、CI 連携、運用向けモニタリング・アラート機能の追加を予定しています。