# CHANGELOG

すべての重要な変更を記録します。本ファイルは Keep a Changelog のフォーマットに準拠します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-27

初回公開リリース。本リポジトリの基盤機能として、日本株自動売買・データ基盤・リサーチ・AI スコアリングの主要コンポーネントを実装しました。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期版を公開。バージョンは 0.1.0。
  - top-level の公開モジュール: data, strategy, execution, monitoring を __all__ で定義。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出は .git または pyproject.toml を基準に行い、CWD に依存しない方式。
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
    - override と protected キーの概念で OS 環境変数の保護に対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境・ログレベル等のプロパティを用意。
    - 必須値未設定時は明確なエラーメッセージ（ValueError）を送出。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値セット）を実装。
    - duckdb/sqlite のデフォルトパスを設定（expanduser 対応）。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ保存する処理を実装。
    - 処理内容:
      - JST ベースのニュースウィンドウ計算（前日15:00〜当日08:30、内部は UTC naive で扱う）。
      - 銘柄ごとに記事結合・文字数トリム（最大記事数・最大文字数制限）。
      - バッチ送信（1 API 呼び出しあたり最大 20 銘柄）。
      - JSON Mode レスポンスのバリデーションと±1.0でのクリップ。
      - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライとフォールバック動作。
      - DuckDB に対する冪等書き込み（DELETE→INSERT、部分失敗時に既存データを保護）。
    - テスト容易性: OpenAI 呼び出しを差し替え可能（内部 _call_openai_api を patch 可能）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を計算。
    - 処理フロー:
      - prices_daily から ma200 比を算出（ルックアヘッド防止のため target_date 未満のデータのみを利用）。
      - raw_news からマクロキーワードでフィルタしたタイトルを取得し、OpenAI で macro_sentiment を評価（記事がなければ LLM コールを行わない）。
      - API 障害時は macro_sentiment=0.0 でフォールバック。
      - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - レート制限・ネットワーク障害等に対するリトライ実装とログ出力。

- データ（Data）モジュール (src/kabusys/data)
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job により J-Quants からの差分取得、バックフィル、健全性チェック、保存処理を実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを導入し、ETL 実行の各種カウント・品質問題・エラー情報を格納可能に。
    - 差分取得、backfill、品質チェック（quality モジュール使用）を想定したユーティリティ群（テーブル存在チェック、最大日付取得など）を実装。
  - etl で使用する型の公開（src/kabusys/data/etl.py: ETLResult を再エクスポート）。

- Research（src/kabusys/research）
  - factor_research.py
    - モメンタム（1M/3M/6M のリターン、ma200 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER、ROE）などのファクター計算関数を実装。
    - DuckDB の SQL を活用し、prices_daily / raw_financials のみ参照する設計。
    - データ不足時の None 扱い、結果は (date, code) ベースの dict リストで返却。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク関数（rank）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - research パッケージ __init__ で主要関数を再エクスポート。

### 変更 (Changed)
- 設計方針の明文化
  - AI / リサーチ系モジュールにおいて「ルックアヘッドバイアス防止」の設計方針を徹底（datetime.today() の直接参照を避け、全て target_date ベースで処理）。
  - API 呼び出しや DB 書き込みはフェイルセーフ（API 失敗時はスコアをスキップまたはゼロにして処理継続）を採用。

### 修正 (Fixed)
- .env パーサの堅牢化
  - クォート内のバックスラッシュエスケープや export キーワード、インラインコメント扱いを正しく処理する実装により、既知のパース不整合を回避。
- DuckDB 対応
  - executemany に空リストを渡すとエラーとなる制約に対応するガードを追加（空のときは実行しない）。
  - DuckDB からの日付型変換を安全に行うユーティリティを追加。

### 既知の問題 / 注意点 (Known issues / Notes)
- OpenAI API の呼び出し部は外部サービスに依存するため、実行には OPENAI_API_KEY（または各関数へ api_key 引数）を設定する必要があります。未設定時は ValueError を送出します。
- 一部の実装は jquants_client や quality モジュールへ依存します。これらの外部クライアントの実装状況により動作が変わります。
- calendar_update_job 等は実行環境の時計（日付）に依存する箇所があるため、テスト時は自動.envロードの無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD）や API 呼び出しのモック化を推奨します。

### 互換性 (Compatibility)
- 初回リリースのため後方互換性に関する破壊的変更はありません。

---

今後のリリースでは、strategy / execution / monitoring の実働ロジックや単体テスト、CI 設定、ドキュメント（Usage / API 仕様）の充実化を予定しています。