# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従ってバージョニングしています。  

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 破壊的変更 (Removed / Breaking Changes)
- セキュリティ (Security)

[Unreleased]

## [0.1.0] - 2026-04-04
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py に基本的なパッケージ情報（__version__ = 0.1.0）と公開サブパッケージ（data, strategy, execution, monitoring）を追加。

- 環境設定・.env ローダー（src/kabusys/config.py）
  - プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動検出して読み込む自動環境変数ローダーを実装。
  - .env 行パーサー実装（コメント、export プレフィックス、シングル／ダブルクォート、エスケープ対応、インラインコメント処理）。
  - override/protected オプションにより OS 環境変数を保護しつつ .env.local を上書きできる挙動を実装。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを実装し、J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム設定（env, log_level 等）を環境変数から取得するプロパティを提供。
  - 環境変数の必須チェック（_require）を実装し、未設定時は ValueError を発生させる。

- AI 関連モジュール（src/kabusys/ai）
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（ai_score）を算出する機能を実装。
    - 時間ウィンドウ計算（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）を含む calc_news_window 実装。
    - バッチ処理（最大 20 銘柄/チャンク）、記事・文字数トリミング（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を実装。
    - 再試行ロジック（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）、レスポンス検証、数値への変換と ±1.0 のクリッピングを実装。
    - DuckDB への冪等書き込み（既存レコードの DELETE → INSERT）を実装し、部分失敗時に他銘柄データを保護する設計。
    - テスト容易性のため、OpenAI 呼び出し関数を差し替え可能に実装（_call_openai_api の patch を想定）。

  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - MA200 計算（_calc_ma200_ratio）：target_date 未満のデータのみを使用しルックアヘッドを防止、データ不足時は中立（1.0）としてフェイルセーフ。
    - マクロキーワードで raw_news をフィルタしてタイトルを抽出（_fetch_macro_news）。
    - OpenAI 呼び出しと再試行（_score_macro）を実装。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。

- データプラットフォーム関連（src/kabusys/data）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理（market_calendar）と営業時間判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装し、DB 登録がない場合は曜日ベースでフォールバック。
    - calendar_update_job を実装し、J-Quants クライアント経由で差分取得→保存（バックフィル・健全性チェックを含む）を行う。
    - DuckDB からの date 変換ユーティリティやテーブル存在チェックを備える。

  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass を実装（取得件数・保存件数・品質チェック結果・エラー一覧などを保持）。
    - 差分取得／backfill／保存／品質チェックの方針を設計文書に基づき実装予定（ETLResult を公開インターフェースとして etl モジュールから再エクスポート）。

  - jquants_client / quality 等の外部データ取得・品質評価モジュールとの連携を想定した設計。

- 研究（Research）モジュール（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、ma200_dev）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）などファクター計算を実装。
    - DuckDB SQL ベースの実装で、データ不足時の None ハンドリング、結果は (date, code) をキーとする dict のリストで返す。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算 calc_ic（Spearman ランク相関）、rank ユーティリティ、factor_summary（基本統計量）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装する設計。

- その他
  - 各モジュールで共通する設計方針を明記（ルックアヘッドバイアス回避のため datetime.today()/date.today() を参照しない設計、API 失敗時の安全なフォールバック、DuckDB での executemany の空リスト対応等）。
  - OpenAI SDK 用のエラー型（RateLimitError, APIConnectionError, APITimeoutError, APIError）を利用した堅牢なエラーハンドリングとリトライ戦略を実装。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed / Breaking Changes
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

既知の注意点（設計上の意図）
- AI モジュールは OpenAI API キー（引数または環境変数 OPENAI_API_KEY）を必要とします。未設定時は ValueError を発生させます。
- .env 自動読み込みはプロジェクトルート検出に基づくため、配布形態や実行パスによっては KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化してください。
- DuckDB の executemany に空リストを渡すと問題になるバージョンを想定しており、その回避ロジックを各所に実装しています。
- ルックアヘッドバイアス対策として、日付・ウィンドウ計算は外部から与えられる target_date に完全に依存します（内部で現在時刻を参照しない）。

今後の予定（例）
- ETL pipeline の差分処理の具体実装（取得ロジック、品質チェックの統合）。
- strategy / execution / monitoring サブパッケージの実装と統合テスト。
- テストカバレッジ向上のためユニットテスト・統合テストの追加。

もし CHANGELOG に追記してほしい点（例: リリース日、より詳細な項目分け、影響範囲など）があれば教えてください。