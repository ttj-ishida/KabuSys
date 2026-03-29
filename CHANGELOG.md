# CHANGELOG

すべての変更は Keep a Changelog の形式に従い記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

なし

## [0.1.0] - 2026-03-29

初回公開リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。主な追加点・設計方針は以下のとおりです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ（__version__ = 0.1.0）
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で公開

- 設定 / 環境変数管理
  - 環境変数自動読み込み機能を実装（プロジェクトルートの .env / .env.local を優先読み込み）
  - .env パーサーは以下に対応:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式のサポート
    - 単一・二重クォートのエスケープ処理
    - クォートなしの場合のインラインコメント処理（直前が空白/タブの # をコメントと判定）
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスを提供（必須環境変数の明示的チェック、デフォルト値、Path 型返却など）
    - 必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト: KABUS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV
    - 値検証: KABUSYS_ENV は development/paper_trading/live のみ、LOG_LEVEL は標準ログレベルのみ許容

- AI / 自然言語処理
  - ニュースNLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini) に JSON Mode で送信
    - バッチサイズ、記事数・文字数のトリム上限を設定 (_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)
    - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実行
    - レスポンス検証 (results 配列、code/score、スコア数値化、既知コードのみ採用)
    - ai_scores テーブルへ冪等的に保存（該当コードのみ DELETE → INSERT）
    - 時間ウィンドウ計算ユーティリティ calc_news_window を提供（JST 基準の前日 15:00〜当日 08:30）
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成
    - OpenAI を利用したマクロセンチメント評価（gpt-4o-mini、JSON 出力を期待）
    - API 呼び出しでのリトライ / フェイルセーフ: API 失敗時は macro_sentiment = 0.0 として継続
    - DuckDB を用いた ma200_ratio 計算、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - マクロキーワードリストと最大取得数を定義し、raw_news からタイトルを抽出して評価

- データプラットフォーム（DuckDB ベース）
  - calendar_management モジュール
    - JPX マーケットカレンダー管理、営業日判定ユーティリティを提供
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装
    - market_calendar が未取得の際は曜日ベース（週末を休場）でフォールバック
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存、バックフィルと健全性チェックを実装
  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult データクラスを公開（取得件数、保存件数、品質チェック結果、エラーなどを収集）
    - 差分取得、バックフィル、品質チェックの設計を反映したユーティリティ群
    - jquants_client と quality モジュールとの連携を想定
  - etl モジュールは ETLResult を再エクスポート

- リサーチ / ファクター
  - kabusys.research パッケージを提供（ファクター計算・分析ツール）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離を計算（prices_daily 使用）
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率などを計算
    - calc_value: raw_financials から PER / ROE を計算（price 組合せ）
    - 計算は DuckDB SQL とウィンドウ関数を活用し、データ不足時は None を返す
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンをまとめて取得
    - calc_ic: スピアマンのランク相関（IC）を実装（最小有効レコード数チェック）
    - rank: 同順位は平均ランクにするランク関数（浮動小数丸めで ties の安定化）
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーや他の機微情報は Settings 経由で環境変数として取得する設計。ログ出力でのキーの直接出力を避けることを想定。

### 設計上の注意点 / 実装上の配慮
- ルックアヘッドバイアス対策: ほとんどのモジュール（news/regime/research）は datetime.today()/date.today() を直接参照せず、明示的な target_date 引数を受け取る設計。
- DuckDB 互換性のための実装配慮:
  - executemany に空リストを渡さないガード（DuckDB 0.10 の制約回避）
  - 日付型取り扱いのユーティリティ (_to_date)
- DB 操作は冪等性を重視（DELETE → INSERT、ON CONFLICT など）し、トランザクションとロールバック処理を行う。
- OpenAI 連携は JSON Mode を想定。レスポンスのパースやバリデーションで不正な応答を拾わないフォールバックがある。
- LLM 呼び出しはモジュール毎にプライベート関数を別実装し、モジュール間の結合を低く保つ。

---

注記:
- 本 CHANGELOG はソースコードの内容から推測して作成したもので、実際のリリースノートと差異がある場合があります。必要に応じて運用・公開方針に合わせて補足してください。