# Changelog

すべての重要な変更点をこのファイルに記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]

- 予定 / 改善案
  - ユニットテストの拡充（特に OpenAI 呼び出しのモック周り、DuckDB の挙動確認）
  - ドキュメント整備（使用例、DB スキーマの明記、運用ガイド）
  - モデルやプロンプトのチューニング（gpt-4o-mini のプロンプト改善、バッチサイズ調整）
  - 監視・ロギングの強化（Slack 通知やメトリクス出力の追加）
  - jquants_client のエラー回復や再試行戦略の強化

---

## [0.1.0] - 2026-04-02

初期リリース。以下の主要機能と実装方針を含みます。

### Added
- パッケージ基本構成
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。主要サブパッケージとして data, research, ai, ... をエクスポート。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - 読み込み順序: OS 環境 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを抑止可能。
  - .env 行パーサ実装：export 構文、クォート内のバックスラッシュエスケープ、インラインコメント処理等に対応。
  - OS 環境変数の保護: 既存の OS 環境変数は上書きされない（override / protected 機構）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB / 監視閾値 / システム設定等のプロパティを読み込む（必須値未設定時は ValueError を発生）。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値の列挙）。

- データ基盤（src/kabusys/data/*）
  - ETL パイプライン用インターフェースを公開（ETLResult dataclass を再エクスポート）。
  - pipeline モジュール:
    - 差分取得・保存・品質チェックを行う ETLResult 型を実装。
    - backfill / lookahead / 品質チェックの設計方針をコード化。
  - calendar_management モジュール:
    - market_calendar テーブルを元にした営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - カレンダー未登録日は曜日ベースでフォールバック（週末は非営業日）。
    - calendar_update_job による J-Quants からの差分取得と冪等保存（バックフィル・健全性チェック付き）。
    - 最大探索範囲制限（_MAX_SEARCH_DAYS）で無限ループを防止。

- 研究用機能（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離などの算出（prices_daily を参照）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - calc_value: raw_financials から EPS/ROE を取得し PER / ROE を計算。
    - DuckDB のウィンドウ関数を活用した実装。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを一度のクエリで取得。
    - calc_ic: ファクターと将来リターンのランク相関（Spearman ρ）を計算（十分なサンプルがない場合は None）。
    - rank: 同順位は平均ランクを返すランク化ユーティリティ。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - 設計方針: DuckDB と標準ライブラリのみで完結、外部 API や発注処理には接続しない。

- AI / NLP 機能（src/kabusys/ai/*）
  - news_nlp モジュール（score_news）:
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini, JSON Mode）でバッチ評価。
    - バッチサイズ (_BATCH_SIZE = 20)、記事数/文字数のトリム制御、最大再試行/指数バックオフを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リストチェック、コード照合、数値変換、スコアの ±1.0 クリップ）。
    - DuckDB の executemany に対する互換性対策（空リストを渡さないチェック）。
    - API キーは引数または環境変数 OPENAI_API_KEY で提供。未指定時は ValueError を送出。
    - フェイルセーフ: API 呼び出し失敗やバリデーション失敗時は該当チャンク/銘柄をスキップして継続。

  - regime_detector モジュール（score_regime）:
    - ETF 1321 の 200 日移動平均乖離とマクロニュースの LLM センチメントを重み合成（MA 重み 70%、マクロ重み 30%）して市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事は raw_news からキーワードで抽出（_MACRO_KEYWORDS）。
    - LLM 呼び出しは独立実装。API のリトライ/バックオフ、5xx の再試行対応、最終的に失敗した場合は macro_sentiment=0.0 として継続。
    - レジームスコアのクリッピングとしきい値判定（_BULL_THRESHOLD/_BEAR_THRESHOLD）。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。

- 実装上の注意点・設計判断（ドキュメント文字列として明記）
  - ルックアヘッドバイアス回避: datetime.today(), date.today() の直接参照を避け、関数引数の target_date に基づく設計。
  - DB 書き込みはできるだけ冪等（DELETE→INSERT、ON CONFLICT 等）で行う。
  - API 失敗時はフェイルセーフ（例外を上位に投げず局所的に扱う）を優先し、処理継続性を重視。

### Fixed / Improved
- news_nlp / regime_detector における API レスポンス処理の堅牢化
  - JSON モードでも前後に余計なテキストが混入するケースを想定し，最外の {} を抽出して復元する処理を追加。
  - RateLimit/ネットワーク断/タイムアウト/5xx に対する再試行と指数バックオフを実装し、再試行上限到達時はログ出力して安全にスキップ。
- DuckDB 実行互換性
  - executemany に空リストを渡すと失敗する DuckDB バージョンに対処するため、事前に params が空でないことをチェックしてから実行。

### Security
- 環境変数の扱い
  - 重要なトークン（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）は Settings を通して必須チェックを行い、未設定時は明確なエラーメッセージを返す。
  - .env 読み込み時に既存の OS 環境変数は上書きされないよう保護。

---

注: 上記はソースコードから推測できる機能・設計の要約です。内部で利用する外部クライアント（OpenAI, J-Quants クライアント等）の具体的なバージョン依存や運用手順、DB スキーマの詳細は別途ドキュメントまたはコードコメントを参照してください。