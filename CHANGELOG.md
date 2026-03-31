# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従って記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-31

初回公開リリース。本リリースでは、データ収集・ETL・カレンダー管理・リサーチ・AI ベースのニュースセンチメント評価・市場レジーム判定など、日本株自動売買システムの基盤機能を実装しました。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（バージョン 0.1.0、公開 API の __all__ 指定）。

- 設定管理
  - 環境変数/ .env ファイル自動読み込み機能（優先順位: OS 環境 > .env.local > .env）。
  - .env パーサ実装（コメント・export プレフィックス・クォート・バックスラッシュエスケープ対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応（テスト用）。
  - Settings クラスを提供し、必須環境変数の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）、パス（DUCKDB_PATH, SQLITE_PATH）、環境種別・ログレベルの検証を実装。

- データ基盤（data）
  - calendar_management: JPX カレンダー管理と営業日判定ユーティリティ
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - calendar_update_job：J-Quants から差分取得して market_calendar を冪等更新
    - DB 未取得時の曜日ベースフォールバック、最大探索日数制限、バックフィル/健全性チェックを実装
  - pipeline / etl:
    - ETLResult データクラス（ETL の取得件数・保存件数・品質問題・エラー集約）
    - ETL 用ユーティリティ（テーブル存在チェック、最大日付取得など）
    - etl モジュール経由で ETLResult を再エクスポート

- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - ニュース記事を銘柄ごとに集約し OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（ai_score）を ai_scores テーブルへ書き込み
    - 前日 15:00 JST ～ 当日 08:30 JST のウィンドウ計算（UTC 換算）と最大記事数/文字数トリム、バッチサイズ制御
    - JSON Mode レスポンスの検証・復元処理、数値変換・±1.0 クリップ、部分書き換え（DELETE → INSERT）による冪等性
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、失敗時はフェイルセーフでスキップ
  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定
    - prices_daily / raw_news を参照、OpenAI 呼び出しは独立実装（モジュール結合を避ける）
    - LLM 呼び出しのリトライ・フォールバック（API 失敗時 macro_sentiment=0.0）
    - market_regime への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）、エラー時の ROLLBACK 保護

- リサーチモジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン・200 日 MA 乖離（データ不足時は None）
    - calc_volatility: 20 日 ATR・相対 ATR・20 日平均売買代金・出来高比率
    - calc_value: PER（EPSが0/欠損の時は None）・ROE（raw_financials を使用）
    - DuckDB の SQL とウィンドウ関数を活用した実装
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（存在しない場合は None）
    - calc_ic: スペアマンのランク相関（IC）計算
    - rank: 同順位は平均ランク（丸めにより ties の安定化）
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出
  - すべての関数は pandas 等の外部依存を持たず、prices_daily / raw_financials 等の DB テーブルのみを参照

- その他
  - OpenAI Python SDK（chat completions）を利用するラッパーを複数モジュールで独自実装（テスト差し替え容易）。
  - DuckDB を想定した SQL 実装と互換性考慮（executemany の空リスト回避等）。
  - ロギング出力（情報・警告）を多数の箇所で実装し、フォールバックやエラー発生時の状況を記録。

### 変更 (Changed)
- 該当なし（初回リリースのため新規実装のみ）。

### 修正 (Fixed)
- 該当なし。

### 削除 (Removed)
- 該当なし。

### 非推奨 (Deprecated)
- 該当なし。

### セキュリティ (Security)
- 該当なし。

注記:
- 多くの箇所で「ルックアヘッドバイアス防止」の設計方針が採用されています（datetime.today()/date.today() を直接参照しない、クエリに date < target_date を使用する等）。
- OpenAI API キー未設定時は明示的に ValueError を発生させる箇所があり、運用時の設定漏れを検出しやすくしています。
- DB 書き込みは可能な限り冪等化・部分更新を行い、部分失敗時に既存データを不必要に破壊しない考慮がされています。

--- 
（以降のリリースでは各モジュールの詳細な変更点・互換性情報を追記します）