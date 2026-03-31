# Changelog

すべての重要な変更点をこのファイルに記録します。  
このファイルは「Keep a Changelog」フォーマットに準拠し、セマンティックバージョニングを利用します。

--- 

## [0.1.0] - 2026-03-31
初回リリース。プロジェクトのコア機能（データ取得/ETL、マーケットカレンダー、研究用ファクター計算、ニュース/レジームのAI評価、設定管理など）を実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（バージョン: 0.1.0）と主要サブパッケージの公開設定（data, research, ai, など）。
- 環境設定（kabusys.config）
  - .env / .env.local の自動ロード機能を実装。プロジェクトルート（.git または pyproject.toml を探索）を基準に読み込み。
  - .env パーサを実装（コメント行、export 文、シングル/ダブルクォート、エスケープ、インラインコメント処理を考慮）。
  - 環境変数の必須チェック（_require）と Settings クラスを提供。J-Quants / kabu API / Slack / DB パス / ログレベル / 環境種別（development/paper_trading/live）などのプロパティ実装。
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）の導入。
  - 入力値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
- AI 関連（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を利用して銘柄ごとのニューステキストを集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメント評価を行う score_news を実装。
    - タイムウィンドウ（JST: 前日15:00〜当日08:30、内部は UTC naive で扱う）計算ユーティリティ（calc_news_window）。
    - バッチ送信（最大20銘柄／チャンク）、各銘柄のトリム（記事数上限・文字数上限）を実装。
    - 再試行/バックオフ戦略（429/ネットワーク断/タイムアウト/5xx に対して指数バックオフ）、レスポンスの堅牢なバリデーション、スコアの ±1.0 クリップ。
    - DuckDB への冪等的書き込み（DELETE -> INSERT をチャンク単位で実行）、部分失敗時に既存データを保護する戦略。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily から MA200 乖離を計算するロジック、raw_news からマクロキーワード（複数）でフィルタしたタイトル抽出、OpenAI 呼び出しの独立実装、リトライ・フォールバック（API失敗時は macro_sentiment=0.0）のフェイルセーフを実装。
    - 結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）し、例外時の ROLLBACK 処理を考慮。
- データ基盤（kabusys.data）
  - ETL（kabusys.data.pipeline）
    - ETLResult データクラスを公開（取得件数、保存件数、品質チェック結果、エラー一覧などを含む）。
    - 差分取得・バックフィル・品質チェック方針を実装する基盤ロジック（内部ユーティリティ関数としてテーブル存在確認、最大日付取得など）。
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間バッチ更新 job（calendar_update_job: J-Quants から差分取得して market_calendar に冪等保存）を実装。
    - 営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の際の曜日ベースフォールバック、DB 登録優先の一貫した振る舞い、探索範囲制限（_MAX_SEARCH_DAYS）を採用。
  - ETL での J-Quants クライアント（jquants_client 参照）との連携を想定（fetch/save 呼出しをラップ）。
- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ/流動性（20日 ATR、20日平均売買代金、出来高比率）、バリュー（PER, ROE）を計算する calc_momentum / calc_volatility / calc_value を実装。
    - DuckDB を用いた SQL 主導の実装。データ不足時は None を返す動作。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns: 複数ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算（calc_ic: スピアマンランク相関、最低必要レコード数チェック）。
    - ランク変換ユーティリティ（rank: 同順位は平均ランク）。
    - ファクター統計サマリー（factor_summary: count/mean/std/min/max/median 計算）。外部依存せず標準ライブラリのみで実装。
- その他
  - duckdb をデータ処理の主要エンジンとして使用。
  - OpenAI SDK（OpenAI クライアント）を直接利用する呼び出しを実装（テスト用に _call_openai_api を差し替え可能に設計）。
  - ロギングを広範に導入し、重要操作や警告を記録。

### 変更 (Changed)
- 初版につき該当なし。

### 修正 (Fixed)
- 初版につき該当なし。

### セキュリティ (Security)
- 初版につき該当なし。
- 注意: OpenAI API キーや各種シークレットは環境変数（.env）経由で管理する想定。自動 .env ロード時に OS 環境変数を保護する仕組みを導入（.env.local は上書き可だが OS 環境は保護）。

### 既知の制約 / 設計上的注意点
- 全ての関数はルックアヘッドバイアス防止のため date.today()/datetime.today() を内部で直接参照せず、target_date を引数で与える設計。
- OpenAI 呼び出し失敗時はフェイルセーフとして中立値（0.0 等）へフォールバックする箇所があるため、外部可観測の失敗ログを必ず確認すること。
- DuckDB の executemany に空リストを渡せないバージョン（例: 0.10）を考慮した防御的実装が入っている（空の場合は実行をスキップ）。
- market_calendar や raw_* テーブル等の存在を前提にした処理が多い。初回セットアップでスキーマ/テーブルが必要。

---

今後のリリースでは以下が想定されます（例）
- エラーハンドリングの改善とより詳細な監査ログ
- モデル/プロンプトのチューニングや追加評価指標
- ETL スケジューリング・監視周りの強化
- 単体テスト／統合テストの追加と CI 設定

--- 

参照:
- Keep a Changelog: https://keepachangelog.com/en/1.0.0/  
- セマンティックバージョニングに準拠 (https://semver.org/)