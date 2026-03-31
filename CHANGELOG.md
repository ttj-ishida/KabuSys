# CHANGELOG

すべての重大な変更を本ファイルに記録します。This project adheres to "Keep a Changelog" と Semantic Versioning。

フォーマット:
- 各リリースは日付付きで記載
- セクションは Added / Changed / Fixed / Security / Removed / Deprecated を使用

---

## [0.1.0] - 2026-03-31
初回リリース。

### Added
- 全体
  - パッケージ kabusys を初版として公開。主要サブパッケージ: data, research, ai, config, monitoring, execution, strategy（__all__ に公開）。
  - DuckDB を主要なローカル分析ストアとして採用し、SQL ウィンドウ関数を活用した高速集計処理を実装。

- 環境・設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動ロードする仕組みを実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは `export KEY=val` 形式、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB パス 等の設定プロパティを提供。必須キーは未設定時に明確な例外を送出。
  - KABUSYS_ENV の許容値チェック（development / paper_trading / live）、LOG_LEVEL の妥当性検証を追加。
  - デフォルト値（KABUSYS_API_BASE_URL など）と Path 展開（~対応）をサポート。

- AI モジュール (kabusys.ai)
  - news_nlp モジュール
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信して銘柄別センチメントを算出。
    - バッチサイズ、記事数上限、文字数トリム等の肥大化対策を実装（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results フォーマット検証、未知コード除外、スコアの数値化・クリップ）。
    - ai_scores テーブルへの冪等書き込み（対象コードのみ DELETE → INSERT、DuckDB executemany の空リスト対策を含む）。
    - calc_news_window 関数で JST → UTC のウィンドウ計算を提供（ルックアヘッド防止）。
    - テスト容易性のため OpenAI 呼び出し箇所を patch 可能に実装（_call_openai_api を分離）。
  - regime_detector モジュール
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースのフィルタリング（キーワード群）、LLM 呼び出し、スコア合成ロジックを実装。
    - API エラーやパース失敗時はフェイルセーフとして macro_sentiment=0.0 を採用。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、例外時は ROLLBACK で保護）。
    - 内部で日付の取り扱いに注意し、datetime.today()/date.today() に依存しない設計（ルックアヘッドバイアス対策）。
    - OpenAI クライアント生成は API キー注入可能（api_key 引数または OPENAI_API_KEY 環境変数）。

- Data / ETL (kabusys.data)
  - pipeline モジュール
    - ETLResult dataclass を導入し、ETL の取得数・保存数・品質チェック結果・エラー情報を集約。
    - テーブル存在チェック、最大日付取得などのユーティリティ関数を実装。
    - 差分取得・バックフィルの設計方針（デフォルト backfill 値、最小データ日など）を組み込む準備。
  - etl（公開インターフェース）
    - ETLResult を再エクスポートして外部からの参照を容易化。
  - calendar_management モジュール
    - market_calendar を利用した営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録あり→DB優先、未登録→曜日ベースのフォールバックという一貫した挙動を提供。
    - カレンダー夜間更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得、バックフィル、健全性チェック（未来日差の閾値）を含む。
    - 市場カレンダー未取得時でも安全に動作するフォールバック実装。

- Research（kabusys.research）
  - factor_research モジュール
    - モメンタム（1/3/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR, ATR 比率）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）などのファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を活用し、営業日ベースのラグや移動平均を効率的に算出。
    - データ不足時の None 処理やログ出力を実装。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、入力検証）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas に依存しない純標準ライブラリ実装で軽量化。
  - research.__init__ で主要関数を再エクスポート（使いやすさを向上）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数未設定時は明示的に ValueError を送出する設計（例: OpenAI API キー、Slack トークン、J-Quants トークン 等）。これにより秘密情報の未設定に起因する不正挙動を防止。
- .env 自動ロード時、既存 OS 環境変数は保護（protected set）し、.env.local からの上書きは明示的に制御。

### Notes / 設計上の重要点
- ルックアヘッドバイアス防止: AI モジュール・研究モジュールの多くは内部で datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。
- テスト容易性: OpenAI 呼び出し箇所は内部関数で分離されており unittest.mock.patch による差し替えが可能。
- DB 書き込みはできる限り冪等（DELETE→INSERT や ON CONFLICT に相当する手法）かつトランザクションで保護。
- OpenAI 呼び出しは gpt-4o-mini・JSON mode を想定し、レスポンスの堅牢なパースとリトライ戦略を実装。
- DuckDB のバージョン依存差（executemany の空リスト）を回避するための防御的コーディング。

### Breaking Changes
- （初版のため該当なし）

---

今後のリリースでは以下を検討:
- ai/regime/news の評価アルゴリズムの定量的バリデーション（ベンチマーク）結果の記載
- J-Quants クライアント（jquants_client）の実装詳細・エラーハンドリング強化
- モジュール毎の CLI / ジョブ実行スクリプトの追加（運用向け）
- モニタリング・アラート（Slack 連携）の自動化

--- 

（注）本 CHANGELOG は提供されたソースコードから推測して作成しています。実際のリリースノート作成時はコミット履歴・issue・リリース担当者の確認に基づく追記・修正を推奨します。