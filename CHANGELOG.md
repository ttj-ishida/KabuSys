# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
現在のリリースは初期公開バージョンです。

なお日付はこのリリース作成日です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-01

### Added
- パッケージの初期公開
  - パッケージ名: kabusys、バージョン: 0.1.0

- 共通設定・環境変数管理（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）。
  - 読み込み順序: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサを実装（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱い等に対応）。
  - 必須キー未設定時は ValueError を投げる _require() を提供。
  - Settings クラスを提供（settings インスタンスをエクスポート）。主な設定項目:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - PID_FILE_PATH（デフォルト: data/execution.pid）
    - CPU/MEMORY/DISK の監視閾値（デフォルト: CPU 90.0, MEMORY 85.0, DISK 90.0）
    - KABUSYS_ENV（有効値: development, paper_trading, live、取得時にバリデーション）
    - LOG_LEVEL（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL、取得時にバリデーション）
    - is_live / is_paper / is_dev ヘルパー

- AI モジュール（kabusys.ai）
  - ニュース NLU スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols をソースに、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）の JSON Mode に送信し、各銘柄のセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む機能（score_news 関数）。
    - タイムウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（UTC 変換済み）を対象。calc_news_window を公開。
    - バッチ処理: 最大 20 銘柄/回（_BATCH_SIZE=20）、各銘柄は最新10記事・最大3000文字でトリム。
    - 再試行: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ（最大リトライ回数・初回待機は定数で制御）。
    - レスポンス検証: JSON パース、"results" の存在、各要素の code と score を検証。スコアは ±1.0 にクリップ。
    - DB 書き込みは冪等化（該当 date/code を DELETE → INSERT）して部分失敗で他コードの既存スコアを保護。
    - テスト容易性: OpenAI 呼び出し部分は内部関数をパッチ可能にして差し替え可能。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を算出し market_regime テーブルへ書き込む機能（score_regime 関数）。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドを防止。データ不足時は中立（ma200_ratio=1.0）にフォールバックして WARNING を出力。
    - マクロキーワードで raw_news のタイトルを抽出し、最大 20 件を LLM に送る。LLM モデルは gpt-4o-mini。
    - OpenAI API 呼び出しは再試行とフォールバック（失敗時 macro_sentiment=0.0）を行い、最終的に score をクリップしてラベリング。
    - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に行う。失敗時は ROLLBACK を試みる。

- データプラットフォーム関連（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar テーブル）を扱うユーティリティ群を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 未取得時は曜日ベースのフォールバック（土日非営業日）。DB 登録値がある場合は DB 値を優先。最大探索範囲（_MAX_SEARCH_DAYS=60）で無限ループ回避。
    - 夜間バッチ: calendar_update_job を提供。J-Quants から差分取得し冪等に保存。バックフィル（直近 _BACKFILL_DAYS=7 日）や健全性チェックを実装。

  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラスを公開（ETL 実行結果の構造化保存、has_errors / has_quality_errors, to_dict を提供）。
    - 差分取得、保存（jquants_client 経由で冪等保存）、品質チェック（quality モジュール）を想定した設計。デフォルトバックフィル日数やカレンダー先読み等の設計方針を実装予定のインターフェースに反映。

- 研究（research）モジュール（kabusys.research）
  - factor_research モジュールを提供（calc_momentum, calc_volatility, calc_value）。
    - Momentum: mom_1m / mom_3m / mom_6m、および 200 日 MA 乖離（ma200_dev）。データ不足時は None。
    - Volatility / Liquidity: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）。データ不足時は None。
    - Value: raw_financials から最新の財務データを取得し PER（EPS が無効な場合は None）と ROE を計算。
    - すべて DuckDB の prices_daily / raw_financials を参照し外部 API 呼び出しは行わない。結果は (date, code) を含む dict リストで返す。
  - feature_exploration モジュールを提供（calc_forward_returns, calc_ic, factor_summary, rank）。
    - 将来リターン calc_forward_returns: デフォルト horizons = [1,5,21]、horizons の妥当性チェック（正の整数かつ <= 252）。
    - IC（Spearman の ρ）を calc_ic で実装（ランク計算に rank を使用、同順位は平均ランク）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。None 値除外。
    - 実装は pandas 等に依存せず標準ライブラリと DuckDB のみで行う。

- パッケージ API のエクスポート整理
  - 各サブパッケージは必要な関数／ユーティリティを __all__ 経由で公開（例: kabusys.ai.score_news / score_regime、kabusys.research の関数群、kabusys.data.ETLResult など）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を用いる。内部実装でキーをログに出力しない想定。

注意事項（実運用上の設計判断）
- ルックアヘッドバイアス防止のため、すべての日時ロジックは target_date 等の明示的引数を使用し、datetime.today()/date.today() の無制限参照を避ける設計になっています（一部ジョブや設定取得では date.today() を用いる箇所あり）。
- OpenAI 呼び出しは外部サービス依存のため、API エラー・レート制限・ネットワーク障害に対してフォールバック（スコア 0.0 やスキップ）を行い、致命的例外を発生させないフェイルセーフ設計を優先しています。
- DuckDB の executemany の制約（空リスト不可など）や互換性を考慮した実装上の注意が複数箇所にあります。

---

（この CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のコミット履歴や変更差分がある場合は適宜追記・修正してください。）