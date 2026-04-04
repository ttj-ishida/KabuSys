# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、Semantic Versioning に従います。

## [Unreleased]

## [0.1.0] - 2026-04-04
初回公開リリース。

注: 以下はソースコードから推測して作成した機能一覧と設計上の注意点です。

### 追加
- パッケージ基盤
  - kabusys パッケージを追加。バージョン: 0.1.0。
  - パッケージの公開名前空間: data, strategy, execution, monitoring を __all__ で定義。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動読み込みする仕組みを実装。
  - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを実装:
    - コメント行対応、export KEY=val 形式対応。
    - シングル/ダブルクォートのエスケープ処理、インラインコメントの取り扱いを実装。
  - Settings クラスを提供（settings インスタンスをエクスポート）:
    - J-Quants / kabuステーション / LINE API / DB パス / 監視閾値等の設定プロパティを定義。
    - 必須値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は _require で検証し未設定時は ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値セットを定義）。
    - ユーティリティプロパティ: is_live / is_paper / is_dev。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を元に銘柄ごとのニュース集合を集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ計算（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）を提供（calc_news_window）。
    - API 呼び出しのリトライ／エクスポネンシャルバックオフ（429・ネットワーク断・タイムアウト・5xx に対応）。
    - レスポンスの堅牢なバリデーション・JSON 復元ロジック（前後テキストを含む場合に {} を抽出）を実装。
    - スコアは ±1.0 にクリップし、取得成功銘柄のみ ai_scores テーブルへ冪等的に書き込み（DELETE→INSERT の方式、部分失敗時の保護）。
    - テスト容易性: _call_openai_api を patch して差し替え可能。
    - バッチサイズ、記事数上限、文字数上限などの定数を設定可能。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はキーワードマッチ（複数キーワード定義）で行う。
    - OpenAI API の呼び出しに対して再試行ロジックを実装（RateLimit / 接続エラー / タイムアウト / 5xx を考慮）。
    - API 失敗時や記事なしの場合はフォールバック（macro_sentiment=0.0）で継続するフェイルセーフ設計。
    - レジーム結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）し、書き込み失敗時はROLLBACK を試み例外を伝播。
    - 設計上、datetime.today()/date.today() を参照せず、target_date ベースでルックアヘッドバイアスを防止。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダー（market_calendar テーブル）を使った営業日判定ロジックを実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days。
    - DB 登録済みデータを優先し、未登録日は曜日ベースでフォールバックする一貫性設計。
    - 夜間バッチ job (calendar_update_job) を実装し、J-Quants クライアントから差分取得→冪等保存（バックフィル・健全性チェックあり）。
    - 最大探索範囲やバックフィル日数等の安全制約を実装。

  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分取得・保存・品質チェック（quality モジュール連携）を想定した設計。
    - データ保存は idempotent（ON CONFLICT 等）を前提とし、バックフィルで後出し修正を吸収。
    - ETLResult は品質検出やエラー集約情報を含み、辞書化メソッドを提供。

- 研究（Research）ユーティリティ (kabusys.research)
  - factor_research モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、ma200_dev を計算（データ不足時は None）。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率などを計算（データ不足時は None）。
    - calc_value: raw_financials から EPS/ROE を組み合わせて PER/ROE を算出（EPS が 0/欠損なら None）。
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 将来リターンを複数ホライズンで計算（範囲検証あり）。
    - calc_ic: スピアマンランク相関（IC）を計算（有効レコード < 3 は None）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
    - rank: 同順位は平均ランクを返すランク変換ユーティリティ（丸めにより ties を安定化）。
  - research パッケージ __init__ で主要関数を再エクスポート。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 削除
- （初回リリースのため該当なし）

### 既知の設計上の注意点 / 制限
- OpenAI への API キーは api_key 引数で注入可能（テスト用）だが、デフォルトは環境変数 OPENAI_API_KEY を使用する。未設定時は ValueError を送出する。
- DuckDB を前提としており、executemany に空リストを渡せないバージョンへの互換性考慮がコード内にある（空リスト時はスキップ）。
- 時刻処理はすべて naive datetime / date で統一している（タイムゾーン侵入を防ぐ設計）。ニュースウィンドウは JST→UTC 変換で DB 比較する実装。
- いくつかの内部 helper（_call_openai_api 等）はテスト用に差し替え可能に実装されている。
- .env パーサは複数のケースに対応しているが、極端に複雑な .env 構文は保証されない可能性あり。

### セキュリティ
- 環境変数ロード時に既存 OS 環境を意図せず上書きしない保護機能を実装（読み込み時に protected set を使用）。
- ログ出力において秘密情報が直接出力されないよう配慮している（ただしアプリ運用時はログ設定に注意）。

---

（将来のリリースでは追加機能・バグ修正・API 互換性変更等をここに追記してください。）