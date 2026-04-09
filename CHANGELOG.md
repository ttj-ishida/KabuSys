# Changelog

すべての変更は Keep a Changelog の仕様に従って記載しています。  
安定版リリース (初版): 0.1.0

<!-- 引数: 日付は 2026-04-09 -->
## [0.1.0] - 2026-04-09

### 追加
- 全体
  - パッケージ初期版を公開。モジュール構成は主に data / ai / research / config 周りを含む。
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。

- 環境設定 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む `Settings` クラスを追加。
  - 自動ロード機能: プロジェクトルート（.git または pyproject.toml）を探して `.env` → `.env.local` の順に読み込み。OS 環境変数を保護（上書き不可）する仕組みを実装。
  - 自動ロード抑止用の環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用に便利）。
  - .env パーサーの強化:
    - `export KEY=val` 形式に対応
    - シングル/ダブルクォート内のエスケープ処理対応
    - インラインコメントの扱いを文脈に応じて正しく解釈
  - 各種設定プロパティを実装（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, DB パス, Paper Trading 関連など）。
  - 設定値バリデーションを追加:
    - `PAPER_FILL_MODE`（"instant"|"partial"|"never"|"reject"）
    - `KABUSYS_ENV`（development|paper_trading|live）
    - `LOG_LEVEL`（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - 監視関連の設定（PID ファイル、kill フラグ、CPU/メモリ/ディスク閾値）を提供。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）により銘柄ごとにセンチメントスコアを算出し、ai_scores テーブルへ書き込む処理を実装。
    - JST の時間窓計算（前日 15:00 JST 〜 当日 08:30 JST）を行う `calc_news_window` を実装（DB 比較のため UTC naive datetime を返す）。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、記事数・文字数上限、安全な JSON Mode パース、レスポンスバリデーションを実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対するエクスポネンシャルバックオフ・リトライを実装。失敗時はフェイルセーフでスキップ（例外を荒く投げず継続）。
    - テスト用に `_call_openai_api` をモック差し替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定、`market_regime` テーブルへ冪等書き込み。
    - MA 計算はルックアヘッド防止（target_date 未満のデータのみ使用）。
    - マクロニュース抽出（キーワードリスト）→ OpenAI で JSON 出力を想定してパース → 重み付け合成。
    - OpenAI API 呼び出しに対してリトライ/バックオフを実装。API 失敗時はマクロセンチメントを 0.0 にフォールバック（フェイルセーフ）。
    - テスト時に差し替え可能な `_call_openai_api` を独立実装（モジュール間のプライベート関数共有を避ける設計）。

- データプラットフォーム (kabusys.data)
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX マーケットカレンダーを扱うユーティリティ群を実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar が存在しない場合の曜日ベースフォールバック（週末は非営業日）を実装し、DB 登録がある場合は DB 値を優先する動作。
    - 夜間バッチ job `calendar_update_job` を実装。J-Quants クライアントから差分取得 → 冪等保存。バックフィル・健全性チェックを実装。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - 差分取得・保存・品質チェックのフレームワークを用意。
    - ETL 実行結果を格納する `ETLResult` データクラスを公開（to_dict 等のユーティリティ含む）。
    - デフォルトのバックフィルや最小データ日など ETL に関する定数を定義。
    - jquants_client および quality モジュールと連携する設計。
  - jquants_client と quality への依存を想定した実装（実行時に具体実装を注入して利用）。

- リサーチ / ファクター (kabusys.research)
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M）、200 日移動平均乖離、ATR（20 日）、流動性指標（20 日平均売買代金・出来高割合）などを DuckDB 上の SQL と Python ロジックで実装。
    - prices_daily / raw_financials のみを参照し、本番発注などの副作用はなし。
    - データ不足時の扱い（必要行数未満は None）を明確化。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、horizons の検証含む）。
    - IC（Information Coefficient）計算（スピアマンの ρ をランクで計算）。
    - ランク関数（同順位は平均ランク）、統計サマリー（count/mean/std/min/max/median）を実装。
  - 研究用ユーティリティをパッケージとして再エクスポート（zscore_normalize 等）。

### 変更
- 設計方針の明確化（ドキュメンテーションコメント内）
  - 主要なモジュール（AI・ETL・research）は「ルックアヘッドバイアス防止」のため datetime.today()/date.today() を直接参照しない設計を採用。
  - DB 書き込みは可能な限り冪等に実装（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK 管理）。
  - DuckDB のバージョン差分（executemany の空パラメータ等）の扱いに配慮した互換性対応。

### 修正
- エラー処理の堅牢化
  - OpenAI 呼び出し周りでの例外 (RateLimit, APIConnectionError, APITimeoutError, APIError) を分類し、5xx サーバーエラーやネットワークエラーはリトライ、それ以外はフォールバックして継続するように実装。
  - DB 書き込み失敗時に ROLLBACK 試行し、ROLLBACK が失敗した場合は警告ログを出力。

### 注意 / マイグレーション
- 環境変数が必須な設定（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY（AI モジュール実行時））は未設定時に ValueError を投げる設計です。動作させる前に `.env` または OS 環境変数を設定してください。
- OpenAI 関連:
  - news_nlp/regime_detector は gpt-4o-mini を使用する想定。API キーは `OPENAI_API_KEY` または各関数の `api_key` 引数で注入可能。
  - テスト時には `_call_openai_api` をモックすることで外部 API へのアクセスを無効化できます。
- DuckDB スキーマ:
  - 各モジュールは prices_daily / raw_news / news_symbols / ai_scores / market_regime / market_calendar / raw_financials など特定のテーブルスキーマを前提としています。実行前にスキーマ整備を行ってください。

### 未解決 / 既知の制約
- 一部関数は外部クライアント（jquants_client、quality）に依存しており、実行環境で該当実装が必要です。
- ETL の詳細な pipeline 実装（差分取得ロジックの具体的な呼び出し順序等）は本リリースで基盤を提供しており、運用上のポリシーに応じた追加実装が想定されます。

---

今後の予定（例）
- テストカバレッジの強化（ユニット / 結合テスト）
- jquants_client / quality の具体実装を同梱するか、インストール時の依存化を明確化
- モニタリング / 実行時ダッシュボードの追加

（初版リリースのため、以降の変更は Unreleased セクションに追記してください）