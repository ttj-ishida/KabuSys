# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠します。  

## [Unreleased]

なし

## [0.1.0] - 2026-03-31

初回リリース — KabuSys 日本株自動売買システムのコア機能を実装しました。主にデータ基盤、リサーチ（ファクター）、AI ベースのニュース評価、マーケットカレンダー管理、および設定/環境変数管理の実装を含みます。

### 追加 (Added)
- パッケージの基本構成
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。
  - main エクスポート: ["data", "strategy", "execution", "monitoring"]。

- 設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション。
  - .env パーサーの実装（export 文、クォート内エスケープ、インラインコメント対応）。
  - 環境変数保護（OS 環境変数を protected として上書き防止）をサポート。
  - Settings クラスを提供しアプリ設定をプロパティで安全に取得
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須設定の検証。
    - DB パス（duckdb / sqlite）、監視用閾値（CPU/メモリ/ディスク）、PID ファイルパス等のデフォルト設定。
    - 環境（development / paper_trading / live）や LOG_LEVEL の検証ユーティリティ。

- データ基盤・ETL (kabusys.data.pipeline / etl)
  - ETLResult データクラスを公開（ETL のフェッチ/保存件数、品質問題、エラーの収集と to_dict）。
  - 差分フェッチ、バックフィル、品質チェックを行う ETL パイプライン設計（J-Quants クライアント経由での差分取得を想定）。

- マーケットカレンダー管理 (kabusys.data.calendar_management)
  - JPX カレンダーの夜間バッチ更新ジョブ (calendar_update_job)。
  - market_calendar テーブル優先の営業日判定（is_trading_day、is_sq_day、next_trading_day、prev_trading_day、get_trading_days）。
  - DB 未収録日は曜日ベースでフォールバックする一貫したロジック。
  - バックフィル、ルックアヘッド、安全性チェック（将来日付の健全性検査）を実装。

- リサーチ / ファクター計算 (kabusys.research)
  - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
  - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
  - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。
  - calc_forward_returns: 将来リターン（複数ホライズン）を一度のクエリで取得。
  - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。
  - rank, factor_summary: ランク算出（同順位は平均ランク）と基本統計量サマリ。

- AI（ニュース NLP / レジーム検出） (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols から銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）にバッチ送信。
    - JSON Mode を使用し、レスポンス検証（results リスト、code/score）とスコアの ±1.0 クリップ。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
    - API 失敗やパース失敗はフェイルセーフでスキップし、部分成功時は DB 上の他銘柄スコアを保護（DELETE→INSERT の置換）。
    - calc_news_window: ターゲット日の前日15:00 JST〜当日08:30 JST に相当する UTC 時間ウィンドウの計算を提供。
    - テスト容易性のため _call_openai_api をパッチ可能に実装。

  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を算出・DB へ書き込み。
    - マクロキーワードフィルタに基づく記事抽出、OpenAI 呼び出し（gpt-4o-mini、JSON 結果）と堅牢なリトライ/フォールバック（API 失敗時 macro_sentiment=0.0）。
    - ルックアヘッドバイアス防止（target_date 未満のデータのみを使用）を設計方針として遵守。
    - DB 書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）で実装。失敗時はロールバック。

- DuckDB を主要な分析ストアとして使用
  - 多くの処理が DuckDB 接続を受け取り、SQL ウィンドウ関数や LEAD/LAG、ROW_NUMBER を活用して実装。

- テスト・ロギング・堅牢性
  - API 呼び出しや DB 書き込みでの例外処理とログ出力を充実させ、フェイルセーフ動作に注力。
  - テスト時に差し替え可能な内部呼び出し点（OpenAI 呼び出しなど）を提供。

### 変更 (Changed)
- 初回公開のため該当なし（新規実装）。

### 修正 (Fixed)
- 初回公開のため該当なし。

### 削除 (Removed)
- 初回公開のため該当なし。

### 既知の制約・注意事項 (Known issues / Notes)
- OpenAI API キー（environment 変数 OPENAI_API_KEY または関数引数）が必須。未設定時は ValueError を送出する実装。
- news_nlp と regime_detector は gpt-4o-mini の JSON Mode に依存するため、実行時の API の挙動に影響される点に注意。
- DuckDB executemany に関する互換性（空リスト不可）を考慮した実装が行われているが、利用する DuckDB のバージョン差異に注意。
- calendar_update_job や ETL ジョブは外部 J-Quants クライアント（jquants_client）や quality モジュールに依存する（これらの実装／設定が必要）。

### セキュリティ (Security)
- 環境変数に API キー等の機密情報を想定。自動 .env ロード機能では既存の OS 環境変数を保護する設計（.env.local は上書き可能だが、OS 環境変数は protected）。
- 外部 API キーは直接ログに出力しないことを想定した実装方針。

---

参照: この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノート作成時は、リリース手順・バージョン管理ルールに合わせて日付や細部を調整してください。