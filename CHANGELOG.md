# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従います。  

なお、以下はソースコードの内容から推測して作成した変更履歴です。

## [0.1.0] - 2026-03-28

### Added
- パッケージの初期リリース。
  - パッケージバージョン: `0.1.0`（src/kabusys/__init__.py にて定義）
  - メインエクスポート: data, strategy, execution, monitoring

- 環境設定・自動 .env ロード機能（src/kabusys/config.py）
  - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動読み込み（CWDに依存しない実装）。
  - export KEY=val 形式やクォート／エスケープ、行内コメントを考慮した堅牢なパーサを実装。
  - OS 環境変数を保護する protected パラメータを用いた上書き制御（.env.local が .env を上書き）。
  - 自動ロードの無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - 必須環境変数取得ヘルパ `_require` と Settings クラスを提供（J-Quants, kabu, Slack, DB パス、実行環境、ログレベルなど）。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を元に銘柄ごとのニューステキストを集約し、OpenAI（gpt-4o-mini, JSON mode）で銘柄ごとのセンチメントを算出して ai_scores テーブルへ保存するワークフローを実装。
  - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算するユーティリティ `calc_news_window` を提供。
  - バッチ処理（1 API 呼び出しで最大 20 銘柄）と、1 銘柄あたりの記事数・文字数トリム（デフォルト：最大記事数10、最大文字数3000）を導入。
  - レートリミット・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ実装（最大リトライ回数と待機時間は定数化）。
  - JSON レスポンスの堅牢なバリデーションとパース（前後余計なテキストが混ざるケースへの復元処理含む）。
  - スコアを ±1.0 にクリップし、取得済みコードのみを置換（DELETE → INSERT）することで部分失敗時に既存スコアを保護。
  - テストしやすさのためのフック（_call_openai_api を patch で差し替え可能）。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF（1321）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等的に書き込む実装を追加。
  - マクロ記事取得は news_nlp の時間窓計算 util を利用。
  - OpenAI 呼び出しは独立実装（モジュール結合を避ける設計）。
  - API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ実装。
  - リトライ（RateLimitError・接続エラー・タイムアウト・5xx）とエラーハンドリングを実装。
  - レジーム合成のクリップおよび閾値処理（bull/bear/neutral）を実装。
  - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT で冪等性を確保、失敗時は ROLLBACK を試行。

- 研究用ファクター計算（src/kabusys/research）
  - factor_research.py: Momentum / Volatility / Value 等の定量ファクター計算を実装。
    - モメンタム: mom_1m, mom_3m, mom_6m, ma200_dev（データ不足時は None を返す設計）。
    - ボラティリティ/流動性: 20 日 ATR（atr_20）、相対 ATR、20 日平均売買代金、出来高比率。
    - バリュー: PER（EPS が 0/NULL の場合は None）、ROE（raw_financials からの取得）。
    - DuckDB のウィンドウ関数を活用した SQL ベースの実装。
  - feature_exploration.py:
    - 将来リターン計算 calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）および rank ユーティリティ（同順位は平均ランク）。
    - factor_summary：カウント/平均/標準偏差/最小/最大/中央値の統計要約。
  - research パッケージ __init__ で主要関数を公開。zscore_normalize を data.stats から再利用。

- データプラットフォーム関連（src/kabusys/data）
  - calendar_management.py:
    - JPX カレンダーの管理ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が存在しない場合の曜日ベースフォールバック（週末非営業日扱い）。
    - DB 値優先・未登録日は曜日ベースで一貫した挙動を提供。
    - カレンダーバッチ更新 job（calendar_update_job）：J-Quants から差分取得して保存（バックフィル、健全性チェック、J-Quants クライアント利用）。
  - pipeline.py / etl.py:
    - ETLResult データクラスおよび ETL パイプラインのユーティリティ（差分取得、保存、品質チェックの統合設計）。
    - ETLResult.to_dict() による品質問題の要約出力。
    - DuckDB 周りの補助関数（テーブル存在チェック、最大日付取得）も実装。
    - etl.py は pipeline.ETLResult を再エクスポート。

- ドキュメント的な設計注釈（各モジュールの docstring）
  - ルックアヘッドバイアス対策（datetime.today()/date.today() を内部処理で直接参照しない設計等）
  - DuckDB 互換性や実装上の注意点（executemany の空リスト制約など）を明示。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を使用。キー管理はユーザー側で行う設計。

## 注記 / 既知の制約・設計上の決定
- DuckDB に依存した実装のため、特定バージョン（例: executemany の空リスト扱い）に起因する挙動が発生する可能性があることをコード中で扱っている（空リストは executemany しない等）。
- 時刻は基本的に UTC naive の datetime / date を使用し、タイムゾーンの混入を避ける設計（ニュースウィンドウでは JST→UTC 変換を行う）。
- OpenAI 呼び出しは gpt-4o-mini を想定。JSON mode の応答をパースするための冗長な復元ロジックを含むが、LLM の応答仕様変更によりパースの失敗が起こる可能性がある。
- API 呼び出し失敗はフェイルセーフ（スコア 0.0 を使用、または該当銘柄をスキップ）として継続する方針。
- テスト容易性のため、外部 API 呼び出し部分（_call_openai_api 等）は patch で差し替え可能。

## マイグレーション / 利用開始ガイド（簡易）
- .env / .env.local に必要な環境変数を設定してください（.env.example を参照する想定）。
  - 必須例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（または api_key 引数で注入）
- DuckDB/SQLite のパスは環境変数で上書き可能（DUCKDB_PATH, SQLITE_PATH）。
- 自動 .env 読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- OpenAI API の呼び出しや J-Quants 連携はネットワークアクセスを伴うため、適切なキーとネットワーク環境を用意してください。

---

今後のリリースでは、細かなバグ修正、テストカバレッジの拡充、外部依存のバージョン互換性対応、さらに strategy/execution/monitoring 関連の具現化が想定されます。必要があればこの CHANGELOG を更新します。