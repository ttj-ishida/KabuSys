# Changelog

すべての変更は Keep a Changelog の形式に従い、重要度の高いものから記載しています。  
本リポジトリの初期バージョンは 0.1.0 です。

## [0.1.0] - 2026-03-28

### Added
- パッケージ基盤
  - kabusys パッケージの初期リリース。パッケージバージョンは `0.1.0`。
  - パッケージエクスポート: `__all__ = ["data", "strategy", "execution", "monitoring"]`。

- 設定 / 環境変数管理 (`kabusys.config`)
  - .env / .env.local ファイルおよび OS 環境変数からの設定読み込みを実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）により作業ディレクトリに依存しないロードを実現。
  - `.env` のパースの細かい実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理）。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 環境変数必須チェック `_require` と Settings クラスを提供。主要プロパティ:
    - J-Quants / kabu ステーション / Slack / データベースパス（DuckDB/SQLite）/環境種別・ログレベル等。
  - `KABUSYS_ENV` のバリデーション（development / paper_trading / live）および `LOG_LEVEL` のバリデーション。

- AI モジュール (`kabusys.ai`)
  - news_nlp: `score_news(conn, target_date, api_key=None)` を実装。
    - ニュース収集ウィンドウ計算（JST ベース → UTC 換算）。
    - raw_news と news_symbols から銘柄ごとに記事を集約し、1 銘柄あたりの文字数/件数制限を行う（トリミング有り）。
    - OpenAI (gpt-4o-mini) の JSON Mode を用いてバッチ（最大 20 銘柄）でセンチメントを取得。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。その他エラーはスキップし継続（フェイルセーフ）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、code の照合、数値変換、スコアクリップ）。
    - DuckDB への冪等書き込み（DELETE → INSERT を executemany で実行）および DuckDB 互換性考慮（executemany の空引数回避）。
    - テスト容易性のため OpenAI 呼び出し部分は `_call_openai_api` を通しパッチ可能。
  - regime_detector: `score_regime(conn, target_date, api_key=None)` を実装。
    - ETF 1321 の 200 日移動平均乖離（最新終値 / MA200）を計算（ルックアヘッド防止のため target_date 未満のデータのみ）。
    - マクロキーワードで raw_news をフィルタしてタイトルを収集、LLM（gpt-4o-mini）でマクロセンチメントを評価。
    - MA（重み 70%）とマクロセンチメント（重み 30%）を合成して regime_score を算出しラベルを付与（bull/neutral/bear）。
    - API 障害時は macro_sentiment=0.0 とするフェイルセーフ、API リトライ/5xx の扱いを実装。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施。
    - テスト容易性のため OpenAI 呼び出し部分は独立実装で差し替え可能（モジュール間のプライベート関数共有を避ける設計）。

- データプラットフォーム (`kabusys.data`)
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）と一連のユーティリティ実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB 登録値優先の一貫したフォールバック戦略（未登録日は曜日ベースの判定を使用）。
    - 夜間バッチ: `calendar_update_job(conn, lookahead_days=90)` により J-Quants から差分取得 → 保存（バックフィル・健全性チェック含む）。
  - pipeline / etl:
    - ETLResult データクラスを提供（取得件数・保存件数・品質検査結果・エラー収集など）。
    - 差分更新・バックフィル・品質チェックの考え方を反映した ETL 基盤コードを実装。
    - jquants_client と quality モジュールを想定した保存/検査フロー（詳細実装は jquants_client 側へ委譲）。
  - ETL 型の再エクスポート（kabusys.data.etl が ETLResult を公開）。

- リサーチ / ファクター群 (`kabusys.research`)
  - factor_research:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、MA200 乖離（cnt 200 未満は None）を計算。
    - calc_volatility(conn, target_date): 20 日 ATR, ATR 比率, 20 日平均売買代金, 出来高比率を計算。true_range の NULL 伝播を制御。
    - calc_value(conn, target_date): raw_financials から直近財務を取得して PER / ROE を計算（EPS 0/NULL は None）。PBR/配当利回りは未実装。
    - SQL + DuckDB ウィンドウ関数を活用し、外部 API に依存しない実装。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズン（営業日）先のリターンを一括で取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）計算（有効レコード 3 件未満は None）。
    - rank(values): 同順位は平均ランクを返すランク関数（丸め対策を含む）。
    - factor_summary(records, columns): count/mean/std/min/max/median を算出する統計サマリー。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （特記事項なし）

---

## 既知の制約・注意事項
- OpenAI API
  - news_nlp / regime_detector は OpenAI API（デフォルトモデル gpt-4o-mini）へ依存。API キーが未設定の場合は ValueError を送出する（引数 api_key または環境変数 OPENAI_API_KEY を使用）。
  - レスポンスが期待フォーマットでない場合は該当チャンクをスキップし、フェイルセーフとして残り処理を継続する設計。
- 環境変数
  - `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID` 等、いくつかの値は必須。Settings が未設定を検出した場合は明確なエラーを出力する。
- DuckDB
  - 一部実装は DuckDB のバージョン差（例: executemany に空リストを与えられない等）を考慮している。DuckDB v0.10 系の挙動に対応。
- ルックアヘッドバイアス対策
  - すべてのバックテスト用 / 研究用関数は内部で datetime.today() / date.today() を直接参照せず、明示的な target_date 引数に依存する設計。
- テスト容易性
  - OpenAI 呼び出し部分はモジュール内のラッパー関数を経由しており、unittest.mock.patch により差し替え可能。DB 書き込みはトランザクションで保護されている。
- 未実装/拡張候補
  - ファクター群における PBR / 配当利回りは未実装（将来追加可能）。

もし特定モジュールの変更点をより詳細に分けて記載したい場合や、別バージョン表記（Unreleased 等）を追加したい場合は指示してください。