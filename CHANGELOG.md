# Keep a Changelog 準拠 CHANGELOG

すべての変更はセマンティックバージョニングに従います。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-01
初回リリース。本リポジトリの主要機能を実装しました。以下はコードベースから推測した主要な追加点・設計方針・既知の挙動です。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョン定義と公開サブパッケージ指定を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
- 環境設定管理
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装（src/kabusys/config.py）。
  - 自動 .env 読み込み（プロジェクトルートの検出による優先読み込み: OS env > .env.local > .env）。
  - .env パースの細かい挙動（export 形式、クォート中のエスケープ、インラインコメントの扱い）に対応。
  - 必須環境変数チェック（_require）と各種設定プロパティ（J-Quants / kabu API / Slack / DBパス / 監視閾値 / 環境・ログレベル検証）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
- AI（NLP）機能
  - ニュースセンチメント解析: score_news（src/kabusys/ai/news_nlp.py）
    - ニュースの時間ウィンドウ計算（JST → UTC 変換）、銘柄ごと記事集約、OpenAI（gpt-4o-mini）へのバッチ送信、レスポンスのバリデーション、結果の ai_scores テーブルへの書き込み。
    - バッチサイズ、記事数/文字数上限、JSON mode 期待のレスポンス整形、リトライ（429/接続/タイムアウト/5xx）を実装。
    - DuckDB の executemany 空配列制約への配慮（空チェックを行う）。
  - 市場レジーム判定: score_regime（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）判定。
    - OpenAI 呼び出し・リトライ・フェイルセーフ（API失敗時 macro_sentiment=0.0）を実装。
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - ai パッケージ公開 API の整理（src/kabusys/ai/__init__.py）。
- データプラットフォーム機能（DuckDB ベース）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、calendar_update_job（J-Quants から差分取得・バックフィル・健全性チェック）を実装。
    - market_calendar が未取得の場合は曜日ベース（平日のみ営業）でフォールバック。
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを追加（ETL のフェッチ数/保存数/品質問題/エラーの集約）。
    - 差分取得・backfill・品質チェック（quality モジュール参照）を想定した設計。
    - jquants_client と連携する想定の差分保存フローを実装（save_* を利用する想定）。
  - jquants_client の再エクスポート等の準備を想定。
- 研究系（Research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M、ma200乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）、Liquidity 指標の計算を実装。
    - DuckDB SQL ウィンドウ関数を活用し、必要データ不足時は None を返すなど堅牢化。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等には依存せず標準ライブラリのみで実装。
  - research パッケージの __init__ にて主要関数を公開。
- ロギング・設計方針
  - ほとんどの処理で詳細な logger メッセージを追加（info/warning/debug）。
  - ルックアヘッドバイアス防止のため、内部で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す方式）。
  - DB 書き込みは冪等性を重視（DELETE→INSERT、executemany を用いた個別 DELETE 等）。
- エラーハンドリングと再試行
  - OpenAI API 呼び出しに対して指数バックオフ再試行を実装（retry 回数・ベース遅延等の定数化）。
  - レスポンスパース失敗や API の非致命的エラーはフェイルセーフ（例: スコアを 0.0 として継続）で処理。

### Changed
- （初版のため履歴無し）

### Fixed
- （初版のため履歴無し）

### Deprecated
- （初版のため履歴無し）

### Removed
- （初版のため履歴無し）

### Security
- OpenAI API キーは引数で注入可能（api_key 引数）か環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出して明示的に要求する実装。
- 環境変数の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト用途想定）。

### Known limitations / 注意点（コードから推測）
- OpenAI の利用には API キーが必須。API 失敗時の挙動は「スコア 0.0 にフォールバック」であり、失敗自体はサイレントに継続される箇所がある（警告ログは出る）。
- DuckDB の executemany が空リストを受け付けない制約に合わせた処理が入っているため、バージョン差異に注意。
- news_nlp と regime_detector はそれぞれ独立した OpenAI 呼び出しラッパーを持つ（モジュール結合を避けるための設計）。テスト時は各モジュールの内部 _call_openai_api をモックする想定。
- .env のパースは多くのケースに対応するが、極端なフォーマット等は未カバーの可能性がある。
- calendar_update_job は J-Quants クライアントの実装（jq.fetch_market_calendar / jq.save_market_calendar）に依存。API のエラーはログ出力された上で 0 を返す設計。
- 一部の関数はデータ不足時に None を返す仕様（ファクター系）。呼び出し側で None の扱いに注意すること。
- デフォルトの DB パスは DUCKDB_PATH="data/kabusys.duckdb"、SQLITE_PATH="data/monitoring.db"。必要に応じて環境変数で上書き可能。

### Migration / Usage notes
- 必須環境変数（主要なものの例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI を利用する関数を実行する際は OPENAI_API_KEY を設定するか、api_key 引数を明示的に渡すこと。
- ログレベルや環境判定は KABUSYS_ENV / LOG_LEVEL 環境変数で制御（値のバリデーションあり）。

---

この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートや運用方針と差異がある場合は適宜調整してください。