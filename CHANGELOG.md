# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
各リリースは機能追加（Added）、変更（Changed）、修正（Fixed）、セキュリティ（Security）に分類しています。

## [Unreleased]
- 今後の変更予定をここに記載します。

## [0.1.0] - 2026-03-29
初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは src/kabusys/__init__.py の __version__ = "0.1.0"。
  - パッケージ公開 API に data, strategy, execution, monitoring を含める設定（__all__）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に検出（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env のパースは export 構文、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / システム設定等の取得メソッドを提供。
    - 必須変数は取得時に検証して未設定なら ValueError を送出。
    - KABUSYS_ENV, LOG_LEVEL の検証（許容値チェック）を実装。
    - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）や KABU_API_BASE_URL のデフォルト値を定義。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を利用して銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込むワークフローを実装。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST 相当）計算ユーティリティ calc_news_window を提供。
    - チャンク処理（最大20銘柄/チャンク）、1銘柄あたりの記事制限（最大記事数・文字数）によるトリム、JSON 応答の厳密検証、スコアの ±1.0 クリッピングを実装。
    - API エラー（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフリトライと、失敗時のフェイルセーフ（スキップ）を実装。
    - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みを行う処理を実装。
    - マクロ記事は raw_news からキーワードフィルタで抽出し、OpenAI により -1.0..1.0 の macro_sentiment を得る。API エラー時は macro_sentiment=0.0 にフォールバック。
    - レジームスコアは clip をかけ、閾値によりラベルを付与。
    - OpenAI 呼び出しは独自実装（news_nlp と private 関数を共有しない）でテスト用差し替えを想定。

- データプラットフォーム（kabusys.data）
  - ETL インターフェース（kabusys.data.etl）
    - pipeline.ETLResult を再エクスポート。
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得・保存・品質チェックのための ETLResult データクラスを実装。
    - DuckDB を想定したユーティリティ（テーブル存在確認、最大日付取得、トレーディングデイ調整など）を実装。
    - バックフィルや品質チェックの取り扱い方針（部分失敗の保護、エラー収集）を実装。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar を利用した営業日判定ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB データ優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job により J-Quants から差分取得して冪等保存（バックフィル、健全性チェック含む）を実装。
    - jquants_client との連携を想定（fetch/save 呼び出し）。

- 研究用モジュール（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER、ROE）および流動性指標を DuckDB 上の prices_daily/raw_financials を使って計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 扱い、レスポンスは (date, code) をキーとした dict のリストで返却。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（Spearman の ρ）計算（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - 外部依存を持たず（pandas など未使用）標準ライブラリと DuckDB で計算。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- （初版のため該当なし）

---

注記（既知の設計方針・制約）
- すべての AI 系処理は外部 API（OpenAI）に依存しており、API キー未設定時は ValueError を投げる箇所がある（score_news / score_regime）。テスト時は api_key 引数にモックキーや patch を注入する想定。
- AI 呼び出しの失敗はフェイルセーフ（多くのケースで 0.0 またはスキップ）でハンドリングされ、ETL や DB の一貫性を保つために部分書き換え・トランザクション（BEGIN/DELETE/INSERT/COMMIT）を使用。DB 書き込み失敗時は ROLLBACK を試行。
- time や日付の取り扱いに関してルックアヘッドバイアスを避ける設計（内部で datetime.today() や date.today() を直接参照しない）が採用されている。
- テスト容易性: OpenAI 呼び出しを行う内部関数は patch により差し替え可能に設計。

今後の予定（例）
- モデル改善や追加指標の実装（PBR・配当利回りなど）。
- jquants_client / kabu API クライアントの更なる統合テストとモック実装。
- モニタリング・アラート機能の拡充（Slack 通知などの統合）。

--- 

作成: ソースコードから推測して自動生成した CHANGELOG です。実際の変更履歴やリリース日付はプロジェクト運用ポリシーに合わせて調整してください。