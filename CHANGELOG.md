# Changelog

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」フォーマットに準拠します。

現在のバージョン: 0.1.0

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-28
初回公開リリース

### Added
- パッケージ基盤
  - パッケージ名: kabusys。バージョンを src/kabusys/__init__.py で "0.1.0" と定義。
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を起点）により CWD に依存しない自動ロード。
  - .env / .env.local の読み込み優先度実装（OS 環境変数保護、override 挙動、上書き保護）。
  - 行パーサーは export 形式、クォート／エスケープ、インラインコメントに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - Settings クラス提供（プロパティベース）。J-Quants / kabuステーション / Slack / DB パス等の設定を取得・必須チェック。
  - 環境変数値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
  - duckdb/sqlite のデフォルトパス設定と Path 返却。

- AI（自然言語処理）機能 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols から指定ウィンドウのニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - ウィンドウ定義: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）。
    - トークン肥大対策: 1 銘柄あたりの最大記事数／文字数を制限。
    - バッチ処理（最大 20 銘柄/回）、JSON Mode を利用した厳密なレスポンス期待。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンスの堅牢なバリデーションとスコアの ±1.0 クリップ。
    - スコアを ai_scores テーブルへ冪等的に書き込む（DELETE → INSERT、部分失敗に配慮）。
    - テスト用フック: _call_openai_api をパッチ差替え可能に実装。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - calc_news_window と連携して記事ウィンドウを決定、OpenAI を呼んで macro_sentiment を算出（記事がない場合は LLM 呼び出しを行わず 0.0 を利用）。
    - API 呼び出しはリトライ（エラー分類に応じた扱い）、フェイルセーフとして API 失敗時は macro_sentiment=0.0。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）し、DB 書き込み失敗時は ROLLBACK を試行して例外を再送出。
    - 設計上いかなる箇所も datetime.today()/date.today() の直接参照を避け、ルックアヘッドバイアスを防止。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルを参照/更新するユーティリティ群を実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録データ優先、未登録日は曜日ベースでフォールバックする一貫した判定ロジック。
    - カレンダーデータの差分取得バッチ（calendar_update_job）を実装：J-Quants から差分取得 → 保存（バックフィル・健全性チェックあり）。
    - 最大探索範囲設定で無限ループ防止。
  - ETL パイプライン (pipeline)
    - ETLResult データクラスを提供（ETL 実行結果の構造化された集約: フェッチ/保存件数、品質問題、エラー等）。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）、jquants_client 経由の冪等保存方針を実装するための基盤を提供。
    - DuckDB 互換性、テーブル存在チェック、最大日付取得ユーティリティ等を提供。
  - etl モジュールで ETLResult を再エクスポート。

- 研究（research）モジュール (kabusys.research)
  - ファクター計算 (research.factor_research)
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離を計算する calc_momentum。
    - ボラティリティ/流動性: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算する calc_volatility。
    - バリュー: raw_financials を用いて PER（EPS が無効な場合は None）、ROE を算出する calc_value。
    - すべて DuckDB の prices_daily/raw_financials のみ参照、外部 API へのアクセスなし。データ不足時は None を返す動作。
  - 特徴量探索 (research.feature_exploration)
    - 将来リターン計算 calc_forward_returns（任意ホライズン、入力検証、1 クエリでの効率的取得）。
    - Information Coefficient（Spearman の ρ）を計算する calc_ic（ランク化、欠損除外、最小サンプルチェック）。
    - ランク関数 rank（同順位は平均ランクで扱う）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median を算出）。
  - zscore_normalize を data.stats から再エクスポート（research パッケージ初期化で公開）。

### Design / Reliability Highlights
- ルックアヘッドバイアス回避:
  - すべての時間ウィンドウ/日付決定で datetime.today()/date.today() の直接参照を避け、呼び出し側が target_date を指定する設計。
- トランザクション安全性:
  - 重要な DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の形式で冪等性を保ち、例外時に ROLLBACK を試行してログ出力。
- 外部 API の堅牢性:
  - OpenAI API 呼び出しは JSON Mode を利用して厳格にパース、429/ネットワーク/タイムアウト/5xx に対するリトライ実装と、パース失敗時のフェイルセーフ（スコア=0 やスキップ）を備える。
- テスト容易性:
  - OpenAI 呼び出しポイント（_call_openai_api）に対するパッチ差し替えを想定した設計。
- DuckDB 互換性配慮:
  - executemany に空リストを渡さない等、DuckDB の既知制約を回避する実装。

### Fixed
- （初回リリースのため該当なし）

### Changed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数または環境変数（OPENAI_API_KEY）から解決。キー未提供時は ValueError を発生させ適切に失敗することでキー漏洩リスクを低減。

---

注: 本 CHANGELOG はソースコードから機能・設計を推測して作成しています。実際のリリースノートに反映する際は、リリース担当者による確認・追記（既知の既報バグ、Breaking Changes、マイグレーション手順等）を推奨します。