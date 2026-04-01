# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングに基づいて記載します。

## [0.1.0] - 2026-04-01

初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。以下の主要コンポーネントと機能を含みます。

### 追加 (Added)
- パッケージ初期化
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ に data / strategy / execution / monitoring を公開

- 設定・環境変数管理 (src/kabusys/config.py)
  - Settings クラスを提供し、環境変数から各種設定を取得するプロパティを実装
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須値取得
    - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL（DEBUG/INFO/...）の検証
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）、監視設定（PID_FILE_PATH, CPU/MEM/DISK 閾値）などを取得
    - is_live / is_paper / is_dev ヘルパープロパティ
  - .env 自動ロード:
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - .env.local は .env を上書き（OS 環境変数は保護）
  - .env パーサー:
    - export KEY=val 形式、シングル/ダブルクォート、エスケープ、行末コメントの扱いに対応
    - 無効行（コメント行や不正な行）をスキップ

- ニュース NLP（センチメント） (src/kabusys/ai/news_nlp.py)
  - raw_news / news_symbols を元に OpenAI（gpt-4o-mini, JSON Mode）を用いて銘柄別センチメントを算出
  - 処理フロー:
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換）で記事を収集
    - 銘柄ごとに記事を集約し（最大記事数・最大文字数でトリム）、銘柄チャンク（最大 20）で API 送信
    - API の 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ
    - レスポンスを厳密にバリデートし、スコアを ±1.0 にクリップ
    - 成功した銘柄のみ ai_scores テーブルへ置換（DELETE→INSERT）し、部分失敗時に既存スコアを保護
  - テスト容易性:
    - OpenAI 呼び出しを抽象化して単体テストで差し替え可能

- 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の 200日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を組み合わせて
    日次で市場レジーム（bull / neutral / bear）を算出して market_regime テーブルへ冪等書き込み
  - 特徴:
    - ma200_ratio 計算は target_date 未満のデータのみを使用（ルックアヘッド防止）
    - マクロセンチメントはニュースタイトルを抽出して LLM へ投げ、JSON で受け取りパース
    - API エラー時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）
    - 冪等な DB 操作（BEGIN / DELETE / INSERT / COMMIT）を実装
  - パラメータ:
    - デフォルトモデル: gpt-4o-mini
    - リトライ回数、バックオフなどの制御を実装

- Research（ファクター計算・特徴量探索） (src/kabusys/research/)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算
    - calc_value: PER（株価/EPS）・ROE を raw_financials と prices_daily から計算
    - calc_volatility: 20日 ATR（平均 true range）、相対 ATR、20日平均売買代金、出来高比率を計算
    - 設計方針: DuckDB に対する SQL ベース実装、外部 API へはアクセスしない
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）で将来リターンを計算
    - calc_ic: スピアマンランク相関（IC）を計算。データ不足時は None を返す
    - rank: 平均ランク処理（同順位は平均ランク）
    - factor_summary: 基本統計（count/mean/std/min/max/median）を算出
  - research パッケージ初期化で主要関数を再エクスポート

- データプラットフォーム（Data） (src/kabusys/data/)
  - calendar_management:
    - JPX マーケットカレンダーを扱うユーティリティ群
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - market_calendar がない場合は曜日ベース（土日非営業）でフォールバック
    - カレンダー取得ジョブ calendar_update_job を実装（J-Quants から差分取得 → 保存）
    - 各種安全チェック（最大探索日数、バックフィル、健全性チェック）を実装
  - pipeline / etl:
    - ETLResult データクラス（target_date・取得/保存件数・品質問題・エラー一覧など）
    - ETL パイプラインの設計（差分更新、バックフィル、品質チェック連携、idempotent 保存）
    - data.etl で ETLResult を再エクスポート

- 例外処理・ロギング強化
  - 各モジュールで API エラーや JSON パース失敗時に WARN/INFO/ERROR ログを出力し、フェイルセーフ挙動を採用
  - DB 書き込みでの例外時にロールバックを試みる実装

### 変更 (Changed)
- （初回リリースのため履歴なし）

### 修正 (Fixed)
- （初回リリースのため履歴なし）

### 既知の制約・挙動（注意）
- OpenAI API キーは api_key 引数で注入可能（テスト用）。未指定時は環境変数 OPENAI_API_KEY を参照する。未設定の場合は ValueError を送出する。
- News/Regime の LLM 呼び出しは gpt-4o-mini および JSON Mode を前提にしている（将来のモデル変更は実装修正が必要）。
- DuckDB executemany に空リストを渡すとエラーとなるため、空でないことを事前にチェックしている（互換性対応）。
- calendar / ETL の外部 API 呼び出し（J-Quants）部分は jquants_client 経由で抽象化されているため、実運用では該当クライアント実装が必要。
- datetime.today()/date.today() を参照せず、関数の引数として target_date を必須としている箇所が多く、ルックアヘッドバイアス（データ漏洩）を防止する設計。

### 将来の改善案（非必須）
- strategy / execution / monitoring の具体的な実装（現在パッケージ公開名のみ設定）
- OpenAI レスポンスのより堅牢な検証・メトリクス収集
- ETL のより細かな品質チェックルール追加（quality モジュール拡張）
- 単体テスト・統合テストの追加（OpenAI・J-Quants 呼び出しのモック整備）

---

記載はソースコードからの推測に基づきます。実際のリリースノートとして使用する場合は、変更点の正確性をコードベースやコミット履歴と照合してください。