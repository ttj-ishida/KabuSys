CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。
リリースはセマンティックバージョニングに従います。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-28
--------------------

Added
- 初回公開（基本機能群を実装）
  - パッケージ基盤
    - kabusys パッケージ初期化（__version__ = 0.1.0、公開サブパッケージ: data, strategy, execution, monitoring）。
  - 設定 / 環境変数管理（kabusys.config）
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env のパースロジックを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱い等に対応）。
    - .env の上書きルール: OS 環境変数 > .env.local（上書き） > .env（未設定時にのみ設定）。
    - 必須環境変数取得ヘルパー _require を提供（未設定時は ValueError を送出）。
    - 設定オブジェクト Settings を公開。主なプロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
      - KABUSYS_ENV（許容値: development, paper_trading, live）と関連ユーティリティ（is_live 等）
      - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - AI モジュール（kabusys.ai）
    - ニュース NLP（kabusys.ai.news_nlp）
      - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
      - JST ベースのニュース時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST → UTC 変換ロジック）を実装。
      - バッチサイズ、トークン肥大化対策（記事数上限・文字数上限）を実装。
      - JSON Mode を利用した出力パース、レスポンスのバリデーション、スコアの ±1.0 クリップ。
      - API レート制限/ネットワーク断/タイムアウト/5xx に対するエクスポネンシャルバックオフによるリトライ。
      - レスポンスの部分不備や API 失敗時はフェイルセーフでスキップしログに警告を出力。
      - DuckDB への書き込みは冪等（DELETE → INSERT）で行い、部分失敗時に既存データを保護する実装。
      - 公開関数: score_news(conn, target_date, api_key=None) -> 書き込んだ銘柄数。
    - 市場レジーム判定（kabusys.ai.regime_detector）
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
      - マクロキーワードで raw_news をフィルタし、OpenAI（gpt-4o-mini）でマクロセンチメントを評価。
      - API 呼び出し失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
      - 判定結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
      - 公開関数: score_regime(conn, target_date, api_key=None) -> 1（成功）
    - テスト容易性のため、OpenAI 呼び出し部分は内部で関数化され、unittest.mock.patch による差し替えを想定。
  - データモジュール（kabusys.data）
    - マーケットカレンダー管理（kabusys.data.calendar_management）
      - market_calendar テーブルを参照する営業日判定ユーティリティを実装:
        - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
      - DB データがない/未取得時は曜日ベース（土日非営業日）でフォールバック。
      - next/prev に最大探索日数の上限（_MAX_SEARCH_DAYS=60）を設けて無限ループを防止。
      - calendar_update_job による夜間バッチ更新ロジック（J-Quants から差分取得、バックフィル、健全性チェック、保存）を実装。
    - ETL / パイプライン（kabusys.data.pipeline / etl）
      - ETLResult データクラスを公開（ETL 実行結果の集約）。
      - 差分取得・保存・品質チェックを行うパイプライン設計（jquants_client 経由の idempotent 保存、品質チェックの集約レポート化）。
      - DuckDB の executemany に関する互換性（空リストバインド対策）に配慮した実装。
  - 研究/リサーチモジュール（kabusys.research）
    - factor_research:
      - Momentum（1M/3M/6M リターン、200日 MA 乖離率）、Volatility（20日 ATR 等）、Value（PER/ROE）計算を実装。
      - DuckDB 上で SQL を用いて効率的に計算。データ不足時は None を返す設計。
    - feature_exploration:
      - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）を実装。
      - pandas 等の外部依存を使わず、標準ライブラリと DuckDB のみで実装。
  - いくつかのユーティリティ/補助実装
    - duckdb 結果の date 型変換ヘルパー、テーブル存在チェック等。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数や API キーは Settings 経由で扱うことを想定。.env ファイルの読み取りは UTF-8 で行い、読み込み失敗時は警告を出力して継続。

Known limitations / Notes（既知の制約・設計上の注意）
- OpenAI 関連
  - 使用モデルは現状 gpt-4o-mini にハードコードされている。
  - API 呼び出しは外部依存のため、ローカルテストでは patch による差し替えを推奨。
  - API キーは関数引数で注入可能（api_key=None の場合は環境変数 OPENAI_API_KEY を参照）。未設定の場合は ValueError を送出する。
  - レスポンスパースや API エラーは多くの箇所でフェイルセーフ（0.0 や空スコアで継続）になっているため、呼び出し側でログを確認する必要がある。
- 時刻/タイムゾーン
  - ニュースの時間ウィンドウでは JST を基準に UTC naive datetime を用いて DB と照合する設計。timezone 情報は混入させない前提。
- ルックアヘッドバイアス対策
  - datetime.today() / date.today() を計算ロジック内で直接参照しない方針。target_date に依存した計算を行うよう設計されている（テスト/検証の容易化）。
- DuckDB 関連
  - DuckDB のバージョン差異（例: executemany の空リスト問題、リスト型バインドの挙動）に配慮して実装されているが、運用環境の DuckDB バージョンでの動作確認を推奨。
- データ不足時の扱い
  - MA200 等で過去データが不足する場合は中立（1.0 や None）を返す等のフォールバックを行うため、上流でのデータ品質が結果に影響する。

開発者向けメモ
- テスト容易性のため、OpenAI 呼び出し部分（_call_openai_api など）はモック/パッチで差し替え可能に設計されています。
- 自動 .env ロードはプロジェクトルートの検出に依存するため、パッケージ配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して明示的に環境を制御してください。
- 必須の環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - AI 機能を使う場合は OPENAI_API_KEY（または各関数に api_key を渡す）

-----

この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノート作成時には運用上の決定（例えばリリース日、既知のバグ、互換性の詳細など）を反映してください。