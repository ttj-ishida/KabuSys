# Changelog

すべての変更はセマンティックバージョニングに従います。  
このファイルは Keep a Changelog の書式に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-31

### Added
- 初回リリース。パッケージ名: kabusys, バージョン: 0.1.0。
- パッケージ公開インターフェースを定義（src/kabusys/__init__.py）。
- 環境設定管理（src/kabusys/config.py）
  - Settings クラスを導入し、アプリ設定を環境変数から取得するプロパティ群を提供。
  - .env 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - .env パーサを堅牢化（export プレフィックス対応、シングル/ダブルクォートやバックスラッシュエスケープ、インラインコメント処理など）。
  - OS 環境変数保護（protected set）や .env.local による上書き挙動をサポート。
  - 必須キー未設定時は ValueError を送出する _require を提供。
  - J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / ログレベル / 環境種別の取得を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄ごとのニュースを OpenAI（gpt-4o-mini）の JSON モードでバッチ評価。
    - バッチサイズ制限（デフォルト 20 銘柄）、記事数・文字数トリム（最大記事数・文字数制限）を実装。
    - リトライ（429・ネットワーク・タイムアウト・5xx に対する指数バックオフ）、レスポンス検証（JSON 抽出・results 構造・コード整合・数値検証）を実装。
    - スコアは ±1.0 にクリップ。スコア保存は部分置換（DELETE → INSERT）で部分失敗時の既存データ保護。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）および calc_news_window を提供。
    - API キー未設定時は ValueError を報告。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースセンチメント（重み 30%）を合成し、日次でレジーム（bull/neutral/bear）を判定。
    - prices_daily から ma200 比率を計算、raw_news からマクロキーワードで記事抽出（最大 20 件）、OpenAI によるマクロセンチメント評価、合成スコアのクリップ、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 呼び出しのリトライ、API 失敗時は macro_sentiment=0.0 のフェイルセーフを採用。
    - 内部で OpenAI クライアントを使用（gpt-4o-mini）、テスト用に _call_openai_api をモック可能。
    - API キー未設定時は ValueError を送出。
  - 共通方針として、LLM 呼び出しはモジュール間でプライベート関数を共有せず独立実装。

- Research モジュール（src/kabusys/research）
  - factor_research.py: モメンタム / ボラティリティ / バリュー等の定量ファクター計算機能を提供
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS 不在時は None）。
    - DuckDB を用いた SQL ベース実装で、prices_daily / raw_financials のみ参照（本番発注 API にはアクセスしない）。
  - feature_exploration.py: 将来リターン・IC・統計サマリー等の解析ユーティリティを提供
    - calc_forward_returns: 各ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ランク相関（Spearman）の計算（3 件未満で None）。
    - rank: 同順位は平均ランクで処理（丸めによる ties の回避）。
    - factor_summary: count/mean/std/min/max/median の算出。
  - research パッケージは zscore_normalize（kabusys.data.stats からの再エクスポート）等を公開。

- Data モジュール（src/kabusys/data）
  - calendar_management.py: JPX カレンダー管理と営業日ロジック
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の提供。
    - market_calendar が未登録の場合は曜日ベース（土日除外）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックを実装。
  - pipeline.py / etl.py: ETL パイプライン関連
    - ETLResult データクラス（target_date, fetched/saved カウント, quality_issues, errors）を提供。to_dict によりログ用途で直列化可能。
    - 差分取得・バックフィル・品質チェックの設計方針とユーティリティを実装。
  - データアクセスは DuckDB 前提。テーブル存在チェック等のユーティリティを備える。

### Security & Safety
- API キーは引数経由または環境変数（OPENAI_API_KEY）で明示的に渡す必要あり。未指定時は ValueError を送出して明示的に失敗させる設計。
- 外部 API 呼び出し（OpenAI / J-Quants）失敗時は多くの箇所でフェイルセーフ（スコア 0.0 や処理スキップ）を採用し、システム全体の堅牢性を確保。
- .env の自動読み込みで OS 環境変数を保護する設計（既存環境変数の保護、.env.local による上書き制御）。

### Design notes / その他
- ルックアヘッドバイアス対策として、主要な関数は内部で datetime.today()/date.today() を直接参照しない。target_date を明示的に受け取り、その日付未満のデータのみを参照するようクエリが書かれている。
- OpenAI 呼び出し周りはテストの容易性を考慮して _call_openai_api を patch 可能に実装。
- DuckDB のバージョン差異に配慮した実装（executemany の空リスト回避等）。
- ロギングと警告を各所に充実させ、失敗時のトラブルシュートを支援。

### Breaking Changes
- 初回リリースのためなし。

### Known issues / Limitations
- PBR・配当利回りなど一部バリューファクターは現バージョンで未実装。
- DuckDB 固有のバインド制約に依存する箇所があるため、将来の DuckDB バージョンでの挙動確認が必要。

---

開発・運用上の詳細（使用モデル名、バッチサイズ、ウィンドウ定義、閾値など）は各モジュールのドキュメント文字列（docstring）に記載されています。必要であれば各モジュールごとのより詳細な変更履歴（関数単位の説明や追加予定のタスク）を追記します。