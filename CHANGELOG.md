# Changelog

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。  

現在の日付: 2026-03-31

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース。本リリースでは、日本株自動売買システムのコアライブラリを提供します。
主要モジュールは環境設定、データ ETL / カレンダー管理、研究用ファクター計算、AI を用いたニュース解析・市場レジーム判定などです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期版（__version__ = 0.1.0）。
  - 公開パッケージ API: data, strategy, execution, monitoring を __all__ に設定。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込みを提供。
  - 自動ロードロジック:
    - プロジェクトルートの検出（.git または pyproject.toml を基準）。
    - 読み込み優先順位: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - .env の堅牢なパーサ実装:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い等。
  - Settings クラスで主要設定値をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU/MEMORY/DISK 閾値など。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーション。
    - is_live / is_paper / is_dev ヘルパー。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp.score_news)
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）でセンチメントを評価。
    - バッチ送信（最大 20 銘柄/バッチ）、1 銘柄当たり記事数・文字数制限（記事数: 10、文字数: 3000）でトリム。
    - エラーに対するエクスポネンシャルバックオフとリトライ（429/ネットワーク/タイムアウト/5xx）。
    - レスポンスの厳密な JSON バリデーション（results 配列、code/score）、スコアを ±1.0 にクリップ。
    - 書き込みは冪等（DELETE → INSERT、部分失敗時に既存データを保護）。
    - ルックアヘッドバイアス回避のため datetime.today()/date.today() を参照しない設計。
  - 市場レジーム判定 (kabusys.ai.regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で regime（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news をフィルタ、最大 20 件のタイトルを LLM に送信して macro_sentiment を算出。
    - OpenAI 呼び出しでのリトライ、API 失敗時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフ。
    - 計算結果は market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- データ・ETL モジュール (kabusys.data)
  - ETL 結果型の公開インターフェース (kabusys.data.ETLResult) を定義（pipeline モジュールのデータクラス再エクスポート）。
  - ETL パイプライン (kabusys.data.pipeline)
    - 差分取得、保存（jquants_client の save_* を利用して冪等保存）、品質チェック（quality モジュールとの連携）を想定した ETLResult データクラスを提供。
    - デフォルトのバックフィルやカレンダー先読み等の設計ポリシーを実装。
    - DuckDB を利用した最大日付取得やテーブル存在チェック等のユーティリティを提供。
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を基にした営業日判定ロジックを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日扱い）。
    - calendar_update_job により J-Quants から差分取得して market_calendar に冪等更新（バックフィル、健全性チェック付き）。

- 研究用モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m/3m/6m、ma200 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials を用いて PER, ROE を計算（target_date 以前の最新財務データを使用）。
    - 全関数は prices_daily / raw_financials のみ参照。結果は (date, code) を含む dict のリストで返す。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンのランク相関による IC 計算（欠損/非有限値を除外、有効レコード < 3 は None）。
    - rank: 同順位は平均ランクとするランク付け実装（丸めで ties 対策）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - 研究向けユーティリティとして kabusys.data.stats.zscore_normalize を再エクスポート。

### 変更 (Changed)
- 設計上の重要ポリシー（すべての該当モジュールで適用）
  - ルックアヘッドバイアス防止のため、内部実装は date / target_date に依存し、date.today() / datetime.today() を直接使用しない方針を採用。
  - OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）での処理を前提とし、パースの堅牢性を強化。
  - DuckDB 特性に対応するため、executemany に空リストを渡さないガードを導入（互換性対策）。

### 修正・品質向上 (Fixed / Improved)
- OpenAI API 呼び出しに対する堅牢化
  - 429（レート制限）、ネットワーク断、タイムアウト、5xx に対するリトライ／バックオフ実装。
  - 非 5xx の API エラーや JSON パース失敗時は例外を投げずログを残してフォールバック（0.0 やスキップ）するフェイルセーフ動作を採用。
- DB 書き込みの冪等性確保
  - ai_scores / market_regime などへの書き込みは DELETE → INSERT の手順で実装し、部分失敗時に既存データを不整合にしない工夫。
- .env パーサの堅牢化
  - クォート内エスケープ、コメント扱い、export プレフィックス対応など、多くの .env フォーマット差異に対処。

### 注意事項 / 既知の制約 (Notes / Known issues)
- OpenAI API キーが未設定の場合、score_news / score_regime は ValueError を送出する設計。api_key 引数でキーを注入可能。
- 一部の設計は外部クライアント（jquants_client、quality、slack 等）に依存しており、実行にはそれらの実装と DuckDB のスキーマが必要。
- ETL pipeline の一部実装（ファイル末尾など）や外部モジュールの完全な実装は本リリースに含まれない可能性があるため、実運用前にテストを推奨。

### セキュリティ (Security)
- 本バージョンで特にセキュリティ脆弱性は報告されていません。API キー・シークレットは環境変数経由で管理することを推奨します。

---

この CHANGELOG はソースコードの内容から機能・振る舞いを推測してまとめたものです。実際の変更履歴やリリース日付はリポジトリのタグ付けやリリースノートに準じて更新してください。