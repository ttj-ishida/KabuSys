# CHANGELOG

すべての注記は Keep a Changelog の方針に準拠しています。  
主な設計判断・挙動はソースコードから推測して記載しています。

---

## [0.1.0] - 2026-03-28

初回公開リリース。

### 追加 (Added)
- パッケージ骨格
  - kabusys パッケージを公開（__version__ = 0.1.0）。モジュール群: data, research, ai, config, etc.

- 環境設定・自動 .env ロード (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを実装（コメント/export/シングル・ダブルクォート、バックスラッシュエスケープ対応）。
  - OS 環境変数の保護機構（.env の上書き時に既存 OS 環境変数は protected として扱う）。
  - 必須環境変数を取得するヘルパー _require() と、Settings クラスを提供。
  - Settings で参照する環境変数（必須/既定値）:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live、デフォルト: development）
    - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）

- AI モジュール (kabusys.ai)
  - ニュースセンチメント解析: score_news（news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとに記事を結合し、OpenAI (gpt-4o-mini) に JSON モードで投げて ai_scores テーブルに書き込み。
    - バッチ処理: 最大 20 銘柄/コール、1銘柄あたり最大 10 記事、最大 3000 文字にトリム。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ実装。
    - レスポンスの厳密バリデーション (results キー、code の検証、数値チェック)、スコアを ±1.0 にクリップ。
    - 取得済みコードのみを DELETE → INSERT で置換することで部分失敗時の既存データ保護（冪等性配慮）。
    - ルックアヘッドバイアス防止のため datetime.today() を参照しない設計、明示的な target_date 引数。
    - OpenAI API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。

  - 市場レジーム判定: score_regime（regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で regime_label(bull/neutral/bear) を算出し market_regime に格納。
    - マクロニュース抽出はニュース NLP のウィンドウ計算 calc_news_window を利用。
    - LLM 呼び出しは独立実装で、APIエラー時は macro_sentiment=0.0 のフェイルセーフを採用。
    - JSON レスポンスパース失敗や API エラーに対する詳細なログ・リトライ処理。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK 保護。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (calendar_management.py)
    - market_calendar を元に営業日判定・次/前営業日検索・期間内営業日取得・SQ 日判定を提供。
    - DB にデータがない場合は曜日ベースのフォールバック（土日非営業）。
    - next_trading_day / prev_trading_day は最大探索日数を制限して ValueError を返す安全設計。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル、健全性チェック付き）。
  - ETL パイプライン (pipeline.py / etl.py)
    - ETLResult dataclass を公開（取得数・保存数・品質チェック結果・エラー一覧を格納）。
    - 差分更新・バックフィル・品質チェックの設計方針を実装（jquants_client と quality モジュール利用を想定）。
    - DB テーブル存在チェックや最大日付取得ユーティリティを提供。

- リサーチ用モジュール (kabusys.research)
  - ファクター計算 (factor_research.py)
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離 (ma200_dev) を計算。
    - Volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率。
    - Value: EPS に基づく PER、および ROE（raw_financials から最新レコードを取得）。
    - DuckDB を用いた SQL 中心の実装、データ不足時は None を返す挙動。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算（calc_forward_returns: 任意ホライズンで LEAD を使って算出）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）。
    - ランキングユーティリティ（rank）、ファクター統計サマリー（factor_summary）。
    - pandas 等の外部依存を避け、標準ライブラリ + duckdb で実装。

- 汎用設計上の配慮
  - DuckDB を中心ストレージ（ローカル分析向け）として全面的に利用。
  - DB 書き込みは冪等性を重視（DELETE → INSERT、ON CONFLICT 等を利用）。
  - LLM 周りは JSON モード・レスポンスバリデーション・スコアクリッピング・フェイルセーフ（ゼロフォールバック）を採用。
  - すべての "日付基準" (target_date) は明示的に引数化し、datetime.today()/date.today() によるルックアヘッドを避ける設計方針。

### 変更 (Changed)
- （初版ため該当なし）

### 修正 (Fixed)
- LLM 呼び出しや API エラー時に例外を雑多に伝播させず、ログ記録の上でフェイルセーフ（スコア 0.0 など）で続行する実装を採用。これにより一部 API障害時でもパイプライン全体が停止しないように設計。

### 既知の注意事項 (Notes)
- OpenAI SDK の例外型や status_code の有無に依存せず堅牢に処理するため getattr 等で対応しているが、将来の SDK 変更に注意。
- DuckDB の executemany に空リストを渡せないバージョンへの互換性に配慮したチェックを行っている（空パラメータは送らない）。
- news_nlp と regime_detector は OpenAI 呼び出し関数を互いに共有せず、モジュール間結合を低減している（テスト用に個別 patch で差し替え可能）。
- J-Quants / kabu API / Slack 等の外部連携はクライアント実装（jquants_client 等）に依存するため、本リポジトリ内でのクライアント実装の存在を想定する。

### セキュリティ (Security)
- .env 自動読み込み時に既存 OS 環境変数を保護（.env による上書きを制限）する仕組みを採用。
- 必須環境変数未設定時は ValueError を発生させ明示的に失敗するため、誤ったランタイム設定のまま実行されるのを防止。

### 破壊的変更 (Breaking Changes)
- 初版のため該当なし。

---

今後のリリースで予定している改善例（参考）
- jquants_client / kabu クライアントの実装公開とテストカバレッジ拡充。
- モデル切替やローカルモック用の抽象化レイヤの追加（テスト容易性向上）。
- 並列化・バッチ処理の性能最適化（OpenAI コールのスループット改善）。
- ai_scores / market_regime / calendar テーブルスキーマのドキュメント化とマイグレーション機能。

もし CHANGELOG に追記してほしい観点（例: より詳細な実装箇所、想定 DB スキーマ、外部依存のバージョンなど）があれば教えてください。コードからさらに深掘りして反映します。