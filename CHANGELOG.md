# CHANGELOG

すべての重要なリリースの変更点をここに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。  

なお、本ファイルはコードベースの内容から機能・設計意図を推測して作成しています。

## [Unreleased]
- 現在なし

## [0.1.0] - 2026-03-28
初回公開リリース。

### 追加 (Added)
- パッケージ基本情報
  - kabusys パッケージの初期バージョン（__version__ = 0.1.0）。

- 環境設定
  - .env ファイルまたは環境変数から設定を自動読み込みする設定モジュールを追加（kabusys.config）。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準）。
  - .env / .env.local の読み込みルール（OS 環境変数優先、.env.local は上書き）を提供。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。
  - 必須環境変数未設定時に明示的なエラーを出す _require() 実装。
  - 設定値の妥当性検査（KABUSYS_ENV の許容値・LOG_LEVEL の検証）と補助プロパティ（is_live, is_paper, is_dev）を実装。
  - データベースパスに対する Path 返却（duckdb/sqlite）。

- AI（自然言語処理）機能
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメントを取得。
    - バッチ化（最大 20 銘柄/リクエスト）、トークン肥大化対策（記事数・文字数制限）を実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - レスポンスのバリデーション（JSON 抽出、results 配列、コード整合、数値チェック）とスコアクリップ（±1.0）。
    - ai_scores テーブルへの冪等的書き込み（対象コードに対する DELETE → INSERT）を実装。
    - テストのために OpenAI 呼び出しを差し替え可能（_call_openai_api を patch できる）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - LLM には gpt-4o-mini を利用。JSON 出力を想定。
    - API 失敗時のフェイルセーフ（macro_sentiment=0.0）、およびリトライ/エラーハンドリングを実装。
    - market_regime テーブルへ冪等的に書き込むトランザクション処理（BEGIN/DELETE/INSERT/COMMIT と ROLLBACK の保護）。
    - ルックアヘッドバイアスを避ける設計（date < target_date の排他条件、datetime.today() 未使用）。
    - テスト容易性のため _call_openai_api の差し替えを意図。

- データ管理・ETL
  - ETL パイプライン用の ETLResult データクラスを公開（kabusys.data.pipeline / kabusys.data.etl）。
    - ETL 結果の集約（取得数・保存数・品質問題・エラー）とユーティリティ（to_dict, has_errors, has_quality_errors）。
  - market_calendar を扱うカレンダーモジュール（kabusys.data.calendar_management）
    - 営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データがない場合の曜日ベースフォールバックを採用。
    - カレンダー夜間バッチ更新ジョブ（calendar_update_job）を実装し、J-Quants クライアント経由で差分取得→保存を実行。
    - バックフィル / 健全性チェック（未来日数上限）を導入。
  - ETL 用ユーティリティ（kabusys.data.pipeline）
    - 差分更新、バックフィル、品質チェックの設計方針に沿ったヘルパー実装（内部関数としてテーブル存在チェック、最大日付取得等を提供）。

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）
    - Volatility / Liquidity（20日 ATR、相対ATR、平均売買代金、出来高比）
    - Value（PER、ROE。raw_financials から直近レコード取得）
    - DuckDB を用いた SQL ベース実装。結果は date, code を含む dict のリストで返却。
    - データ不足時の None の扱いやログ出力を実装。
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：任意ホライズンに対応、入力検証。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンのランク相関を実装（同順位は平均ランク処理）。
    - ランク変換ユーティリティ（rank）：丸めによる ties 考慮。
    - ファクター統計サマリー（factor_summary）：count/mean/std/min/max/median を算出。
  - 研究向けユーティリティ群を __all__ で公開。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- 環境変数の自動ロードで OS 環境変数を保護するため protected set を導入（.env の上書きを制御）。
- .env パース機構でシングル/ダブルクォートやエスケープ、コメント処理に対応し、安全に値を読み取るように実装。

### 注意事項 / 設計上の制約
- DuckDB 依存: 内部で DuckDB を利用するため、実行環境に duckdb および該当テーブル（prices_daily など）が必要。
- OpenAI 依存: news_nlp / regime_detector は OpenAI API（gpt-4o-mini）を利用する。API キーは引数で注入可能（テスト用）または環境変数 OPENAI_API_KEY を使用。
- ルックアヘッドバイアス対策: 多くの処理で datetime.today()/date.today() を外部参照しない設計。target_date を明示して実行することを想定。
- トランザクションとロールバック: DB 書き込みは冪等性と失敗時のロールバック処理を考慮しており、部分失敗時でも既存データを不必要に消さない設計。
- テスト容易性: OpenAI 呼び出しはモジュール内関数でラップしてあり、ユニットテストで差し替え可能。

### 既知の制限 / 今後の改善候補
- 現時点では PBR や配当利回りなどのバリュー指標は未実装（calc_value に注釈あり）。
- ETL の品質チェックモジュール（quality）や jquants_client の具体実装は外部に依存しており、実運用時に接続設定が必要。
- OpenAI のモデルやレスポンスフォーマット変化に対する互換性は考慮しているが、将来的な SDK の変更には注意が必要。

---

（備考）本 CHANGELOG はソースコードから読み取れる機能・設計意図に基づいて作成しています。実際のリリースノートでは、実装日・テスト結果・マイグレーション手順・依存パッケージのバージョンなどを併せて記載することを推奨します。