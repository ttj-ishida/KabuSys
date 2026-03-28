# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従っており、セマンティックバージョニングを使用します。

## [Unreleased]
- 今後の変更予定はありません。

## [0.1.0] - 2026-03-28
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - パッケージ公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定 / 設定読み込み (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動で読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込みの無効化対応。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
  - .env の読み込み時に既存 OS 環境変数を保護する protected 機能を実装（.env と .env.local の優先度制御）。
  - 必須環境変数取得用の _require 関数と Settings クラスを提供。
  - 各種設定プロパティを実装（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV、LOG_LEVEL 等）。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値のチェック）を追加。
  - 環境判定ユーティリティ（is_live / is_paper / is_dev）を追加。

- AI モジュール (kabusys.ai)
  - ニュース NLP モジュール（news_nlp）を追加:
    - raw_news / news_symbols から指定ウィンドウ（前日15:00 JST〜当日08:30 JST）に該当する記事を銘柄別に集約。
    - OpenAI（gpt-4o-mini）へのバッチ送信（最大20銘柄/チャンク）で銘柄別センチメントを取得。
    - JSON Mode レスポンスのバリデーション、スコアの ±1.0 クリップ。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフのリトライを実装。
    - DuckDB への書き込みは、部分失敗時に他銘柄の既存スコアを保護するため、対象コードのみ DELETE → INSERT で置換する冪等処理を実装。
    - テストしやすいよう、OpenAI 呼び出し部分は差し替え可能に実装（内部関数名を想定した patch が可能）。
    - 設計上、datetime.today()/date.today() を参照せず、ルックアヘッドバイアスを避ける。
  - 市場レジーム判定モジュール（regime_detector）を追加:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とニュース由来の LLM マクロセンチメント（重み30%）を合成して、日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp.calc_news_window を用いてウィンドウを計算しフィルタ。
    - OpenAI へは gpt-4o-mini を使用、JSON 出力を期待してパース。
    - API エラーに対するリトライ（429・ネットワーク・タイムアウト・5xx）や例外時のフェイルセーフ（macro_sentiment=0.0）を実装。
    - レジーム算出値の閾値とスコア合成ロジックを実装し、market_regime テーブルへ BEGIN/DELETE/INSERT/COMMIT による冪等書き込みを行う。
    - 同様にルックアヘッドバイアス対策が施されている。

- データ基盤 (kabusys.data)
  - ETL パイプライン（pipeline）と ETL 結果型（ETLResult）を実装。ETLResult は品質問題やエラーメッセージを集約して辞書化可能。
  - マーケットカレンダー管理（calendar_management）を追加:
    - market_calendar テーブルの存在判定、営業日判定ロジック（is_trading_day/is_sq_day/next_trading_day/prev_trading_day/get_trading_days）を提供。
    - DB データがない場合の曜日ベースのフォールバック処理（週末判定）を実装。
    - calendar_update_job を定義し、J-Quants API から差分取得→保存（バックフィル、健全性チェック含む）を行うバッチジョブを実装。
    - 最大探索日数やバックフィル日数などの安全パラメータを導入して無限ループや異常値対策を実装。
  - jquants_client 経由のフェッチ／保存操作を想定した実装で、外部 API 呼び出し箇所を抽象化（jq.fetch_market_calendar / jq.save_market_calendar 等を利用）。

- リサーチ / ファクター分析 (kabusys.research)
  - factor_research モジュールを追加:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR、相対ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）ファクター計算を実装。
    - DuckDB のウィンドウ関数を活用し、営業日ベースの窓処理や欠損データへのフォールバックを考慮。
    - 出力は (date, code) をキーにした辞書リスト。
  - feature_exploration モジュールを追加:
    - 将来リターン計算（horizons パラメータ対応、デフォルト [1,5,21]）、IC（Spearman ランク相関）計算、ランク変換、ファクター統計サマリーを実装。
    - horizons のバリデーション、欠損値・有限値チェック、最小サンプル数チェック（IC は有効レコード < 3 の場合 None）を実装。
    - pandas 等の外部依存を使わず標準ライブラリで実装。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### セキュリティ (Security)
- 環境変数（OpenAI API キー等）を未設定のまま処理が進まないよう ValueError を投げる箇所を設け、誤った公開や実行を防止する設計を採用。
- .env の読み込みでは既存 OS 環境変数を上書きしないデフォルト動作とし、.env.local による上書きを許容するが OS 環境変数は protected として保護。

### 注意事項 / 設計上のポイント
- ルックアヘッドバイアス回避のため、日付ベースの処理はすべて外部から与えられる target_date を使用し、内部で date.today()/datetime.today() を直接参照しない設計になっています。
- OpenAI への呼び出しは JSON Mode を想定し、レスポンスのバリデーションや冗長文字列混入の復元処理を行っています。API 呼び出しは retry/backoff を行い、最終的にフェイルセーフ（スコア = 0 など）で続行する方針です。
- DuckDB への書き込みは冪等性を重視（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK 管理）し、部分失敗時に既存データを不必要に消さないようにしています。また、DuckDB の executemany の仕様に合わせて空パラメータのチェックを挟んでいます。
- テストしやすさを考慮し、OpenAI 呼び出し部分はモジュール内のプライベート関数を patch して差し替え可能な実装になっています。

---

今後のリリースでは、外部接続クライアントの抽象化拡張、strategy / execution / monitoring モジュールの具体的実装、テストカバレッジの強化、パフォーマンス最適化等を予定しています。