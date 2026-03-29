CHANGELOG
=========

すべての重要な変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

フォーマット:
- 変更はセマンティックに分類（Added / Changed / Fixed / Removed / Security）しています。
- 各バージョンに対して概要と実装上の重要な設計・挙動上の注意点を記載しています。

Unreleased
----------
（今後の変更をここに記載してください）

[0.1.0] - 2026-03-29
-------------------

初回リリース。日本株自動売買・リサーチ・データ基盤のためのコア機能を実装しました。
主な追加点と設計方針、運用上の注意を以下にまとめます。

Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - サブパッケージの公開: data, research, ai, monitoring, strategy, execution 等を想定する公開 API を整備。

- 環境設定 / 設定管理
  - kabusys.config モジュールを追加。
    - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を探索）。
    - export KEY=val 形式やクォート付き値、インラインコメントの扱い、エスケープ処理に対応した .env パーサを実装。
    - OS 環境変数を保護する protected オプション、上書き制御（override）をサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - 必須設定取得用のヘルパー _require と Settings クラス（J-Quants / kabu / Slack / DB パス / 環境種別 / ログレベル等）。
    - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値チェック）実装。

- AI（NLP）関連
  - kabusys.ai.news_nlp
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄毎のセンチメント ai_score を計算、ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を提供。
    - バッチサイズ、記事数・文字数の上限、JSON Mode レスポンスのバリデーション、±1.0 でのクリップ、部分失敗時の部分更新（DELETE→INSERT）といった仕様を採用。
    - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装。失敗フェイルセーフとしてスキップ継続。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - kabusys.ai.regime_detector
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、ニュースセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定、market_regime テーブルへ冪等書き込み。
    - マクロキーワードで raw_news をフィルタし、最大20記事を LLM に提示して macro_sentiment を算出。
    - APIエラー時は macro_sentiment=0.0 とするフォールバックと複数回リトライ実装。
    - ルックアヘッドバイアス防止のため date の扱いを厳格化（内部で datetime.today() を参照しない等）。

- リサーチ / ファクター計算
  - kabusys.research パッケージの追加。
  - factor_research モジュール
    - モメンタム（1M/3M/6M, MA200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比）、バリュー（PER/ROE）を DuckDB 上で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を用いた実装、データ不足時は None を返す仕様。
  - feature_exploration モジュール
    - 将来リターン算出（calc_forward_returns）、IC（Information Coefficient：Spearman ρ）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。
    - pandas 等外部依存を排し標準ライブラリ＋duckdb のみで実装。

- データ基盤（Data）
  - kabusys.data パッケージ
  - calendar_management
    - market_calendar テーブルを用いた営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、calendar_update_job（J-Quants から差分取得して idempotent に保存）を実装。
    - market_calendar の未取得時は曜日フォールバック（土日除外）。
    - バックフィル、健全性チェック、最大探索範囲制限（_MAX_SEARCH_DAYS）などの安全策を導入。
  - pipeline / etl
    - ETLResult データクラスを公開し、ETL 実行結果（取得数・保存数・品質問題・エラーの一覧）を管理する設計を導入。
    - 差分取得、バックフィル、品質チェック（quality モジュール想定）を行う方向性を示すパイプライン基盤。

- DB / ライブラリ
  - DuckDB を主要なローカル DB として採用し、各モジュールで DuckDB 接続を引数に取る設計。
  - OpenAI SDK（OpenAI クライアント）を使用するインタフェースを実装（テスト置換を容易にする設計）。

Fixed / Safeguards / Behavioral details
- ルックアヘッドバイアス対策
  - AI・リサーチ機能の全てで日時の扱いを厳密化（内部で datetime.today() / date.today() を参照しない、クエリは target_date 未満や半開区間を使用）。
- 冪等性と部分成功保護
  - market_regime / ai_scores 等への書き込みは DELETE→INSERT または個別 DELETE executemany により、部分失敗時に既存データの保護を考慮。
- フォールバック動作
  - OpenAI API の失敗（429/ネットワーク/タイムアウト/5xx）はリトライ後、全失敗時は macro_sentiment や該当チャンクのスコアを 0.0（またはスキップ）で継続処理し、例外を投げない設計（システム停止回避）。
- .env パーサの堅牢化
  - クォート内のバックスラッシュエスケープ、クォートなしのインラインコメント判定（'#' の直前が空白/タブ時のみコメント）に対応。
  - 読み込み失敗時には警告を出し処理を継続。
- テスト性
  - OpenAI 呼び出しを行う内部関数を個別に patch できるように実装（unittest.mock.patch による差し替えを想定）。
- 入力検証
  - Settings の env / log_level の値検証（不正な値は ValueError）。
  - score_news / score_regime で API キー未設定時は ValueError を送出。

Security
- 機密情報の明示的要求
  - 以下の環境変数が本モジュールの各機能で必須（未設定時は ValueError を発生させる箇所あり）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
  - .env にこれらを保存する場合は運用上の秘匿管理に注意してください。

Notes / Migration / 運用上の注意
- 初期リリースのため、実運用にあたっては以下に注意してください:
  - OpenAI 利用部分は API レート・課金に依存します。テスト時は _call_openai_api をモックすることを推奨します。
  - .env 自動読み込みはプロジェクトルートの検出に依存します（.git または pyproject.toml が必要）。CI・テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化してください。
  - DuckDB のバージョン差異（executemany の空リスト挙動等）を考慮した実装上の処理が含まれます。DuckDB バージョンとの互換性確認を行ってください。
  - ETL / calendar_update_job は J-Quants クライアント実装（jquants_client）に依存します。API の変更があった場合は保存ロジック（save_*）の互換性に注意が必要です。

Known issues / TODO
- 一部の機能（PBR・配当利回りなどのバリューファクター）は未実装で将来追加予定。
- news_nlp のレスポンス復元ロジックは頑健化済みだが、LLM 側のフォーマット逸脱に対する追加検査は継続的に必要。
- 外部環境（J-Quants / kabu / OpenAI）の API 変更時にハンドリングが必要になる可能性あり。

履歴について
- 本CHANGELOGはコードベースの実装内容から推測して作成した初期履歴です。実際のリリース履歴や運用での変更は別途このファイルを更新してください。