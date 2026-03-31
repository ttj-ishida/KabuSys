Keep a Changelog
=================

すべての notable な変更はこのファイルに記録します。
このプロジェクトは https://keepachangelog.com/ja/ に準拠しています。

Unreleased
----------

（今後の変更用）

0.1.0 - 2026-03-31
-----------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報:
    - __version__ = "0.1.0"
    - 主要サブパッケージ公開: data, research, ai など（パッケージ構成のエントリを含む）。
- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定値を自動読み込みする機能を実装。
  - プロジェクトルート探索: __file__ を起点に .git または pyproject.toml を探索してルートを特定（CWD非依存）。
  - .env パーサ: export 付き、クォートあり/なし、エスケープ、コメント処理に対応する堅牢なパーサを実装。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードをスキップ可能。
  - Settings クラスを提供し、各種必須環境変数の取得とバリデーションを行う:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などを必須として取得。
    - DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH 等のデフォルトパスを提供。
    - CPU / Memory / Disk の閾値、KABUSYS_ENV (development/paper_trading/live)、LOG_LEVEL の検証ロジックを実装。
- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大20銘柄／チャンク）、記事・文字数トリム、リトライ（429/ネットワーク/タイムアウト/5xx）を実装。
    - レスポンスの厳格なバリデーションとスコアのクリップ処理を実装。
    - 書き込みは部分置換（DELETE → INSERT）で行い、部分失敗時に既存データを保護。
    - テスト容易性のため API 呼び出し部分（_call_openai_api）をモック可能に設計。
    - タイムウィンドウ計算（JST基準）を calc_news_window() で提供し、look-ahead バイアスを避ける設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）に対する200日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出しは gpt-4o-mini を使用、エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ設計。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行。
    - ルックアヘッドバイアス防止のため内部で date.today()/datetime.today() を参照しない実装。
- データプラットフォーム / ETL（kabusys.data）
  - ETL パイプラインの結果を表現する ETLResult データクラスを公開（kabusys.data.etl 経由で再エクスポート）。
  - pipeline モジュール（kabusys.data.pipeline）
    - 差分更新、バックフィル、品質チェック連携（quality モジュール想定）に基づく ETL の設計概要とユーティリティ関数を実装。
    - DuckDB を用いたテーブル存在確認、最大日付取得等のユーティリティを提供。
    - ETL 実行のメタ情報（取得件数、保存件数、品質問題、エラー）を収集して返却。
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - market_calendar を元に営業日判定、前後営業日探索、期間内営業日取得、SQ日判定を実装。
  - DB 登録がない場合は曜日ベースのフォールバック（土日非営業）。
  - calendar_update_job により J-Quants からの差分取得・冪等保存（バックフィル・健全性チェック含む）を実装（jquants_client 経由）。
  - 最大探索範囲やバックフィル日数等の安全パラメータを設計に組み込み。
- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離の算出。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率等の算出。
    - calc_value: raw_financials から最新財務を取得して PER/ROE を算出（EPS 0/欠損は None）。
    - DuckDB 上で SQL を組み合わせて高効率に計算。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。horizons の検証あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装。有効レコード < 3 の場合は None を返す。
    - rank: 平均ランク（同順位は平均ランク）を計算するユーティリティ（浮動小数点丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ機能。
  - research パッケージの一部機能は data.stats の zscore_normalize を re-export。
- 一貫した設計方針・堅牢性
  - ルックアヘッドバイアス防止の徹底（date.today/ datetime.today を直接参照しない）。
  - OpenAI 呼び出しのリトライ（指数バックオフ）、サーバーエラーの扱い、レスポンスパース失敗のフェイルセーフ（多くのケースで 0.0 やスキップで継続）。
  - DuckDB に対する書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。ROLLBACK 失敗時は警告ログ出力を行う。
  - テスト容易性を意識して一部内部 API（_call_openai_api など）をモック可能に設計。
  - 外部依存を最小化（pandas 等に依存せず標準ライブラリ + duckdb + openai SDK を使用する方針が明示）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Known issues / 注意事項
- 一部関数はデータ不足時に None を返す（例: ma200_dev, atr_20 等）。呼び出し側でのハンドリングが必要。
- OpenAI API を利用する機能は api_key が必須。api_key 引数または環境変数 OPENAI_API_KEY を設定しないと ValueError を送出する。
- OpenAI レスポンスのフォールバックは「中立（0.0）」や「スキップ」を選択しており、異常時に例外を上位に伝播しにくい設計になっている（可用性優先）。
- DuckDB の executemany は空リストを受け付けないバージョンへの対応が行われている（空の場合はスキップ）。
- jquants_client / quality モジュールは参照されているが、外部に実装が必要（ETL や calendar_update_job が外部クライアントに依存）。
- OpenAI のモデル指定は gpt-4o-mini。運用時はコスト・利用規約を確認すること。

作者
- kabusys コードベース（初期リリース）