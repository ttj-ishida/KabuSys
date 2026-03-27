# Keep a Changelog — 変更履歴

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
初期リリース v0.1.0（初回公開）について、コードベースから推測できる主要な追加・実装内容と設計方針を日本語でまとめます。

## [Unreleased]

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点および実装方針は以下の通りです。

### Added
- パッケージのエントリポイント
  - src/kabusys/__init__.py による基本エクスポート（data, strategy, execution, monitoring）。
  - パッケージバージョン __version__ = "0.1.0" を定義。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルート検出：.git または pyproject.toml を基準）。
  - .env/.env.local の優先順位処理と既存 OS 環境変数の保護（protected set）。
  - .env の堅牢なパーサー実装：コメント、export プレフィックス、クォート内のエスケープ、インラインコメント等に対応。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定（env, log_level, is_live 等）のプロパティを公開。未設定値は明示的にエラーを出す設計（_require を使用）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に、銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを評価する機能を実装。
    - バッチ処理（最大20銘柄／リクエスト）、1銘柄当たりの記事数と文字数の上限（トリム）、JSON mode を使った厳密な応答期待。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライロジックを実装。
    - レスポンスのバリデーション（JSON パース回復ロジック、results 配列検査、コード照合、スコア数値検証、±1.0 クリップ）。
    - DuckDB への冪等書き込み（DELETE→INSERT）と部分失敗時の既存データ保護。
    - テスト容易性のため OpenAI 呼び出しは _call_openai_api を経由し patch 可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を参照し、ma200_ratio 計算、マクロキーワードで記事抽出、OpenAI 評価、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API エラー時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - OpenAI 呼び出しのリトライと 5xx 判定での再試行を実装。テスト用に呼び出しを置換可能。
    - ルックアヘッドバイアス対策として datetime.today()/date.today() を参照しない、DB クエリは target_date 未満の排他条件を使用。

- Data モジュール（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar に基づく営業日の判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバック。最大探索日数で無限ループを回避。
    - 夜間バッチ job（calendar_update_job）で J-Quants から差分取得して保存、バックフィルと健全性チェックの実装。
  - ETL パイプライン（pipeline, etl）
    - ETLResult データクラスを公開（etl モジュールで再エクスポート）。
    - 差分更新・保存（idempotent save）、品質チェックフレームワーク統合（quality モジュール参照）の骨組み。
    - 最終取得日の検出、バックフィル日数、J-Quants API 呼び出しと保存処理のエラーハンドリング／ログ出力。
    - DuckDB の存在チェックや MAX 日付取得ユーティリティを提供。

- Research モジュール（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、出来高指標）、Value（PER、ROE）などの計算関数を実装。
    - DuckDB SQL を駆使して各ファクターを高速に算出。データ不足時の None ハンドリング。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）：複数ホライズンの一括取得、入力検証。
    - IC（calc_ic）：Spearman ランク相関（ランクは同順位平均）を実装。レコード不足や分散ゼロを考慮。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を標準ライブラリのみで算出。
    - ユーティリティとして zscore_normalize（data.stats から再エクスポート）や rank 関数を提供。

### Changed / Design decisions（実装時に明示された方針）
- すべてのモジュールでルックアヘッドバイアスを避ける設計（datetime.today()/date.today() を直接参照しない）。
- OpenAI 呼び出しは JSON Mode を利用し厳密な JSON 応答を期待。API 失敗時は例外を投げずにフェイルセーフでスコア 0.0 またはスキップして ETL の継続を優先。
- DuckDB とのやり取りは冪等性を重視（DELETE→INSERT、ON CONFLICT 相当の扱い）、executemany の空リスト扱い（DuckDB 0.10 の制約）に注意した保護実装あり。
- テスト容易性のため、API 呼び出し部（_call_openai_api 等）は patch / mock しやすいように分離。
- ロギングを適切に追加し、失敗時は警告・例外ログを残して上位に伝播またはフェイルセーフ化。

### Fixed
- （初版のため既知のバグ修正履歴は未該当。実装内にログ出力・例外処理で不整合検出時の回復措置あり。）

### Security
- 環境変数保護のため OS 環境変数を protected set として上書き回避する仕組みを導入。
- OpenAI キーは引数で注入可能（テスト時のキー露出軽減）かつ環境変数から取得。未設定時は ValueError を送出して明示的に扱う。

---

注記:
- この CHANGELOG はリポジトリ内のソースコードから実装内容と設計方針を推測して作成したもので、実際の変更履歴（コミット単位や作業履歴）をそのまま反映するものではありません。実際のリリースノート作成時はコミットログや PR を参照して補完してください。