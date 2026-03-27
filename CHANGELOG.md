# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

全般的な注意:
- 本リリースはパッケージの初期公開（初版）として想定した変更点をコードベースから推測して記載しています。
- 日付はリリース日として 2026-03-27 を使用しています（コード内の参照や例と整合）。

## [0.1.0] - 2026-03-27

### Added
- パッケージ初期構成
  - パッケージ名: kabusys、バージョン `0.1.0`（src/kabusys/__init__.py）。
  - パブリック API: data, strategy, execution, monitoring を __all__ で公開。

- 環境設定管理 (`kabusys.config`)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト等での利用を想定）。
  - .env 行パーサーの実装（コメント、export 形式、クォート/エスケープ対応、インラインコメント処理含む）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定等のプロパティ経由で取得可能:
    - 必須項目取得時に未設定なら ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）。
    - KABUSYS_ENV の検証（development/paper_trading/live のみ許容）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - duckdb/sqlite パスを Path 型で返却。

- AI 関連モジュール (`kabusys.ai`)
  - ニュースセンチメント（銘柄単位）スコアリング: score_news を実装（kabusys.ai.news_nlp）。
    - タイムウィンドウ: JST 基準で前日 15:00 ～ 当日 08:30 を対象（UTC naive datetime に変換して DB 比較）。
    - raw_news と news_symbols を集約し、1 銘柄あたり最大記事数・最大文字数でトリムして LLM に送信。
    - gpt-4o-mini（JSON Mode）を利用したバッチ評価（1 回のコールで最大 20 銘柄）。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフ再試行処理実装（リトライ制御）。
    - レスポンスの厳密バリデーション（JSON 解析、results リスト、code と score の型チェック、未知コードの無視、数値チェック）。
    - スコアは ±1.0 にクリップ。取得成功分のみ ai_scores テーブルへ冪等書き込み（DELETE → INSERT）。
    - API キー注入可能（api_key 引数または OPENAI_API_KEY 環境変数を使用）。テスト用に _call_openai_api を差し替え可能。
    - API失敗時はフェイルセーフでスキップ継続（例外を拾いログ出力し、部分成功は保持）。

  - 市場レジーム判定: score_regime を実装（kabusys.ai.regime_detector）。
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - prices_daily から 1321 の終値データ取得、ルックアヘッドバイアス防止（date < target_date を使用）。
    - ニュース抽出はマクロキーワード群でフィルタし、LLM（gpt-4o-mini）に渡して macro_sentiment を算出。
    - LLM 呼び出しは再試行ロジックを持ち、最終的に失敗した場合 macro_sentiment=0.0 として継続。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書込失敗時は ROLLBACK を試行して例外を上位へ伝播。

- 研究用（Research）モジュール (`kabusys.research`)
  - factor_research:
    - モメンタムファクター calc_momentum（1M/3M/6M リターン、200日 MA 乖離）。
    - ボラティリティ/流動性 calc_volatility（20日 ATR、ATR 比率、20日平均売買代金、出来高比）。
    - バリューファクター calc_value（PER、ROE。raw_financials から最新財務データを取得）。
    - DuckDB の SQL を活用した高効率な集計実装。十分な履歴がない場合は None を返す挙動。
  - feature_exploration:
    - 将来リターン calc_forward_returns（任意ホライズン。デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算 calc_ic（Spearman のランク相関）。
    - rank ユーティリティ（同順位は平均ランク処理、丸め対策あり）。
    - factor_summary（count/mean/std/min/max/median を計算）。
  - zscore_normalize を data.stats から再エクスポート。

- データプラットフォーム関連 (`kabusys.data`)
  - カレンダー管理 calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティ:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - DB データ優先、未登録日は曜日ベースでフォールバックする一貫したロジックを提供。
    - calendar_update_job により J-Quants から差分取得して冪等保存。バックフィル・健全性チェック実装。
  - ETL パイプライン pipeline:
    - ETLResult データクラス（target_date, fetched/saved counts, quality_issues, errors 等）を実装して公開。
    - 差分取得、保存（idempotent）、品質チェックの設計方針を反映。
    - _get_max_date などの内部ユーティリティを実装して、テーブル存在チェックや最大日付取得に対応。
  - etl モジュールから ETLResult を再エクスポート。

- 一般的な設計方針（各モジュール共通）
  - ルックアヘッドバイアス回避: datetime.today() / date.today() を内部ロジックで直接使用せず、target_date を明示的に受け取る設計。
  - DuckDB を主要なデータベースとして想定し、SQL と Python を組み合わせた実装。
  - API 呼び出しは失敗してもシステム全体が停止しないようフェイルセーフ（ログ出力・部分成功保持）。
  - テスト容易性を考慮し、API 呼び出し箇所（_call_openai_api 等）を差し替え可能に実装。

### Changed
- 初期公開につき該当なし。

### Fixed
- 初期公開につき該当なし。

### Deprecated
- 初期公開につき該当なし。

### Removed
- 初期公開につき該当なし。

### Security
- 初期公開につき該当なし。

---

注記:
- 本 CHANGELOG はソースコードの実装から推測して作成した初版の変更履歴です。今後のリリースでは実際の変更差分に合わせて「Added/Changed/Fixed/Deprecated/Removed」等を追加してください。