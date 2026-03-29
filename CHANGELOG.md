# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-29

初回リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - モジュール公開: data, strategy, execution, monitoring を __all__ に登録。

- 環境設定
  - 環境変数／.env ファイルの自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を読み込む（CWD に依存しない実装）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export 形式、クォート、エスケープ、インラインコメント等に対応。
    - OS 環境変数を保護するため protected セットを使用した上書き制御を実装。
  - Settings クラスを提供し、アプリ固有の設定値をプロパティ経由で取得:
    - J-Quants / kabu / Slack / DB（DuckDB / SQLite）パス / 環境名（development|paper_trading|live）/ ログレベル等。
    - 必須環境変数未設定時は ValueError を送出する _require を提供。
    - env 値と LOG_LEVEL のバリデーション（有効値チェック）を実装。

- AI（自然言語処理）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを統合して OpenAI Chat API（gpt-4o-mini, JSON mode）でセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST、UTC 変換）を実装（calc_news_window）。
    - API 呼び出しはバッチ（最大 20 銘柄/回）で送信し、429/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ。
    - レスポンスの厳密なバリデーションとクリッピング（±1.0）、JSON 前後ノイズ除去ロジックを実装。
    - DuckDB への冪等書き込み（DELETE → INSERT、executemany の空リスト対策あり）。
    - テスト用に _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
    - 公開 API: score_news(conn, target_date, api_key=None) を提供。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily から ma200_ratio を算出（ルックアヘッド防止: date < target_date を使用）。
    - raw_news からマクロキーワードで記事タイトルを抽出し、OpenAI で macro_sentiment を取得。
    - API エラーやパース失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - 冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時に ROLLBACK）。
    - 公開 API: score_regime(conn, target_date, api_key=None) を提供。

- データ（Data platform）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを利用した営業日判定ロジックを提供:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB にデータがない場合は曜日ベースのフォールバック（週末は非営業日）。
    - 最大探索日数制限を設けて無限ループを防止（_MAX_SEARCH_DAYS）。
    - calendar_update_job により J-Quants から差分取得 → market_calendar へ保存（バックフィル・健全性チェックあり）。
    - jquants_client を介した取得・保存処理と統合。

  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを公開（ETL 結果の集計と to_dict メソッド）。
    - 差分取得、バックフィル、品質チェック連携（quality モジュール想定）に基づく設計。
    - テーブル存在チェック、最大日付取得ユーティリティを実装。
    - id_token 注入やエラー収集のためのデザイン（Fail-Fast 回避）。

- リサーチ（Quant Research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（200 日データ不足時は None）。
    - calc_volatility: 20 日 ATR / ATR% / 20 日平均売買代金 / 出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials から直近財務データを取得して PER / ROE を計算。
    - DuckDB SQL ベースで高速に集計する実装。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を使用）。
    - calc_ic: スピアマン（ランク）相関による IC を計算（3 レコード未満で None を返す）。
    - rank: 値を平均ランクへ変換（同順位は平均ランク、丸め処理で ties 回避）。
    - factor_summary: count/mean/std/min/max/median の基本統計量を計算。
    - pandas 等に依存しない純標準ライブラリ実装。

- その他
  - DuckDB と OpenAI SDK（openai）への依存を前提とした実装。
  - ロギングを広範に利用し、各種フェイルセーフ（警告ログ・情報ログ）を実装。
  - 主要なデザイン方針として「ルックアヘッドバイアスの排除」を徹底（datetime.today() や date.today() に依存しない処理）。

### 変更 (Changed)
- 初版のため該当なし。

### 修正 (Fixed)
- 初版のため該当なし。

### 非推奨 (Deprecated)
- 初版のため該当なし。

### 削除 (Removed)
- 初版のため該当なし。

### セキュリティ (Security)
- OpenAI API キーや各種トークンは環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）で管理すること。設定がない場合、多くの関数は ValueError を送出するかフェイルセーフでスキップする。
- .env の自動読み込み機構はデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

## 既知の制約・注意事項
- DuckDB の executemany に空リストを渡せないバージョンへの互換性対策をコード中に実装している（空チェックを行ってから executemany を呼ぶ）。
- AI レスポンスの形式が不正（JSON パース失敗等）な場合は該当チャンク／銘柄をスキップし、全体処理は継続する設計（部分的なスコア欠落がありうる）。
- 一部関数はデータ不足時に None を返す仕様（例: ma200_dev, atr_20 等）。利用側で None ハンドリングが必要。
- calendar_update_job は jquants_client.fetch_market_calendar / save_market_calendar の例外を捕捉し、問題発生時は 0 を返す。

---

（本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノートでは利用者向けに必要に応じて追加の導入手順、依存バージョン、移行手順、サンプル設定例などを追記してください。）