# CHANGELOG

すべての変更は Keep a Changelog の形式に従い記載しています。  
このファイルはコードベースから推定した初回リリース向けの変更履歴です（__version__ = 0.1.0）。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-03
初回リリース。以下の主要機能・設計方針・実装を追加しました。

### Added
- パッケージ基盤
  - パッケージ初期化: kabusys パッケージを追加。公開サブモジュール: data, research, ai, execution, monitoring, strategy（__all__ で公開）。
  - バージョン情報を src/kabusys/__init__.py にて管理（__version__ = "0.1.0"）。

- 設定管理
  - 環境変数 / .env ロード機能（src/kabusys/config.py）
    - プロジェクトルートを .git または pyproject.toml で自動検出し、ルート配下の .env / .env.local を読み込む。
    - 読み込み優先順位: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - export KEY=val やクォート・エスケープ、インラインコメント等の .env 文法をサポートする独自パーサ実装。
  - Settings クラスで主要設定値をプロパティとして提供（J-Quants, kabu API, LINE, DB パス, 監視閾値, 環境・ログレベル等）。
    - 必須項目取得時は _require() で未設定なら ValueError を送出（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
    - KABUSYS_ENV と LOG_LEVEL の妥当性チェックあり（許容値チェック）。
    - デフォルト DB パス: DuckDB は data/kabusys.duckdb、SQLite は data/monitoring.db。

- データプラットフォーム / ETL
  - ETL パイプラインのインターフェース ETLResult を公開（src/kabusys/data/pipeline.py / etl.py）。
    - ETLResult に取得数・保存数・品質チェック結果・エラー一覧を保持し、has_errors / has_quality_errors / to_dict を提供。
  - market_calendar（カレンダー）管理（src/kabusys/data/calendar_management.py）
    - 営業日判定（is_trading_day）、翌/前営業日取得（next_trading_day / prev_trading_day）、期間内営業日取得（get_trading_days）、SQ判定（is_sq_day）等を実装。
    - DB にカレンダーがない場合は曜日ベースでフォールバック。DB が部分的にしかない場合にも一貫性を保つ設計。
    - calendar_update_job: J-Quants API から差分取得 → 冪等保存（ON CONFLICT）・バックフィル・健全性チェックを実装。
  - ETL 実行ユーティリティ・品質チェック連携の土台を実装（差分取得・バックフィル・品質問題の収集設計）。

- 研究（Research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: 1M/3M/6M リターンと 200 日移動平均乖離（ma200_dev）を計算（prices_daily を参照）。
    - Volatility & Liquidity: 20 日 ATR（atr_20）, 相対 ATR（atr_pct）, 20 日平均売買代金, 出来高比率を計算。
    - Value: raw_financials から最新財務を取得し PER / ROE を算出（EPS が 0 または欠損時は None）。
    - 全関数とも DuckDB 接続を受け取る関数として実装し、(date, code) 単位の dict リストを返す。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズン）を単一 SQL で高速取得する実装。
    - IC（Information Coefficient）計算（Spearman ランク相関）および rank / factor_summary 実装。
    - 外部依存を極力排し、標準ライブラリのみでの実装。

- AI / NLP 機能
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチで送信してセンチメント（ai_score）を算出。
    - タイムウィンドウは前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）。
    - バッチサイズ、記事数・文字数上限、JSON Mode（厳密 JSON 出力）を採用し、レスポンスのバリデーションとスコアの ±1.0 クリップを実施。
    - エラー（429、接続断、タイムアウト、5xx）は指数バックオフでリトライ、致命的でない場合はスキップして継続（フェイルセーフ）。
    - 部分失敗に備え、ai_scores テーブルへの書き込みは該当コードのみ DELETE → INSERT により部分置換。
    - テスト容易性のため _call_openai_api を分離してモック差替え可能。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で market_regime を判定。
    - マクロキーワードで raw_news タイトルを抽出し、OpenAI（gpt-4o-mini）により macro_sentiment を評価（記事なし時は LLM 呼び出しをスキップして 0.0）。
    - LLM 呼び出しはリトライ・バックオフ・エラー時のフォールバック（macro_sentiment = 0.0）。DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等に実行。
    - LLM 呼び出しはニュース NLP と別実装の private 関数にしてモジュール結合を避け、テストで差し替え可能。

- テスト性・安全性の向上
  - API キー注入を関数引数で受け付ける設計（api_key 引数、無ければ OPENAI_API_KEY 環境変数を参照）。
  - ルックアヘッドバイアス対策: datetime.today()/date.today() を直接参照しない実装（全て target_date を明示）。
  - DuckDB の executemany の制約（空リスト不可）に対する防御や、部分失敗時に既存スコアを消さない書き込み戦略を採用。
  - 詳細なログ出力（警告・情報）を多数追加し障害解析を容易に。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは環境変数または明示的引数でのみ受け付け、未設定時は明示的なエラーを返すように実装。
- .env の読み込みは OS 環境変数を保護する仕組み（protected set）を実装し、上書き挙動を制御可能。

### Performance
- Research / ETL / News の各種処理で SQL ベースの集約やウィンドウ関数を活用し、DuckDB 上で一括処理することで処理性能を意識した実装。
- ニュース処理はバッチ（最大 20 銘柄）での API 呼び出しを実施し、トークン肥大化対策として記事文字数トリムを実装。

### Documentation
- 各モジュールに機能説明 / 処理フロー / 設計方針の docstring を充実させました（config, ai, research, data 等）。
- .env パーサの振る舞いや時間ウィンドウ定義（ニュースウィンドウ）など、挙動を明記。

### Breaking Changes
- （初回リリースのため該当なし）

### Migration notes / 注意事項
- 実行に必須な環境変数:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - OPENAI_API_KEY（AI 機能利用時必須）
  - 他に任意: KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, DUCKDB_PATH, SQLITE_PATH 等
- 自動 .env ロードはデフォルトで有効。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, market_regime, raw_financials 等）が事前に整備されている必要があります。
- AI 機能は gpt-4o-mini を利用する前提のプロンプト / JSON Mode を実装しています。プロンプトの出力形式に依存するため、将来的なモデル変更時はバリデーション部分の調整が必要です。

----

この CHANGELOG はソースコードの実装内容から推定して作成しています。実際の変更履歴やリリースノートを作成する際は、コミットログやリリース手順に合わせて適宜調整してください。