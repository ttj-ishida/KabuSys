# CHANGELOG

すべての notable な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。  

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-01

初回公開リリース。以下の主要機能とモジュールを追加しました。

### Added
- パッケージ基盤
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"
  - 公開サブパッケージ: data, strategy, execution, monitoring（__all__ に列挙）

- 設定 / 環境変数管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（優先順位: OS 環境変数 > .env.local > .env）
  - .env パーサ実装（コメント、export プレフィックス、クォート内のエスケープ対応、インラインコメント処理など）
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）
  - 環境値の取得ユーティリティ Settings を実装。以下のプロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
    - KABUSYS_ENV（development, paper_trading, live の検証）および LOG_LEVEL 検証
    - is_live / is_paper / is_dev ヘルパー

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメントを取得
  - タイムウィンドウ計算ユーティリティ calc_news_window（JST 基準で前日 15:00 ～ 当日 08:30 を対象）
  - バッチ処理（1 回最大 20 銘柄）、1 銘柄当たり最大記事数・文字数によるトリム
  - 再試行ポリシー（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）
  - API レスポンスの厳密なバリデーション（JSON 抽出、results リスト、既知コードのみ、数値チェック、±1.0 クリップ）
  - 成功したスコアを ai_scores テーブルへ冪等的に置換（DELETE → INSERT、部分失敗に備えコード絞り込み）
  - API キーを引数で注入可能（テスト容易性）、未設定時は環境変数 OPENAI_API_KEY を参照

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）をスコアリング
  - ma200_ratio の計算（target_date 未満のデータのみ使用、データ不足時は中立値を採用）
  - マクロ記事は raw_news からキーワードフィルタで抽出（最大 20 件）
  - OpenAI 呼び出しは独立実装（news_nlp とプライベート関数を共有しない）でリトライ／フォールバック実装あり
  - 結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
  - API キーは引数または環境変数で指定。未指定時は ValueError を送出

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルに基づく営業日判定ロジックを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にデータがない場合は曜日ベース（土日非営業）でフォールバック
    - 夜間バッチ更新 job: calendar_update_job（J-Quants API から差分取得し冪等的に保存、バックフィルと健全性チェックを実装）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー等を格納）
    - 差分更新、バックフィル、品質チェック（kabusys.data.quality を参照）の設計に基づく実装方針を反映
  - ETLResult を data.etl で再エクスポート（public API として提供）

- リサーチ / ファクター（kabusys.research）
  - factor_research: Momentum / Volatility / Value を計算する関数を実装:
    - calc_momentum（1M/3M/6M リターン、ma200_dev。データ不足時は None）
    - calc_volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）
    - calc_value（PER, ROE。raw_financials から target_date 以前の最新財務データを使用）
  - feature_exploration: 将来リターン・IC（Information Coefficient）・ファクター統計
    - calc_forward_returns（複数ホライズン対応、入力検証、パフォーマンス最適化）
    - calc_ic（スピアマンのランク相関、データ不足時は None）
    - rank（同順位は平均ランクにする実装）
    - factor_summary（count/mean/std/min/max/median の算出）
  - zscore_normalize を data.stats からインポートして再公開
  - 研究用 API は DuckDB 接続を受け取り、外部通信や取引 API へはアクセスしない設計

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは関数引数で注入可能にし、環境変数依存を緩和（テスト/運用でのキー漏洩リスク軽減に寄与）

注記・設計上の重要点
- ルックアヘッドバイアス防止: 各処理は内部で datetime.today()/date.today() を参照せず、必ず外部から渡された target_date を基準に動作します。
- フェイルセーフ: OpenAI API 呼び出し失敗時やデータ不足時は例外を上位へ投げずにフォールバック（0.0 や中立値）して処理を継続する箇所があり、バッチ処理の堅牢性を重視しています。
- DB 書き込みは冪等性を意識（DELETE→INSERT や ON CONFLICT 相当の保存を想定）して実装しています。
- DuckDB を主要なローカルデータストアとして利用する前提です。API クライアント（jquants_client）と品質チェック（quality）モジュールへの参照があります（これらは別モジュールとして実装される想定）。

--- 

注: 本 CHANGELOG はコードベースの内容から推測して記載しています。実際のリリースノートとして利用する場合は、差分やコミット履歴・リリース担当者の確認を推奨します。