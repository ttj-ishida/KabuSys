# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に沿って管理しています。  

※日付はリリース日を示します。

## [Unreleased]
- 今後の変更予定

## [0.1.0] - 2026-04-04
初回リリース

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを公開。__version__ = 0.1.0。
  - パッケージ内モジュール群を export（data, strategy, execution, monitoring）。

- 設定管理 (kabusys.config)
  - .env ファイルと環境変数を統合的に読み込む自動ロード機能を実装。
    - プロジェクトルートは .git または pyproject.toml を基準に __file__ から探索（CWD 非依存）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - POSIX 風の .env パース実装（export KEY=val, クォート、エスケープ、行末コメント対応）。
  - Settings クラスを提供し、環境変数をプロパティ経由で取得可能：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL などのキーをサポート。
    - DBパス（DUCKDB_PATH, SQLITE_PATH）、監視関連設定（PID/KILLフラグ/閾値）などのデフォルトと型安全な取得。
    - KABUSYS_ENV の検証（development / paper_trading / live）および LOG_LEVEL 検証。
    - is_live/is_paper/is_dev の利便性プロパティ。

- データ関連 (kabusys.data)
  - カレンダー管理 (calendar_management)
    - JPX マーケットカレンダー管理機能。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar テーブルがない場合は曜日ベースでフォールバック。
    - calendar_update_job: J-Quants から差分取得し冪等に保存（バックフィル・健全性チェック付き）。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（ターゲット日、取得件数、保存件数、品質問題、エラー等を格納）。
    - ETL 差分取得・保存・品質チェックの設計方針に沿ったインターフェースを提供。
    - jquants_client 経由の保存処理を想定（idempotent 保存）。

- AI/自然言語処理 (kabusys.ai)
  - ニュース NLP (news_nlp)
    - raw_news / news_symbols を集約して銘柄単位にテキストを結合、OpenAI (gpt-4o-mini) の JSON Mode を用いてセンチメントを算出。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたり記事数・文字数制限（トークン肥大化対策）を実装。
    - 429・ネットワーク・タイムアウト・5xx に対する再試行（指数バックオフ）。その他エラーはスキップしフェイルセーフに処理。
    - レスポンスバリデーション（JSON 抽出、results 配列検査、コード照合、数値変換、クリップ）。
    - ai_scores テーブルへの置換的書き込み（部分失敗時に既存スコアを保持するためコードを絞って DELETE → INSERT）。
    - テスト容易性を考慮し、内部の OpenAI 呼び出し関数をモック可能に設計。
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算を提供（時間帯のUTC変換を明確化）。
  - 市場レジーム判定 (regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - OpenAI (gpt-4o-mini) を JSON Mode で利用、API のリトライ/バックオフを実装。API 失敗時は macro_sentiment=0.0 としてフェイルセーフ。
    - ルックアヘッドバイアス防止のため、target_date 未満のデータのみを使用し datetime.today() を参照しない設計。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書込み失敗時は ROLLBACK を試行。

- リサーチ (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR（平均）、相対 ATR、20 日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から EPS/ROE を取り込み PER/ROE を算出（EPS が 0/欠損時は None）。
    - DuckDB の SQL ウィンドウ関数を活用した実装。
  - feature_exploration:
    - calc_forward_returns: 将来リターン計算（指定ホライズンに対応、ホライズン検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。検証・フィルタリングを実施（有効レコード < 3 なら None）。
    - rank: 同順位は平均ランクを返す実装（丸め処理で ties の検出を安定化）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算。
  - 研究向けユーティリティをまとめて再エクスポート。

### 変更 (Changed)
- （初回リリースのため履歴上の変更はなし。設計上の注意点やフェイルセーフ動作を実装ドキュメントとして記載）

### 修正 (Fixed)
- （初版のため該当なし）

### 破壊的変更 (Deprecated / Removed)
- （初版のため該当なし）

### セキュリティ (Security)
- OpenAI API キーの取り扱いや自動ロードは環境変数を優先することで誤設定リスクを低減。
- 環境変数必須項目未設定時は ValueError を発生させて明示的に通知。

### 備考・設計上の重要点
- DuckDB を主要なストレージインターフェースとして使用。SQL と Python を組み合わせた処理を想定。
- 多くの箇所で「ルックアヘッドバイアス防止」を明確に設計（target_date 未満のデータ利用、datetime.today() 参照禁止）。
- OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）を利用。レスポンスパース失敗時は安全にフォールバック。
- DB 書き込みは冪等性を意識（DELETE→INSERT のパターンなど）して実装。
- テスト容易性を配慮し、内部 API 呼び出しの差し替えポイント（_call_openai_api 等）を用意。

---
ここに記載されている内容はソースコード（docstring、関数名、定数、処理フロー）から推測してまとめた変更履歴です。実際のリリースノートに反映する際は、リリース手続きや実際の変更差分に合わせて調整してください。