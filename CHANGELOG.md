# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-29
初期リリース。日本株のデータ取得・ETL、研究用ファクター計算、ニュース/マクロのAI評価、マーケットカレンダー管理などを含む基盤機能を実装しました。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを追加。__version__ = "0.1.0"、公開サブパッケージを __all__ で定義（data, strategy, execution, monitoring）。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルートを .git / pyproject.toml を基準に発見して .env と .env.local を読み込む。
    - 読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - OS 環境変数は protected（上書き不可）として保護。
  - .env のパースは export KEY=val / クォート（'  "） / エスケープ / インラインコメントに対応。
  - Settings クラスを提供（プロパティ経由での設定取得）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）と LOG_LEVEL の検証
    - is_live / is_paper / is_dev のヘルパープロパティ

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して、OpenAI（gpt-4o-mini）により銘柄単位のセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ保存する機能を実装。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して判定。
  - バッチ処理: 最大 20 銘柄／コール、1銘柄あたり最大記事数・文字数でトリム（トークン肥大対策）。
  - JSON Mode を利用しレスポンスを厳密に検証。部分失敗に備え idempotent な DELETE→INSERT の書き込みを行う。
  - リトライ戦略: 429・接続断・タイムアウト・5xx に対して指数バックオフでリトライ（最大回数は定数で制御）。
  - フェイルセーフ設計: エラー時は該当チャンクをスキップし、システム全体を停止させない。
  - テストしやすさ: _call_openai_api を patch してモック可能。

- マクロ／市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の market_regime を算出・保存。
  - ma200_ratio の算出は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを排除。
  - マクロニュースは news_nlp のウィンドウ算出を利用して抽出し、OpenAI でマクロセンチメントを数値（-1〜1）で取得。
  - レスポンスの不正／API障害時は macro_sentiment=0.0 として継続（フェイルセーフ）。
  - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実施。

- 研究用モジュール（kabusys.research）
  - factor_research: calc_momentum, calc_value, calc_volatility を実装。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - Value: PER（EPS が無効なら None）、ROE（raw_financials から最新を参照）。
    - Volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率。
    - DuckDB SQL を利用した高効率実装。外部 API へはアクセスしない。
  - feature_exploration: calc_forward_returns（任意ホライズン）、calc_ic（Spearman ランク相関による IC）、factor_summary（統計サマリ）、rank（同順位は平均ランク）を実装。
    - horizons の検証、戻り値の None 処理、ランクの丸めによる tie の安定化などを含む。
  - data.stats の zscore_normalize を再エクスポート（kabusys.research.__init__）。

- データ基盤（kabusys.data）
  - calendar_management:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - market_calendar テーブルがある場合は DB 値を優先、ない場合は曜日（平日）をフォールバック。
    - next/prev の探索は最大 _MAX_SEARCH_DAYS（デフォルト 60）で打ち切り。
    - calendar_update_job: J-Quants API を呼んで差分取得 → market_calendar に冪等保存。バックフィルと健全性チェックを実装。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを提供（取得数・保存数・品質問題・エラーの集約）。
    - 差分取得、バックフィル、品質チェックを行う方針を文書化（実装の骨組み）。
    - DuckDB 上で _get_max_date などのユーティリティを実装。
  - jquants_client 呼び出しに対応するインターフェースを参照（fetch / save 操作を想定）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 内部 / 設計上の注記 (Internals / Notes)
- ルックアヘッドバイアス回避:
  - 多くのモジュール（news_nlp, regime_detector, research系）は datetime.today()/date.today() を直接参照せず、target_date ベースでウィンドウ計算を行う設計となっている。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定し JSON Mode を利用。レスポンスのパースに堅牢性（余分なテキスト抽出など）を持たせている。
  - テストのために _call_openai_api を差し替え可能にしている。
- フェイルセーフ:
  - API エラーやパースエラー時に例外で全体を停止させず、ゼロまたはスキップで継続する方針。
- DuckDB 互換性:
  - executemany の空リスト問題等、DuckDB の既知制約に対する回避策を採用。
- ログと検証:
  - 設定値（KABUSYS_ENV, LOG_LEVEL）などは明示的に検証し、不正値時は ValueError を送出する。
  - 重要な分岐やフォールバック時にログ出力を行う（info/warning/debug）。

### テスト支援 / フック
- 環境読み込み抑止: KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動 .env 読み込みを抑制（ユニットテスト向け）。
- OpenAI 呼び出しの差し替えポイント（kabusys.ai.news_nlp._call_openai_api、kabusys.ai.regime_detector._call_openai_api）を用意し、モックで安定化テスト可能。

---

今後のリリースで想定される追加事項（例）
- strategy / execution / monitoring の具象実装（現状は公開名のみ）。
- より細かな品質チェックルールの実装と警告レベルの整備。
- 自動テストと CI 統合（OpenAI コールのモック化を含む）。
- ドキュメント（API リファレンス、運用手順、セットアップ手順）の充実。