# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買・データ基盤・リサーチ支援のための基盤機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0）。公開サブパッケージ名を __all__ で定義: data, strategy, execution, monitoring（strategy/execution/monitoring の具象実装は別途）。
- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび OS 環境変数から設定を自動読み込みする機能を実装。
  - 自動ロードの探索はパッケージのファイル位置を基準にプロジェクトルート（.git / pyproject.toml）を特定して行うため、CWD に依存しない。
  - .env/.env.local の読み込み順序を実装（OS 環境変数 > .env.local > .env）。上書き制御、保護されたキーセットのサポート。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等に対応。
  - 設定ラッパー Settings を提供。主要設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL 検証
    - ヘルパー: is_live / is_paper / is_dev
  - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD

- データ関連 (src/kabusys/data/)
  - ETL パイプライン基盤（pipeline.py / etl.py）
    - ETLResult dataclass を実装し、取得件数・保存件数・品質チェック結果・エラーの収集を標準化。
    - 差分取得・バックフィル動作の方針と DuckDB 互換性（テーブル未作成や空データ時の扱い）を実装。
  - カレンダー管理（calendar_management.py）
    - JPX カレンダー（market_calendar）を用いた営業日判定ユーティリティ群を追加:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に更新する夜間ジョブを実装。バックフィル・健全性チェックあり。
    - カレンダー未取得時の曜日ベースのフォールバックを実装（DB の登録値を優先）。

- AI（自然言語処理）モジュール (src/kabusys/ai/)
  - ニュースセンチメント（news_nlp.py）
    - raw_news / news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI Chat（gpt-4o-mini）を JSON mode で呼び出して銘柄単位のセンチメントスコアを算出。
    - バッチ処理（1コールあたり最大20銘柄）、1銘柄あたり記事数上限・文字数トリム、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスの厳密なバリデーションを実装。
    - DuckDB 0.10 の executemany の制約（空リスト不可）を考慮した安全な書き込み処理（DELETE → INSERT の個別 executemany）。
    - API キー注入可能（api_key 引数 or OPENAI_API_KEY 環境変数）。テスト容易性のため _call_openai_api をパッチ可能に設計。
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算（target_date の前日 15:00 JST ～ 当日 08:30 JST を UTC naive datetime に変換）。
  - 市場レジーム判定（regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）、マクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を算出（失敗時は 0.0 にフォールバック）。
    - 合成スコアのクリップ判定と market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API 呼び出しのリトライ、エラー分類（429/ネットワーク/タイムアウト/5xx 等）を実装。テスト用に _call_openai_api を差し替え可能。
  - ai パッケージ初期化で score_news を公開。

- リサーチ（研究）モジュール (src/kabusys/research/)
  - ファクター計算 (factor_research.py)
    - Momentum（1M/3M/6M リターン、ma200_dev）、Volatility（20日 ATR 等）、Value（PER, ROE）等の計算関数を実装。DuckDB SQL と Python の組合せで再現性高く実行。
    - データ不足時の None 扱いなど堅牢な設計。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算（複数ホライズン対応）、IC（Spearman ランク相関）計算、rank ユーティリティ、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等外部ライブラリに依存せず標準ライブラリで実装。
  - research パッケージ初期化で主要関数群と zscore_normalize（kabusys.data.stats から）を公開。

- その他
  - データ再利用性とテスト容易性を考慮して、OpenAI 呼び出し部分はパッチ可能な専用内部関数として実装（ユニットテストで差し替え可能）。

### 修正 (Changed)
- 複数モジュールで以下の設計方針を採用し統一:
  - ルックアヘッドバイアスを避けるため内部で datetime.today()/date.today() を直接参照しない（関数呼び出し時に target_date を明示的に渡す設計）。
  - API 失敗時はフェイルセーフで継続（多くのケースで 0 やスキップで処理継続）、致命的な例外は上位に伝播。
  - DuckDB の挙動差（空の executemany 等）を考慮した互換性処理。

### 注意点 / 既知の制約 (Known issues / Notes)
- OpenAI API 依存
  - news_nlp.score_news / regime_detector.score_regime は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を送出する。
  - LLM の応答フォーマットに依存するため、モデル応答の不整合時には該当チャンクをスキップし安全側にフォールバックする実装になっています（例: JSON 解析失敗 → スコア 0 / スキップ）。
- DuckDB への書き込み挙動
  - DuckDB のバージョン差異による executemany の空リスト不可等を回避するためにチェックを入れている点に留意してください。
- タイムゾーン
  - news_nlp のウィンドウ生成は JST を基準にし、DB 内の raw_news.datetime は UTC（naive datetime）で保存されている想定です。運用時は raw_news のタイムゾーン整合性に注意してください。

### セキュリティ (Security)
- 環境変数に API キー等の機密情報を保持する設計です。レポジトリやログにキーが出力されないように注意してください。
- .env 自動ロードは便利ですが、テスト等で不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

---

今後の予定（例）
- strategy / execution / monitoring の具体実装追加（注文実行ロジック、戦略定義、モニタリング/アラート機能）。
- テストカバレッジ拡充と CI の統合。
- jquants_client の具象実装・エラー処理強化、品質チェックモジュールの詳細実装。

このリリースに関する疑問点や追加で記載してほしい変更点があればお知らせください。