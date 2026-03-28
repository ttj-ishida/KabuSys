# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースから機能・設計方針を推測して作成しています。

フォーマット:
- 主要セクション: Added / Changed / Fixed / Security / Removed
- 各項目には影響範囲（モジュール / 関数名）を明記

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システムの基盤機能群を提供します。主な追加点は以下のとおりです。

### Added
- パッケージ公開インターフェース
  - src/kabusys/__init__.py による公開（data, strategy, execution, monitoring）。
  - バージョン: 0.1.0

- 環境設定・自動.env ロード
  - src/kabusys/config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を起点）に基づく .env / .env.local の自動読み込み。
    - 複雑な .env パース実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
    - 環境変数保護（既存 OS 環境変数をプロテクトして .env.local のオーバーライド制御）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - Settings クラスを公開（J-Quants、kabuステーション、Slack、DBPath、環境/ログレベル検証、is_live/is_paper/is_dev）。

- ニュース NLP（AI）機能
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出。
    - バッチ処理（最大20銘柄/chunk）、記事トリミング（最大記事数・最大文字数）。
    - JSON Mode を用いた厳密レスポンス期待とレスポンスの堅牢なバリデーション。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - スコア ±1 にクリップ、取得成功分のみ ai_scores テーブルへ冪等的に書き込み（DELETE→INSERT）。
    - テスト用に OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。
    - calc_news_window 関数で JST のニュースウィンドウ計算（Look-ahead バイアス対策）。

  - src/kabusys/ai/__init__.py で score_news を公開。

- 市場レジーム判定（AI + ETL 指標合成）
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動）の200日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - DuckDB から過去データを取得（ルックアヘッド防止のため target_date 未満のデータのみ使用）。
    - OpenAI 呼び出しは個別実装でテスト時差し替え可能。API失敗時は macro_sentiment=0.0 でフェイルセーフ。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理。

- データ基盤ユーティリティ（ETL・カレンダー）
  - src/kabusys/data/pipeline.py
    - ETL の結果を表す ETLResult dataclass を定義（取得件数、保存件数、品質問題、エラー群、判定ヘルパー）。
    - テーブル存在チェック、最大日付取得などの内部ユーティリティ。
    - 差分更新・バックフィルの方針や品質チェックの取り扱い方針を実装指針として定義。

  - src/kabusys/data/etl.py
    - pipeline.ETLResult の再エクスポート。

  - src/kabusys/data/calendar_management.py
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 未取得時は曜日ベース（週末除外）をフォールバック。
    - calendar_update_job により J-Quants から差分取得 → 保存（バックフィル・健全性チェック含む）。
    - 最大探索日数やバックフィル、将来日付の健全性チェック等を実装。

- リサーチ（ファクター計算 / 特徴量探索）
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算（DuckDB SQL ベース）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算。
    - いずれも prices_daily / raw_financials のみ参照し、本番取引APIにアクセスしない設計。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（最小有効件数チェック）。
    - rank: 同順位は平均ランクにする安定したランク変換。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
    - research パッケージの公開を整理（__init__.py）。

- DuckDB を利用する前提の広範な DB 操作
  - 各モジュールで DuckDB 接続を引数に取り、SQL＋Python で処理を完結。
  - DuckDB 互換性のため executemany に空リストを渡さないなどのガードを実装。

### Changed
- （初版のため変更履歴なし）

### Fixed
- API 呼び出し失敗時やレスポンスパース失敗に対するフォールバックやログ出力を整備
  - news_nlp / regime_detector: OpenAI API の失敗（RateLimit/Connection/Timeout/5xx）でリトライ後、失敗時はスコアを 0.0 にフォールバックし処理継続。
  - DB 書き込み時の例外で ROLLBACK を試行し、ROLLBACK 自体の失敗は警告ログに記録。

### Security
- 環境変数の扱い
  - Settings.require 相当の実装で必須環境変数未設定時に明示的な ValueError を投げる。
  - .env の自動読み込み時に OS 環境変数を保護（protected set）し、誤った上書きを防止。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト用）。

### Notes / Implementation details
- Look-ahead バイアス対策: news_nlp/regime_detector/calculation いずれも内部で date.today() を参照せず、引数として与えられた target_date に基づいて厳密に過去データのみを参照する設計。
- テストフレンドリーな設計:
  - OpenAI 呼び出しはモジュール内でラップ（_call_openai_api）しており、unittest.mock.patch で差し替え可能。
  - API キーは引数注入も可能（api_key 引数）。空文字列は未設定扱いで ValueError。
- J-Quants クライアントへの依存は data.jquants_client 経由で抽象化されている（fetch/save の呼び出し先を想定）。
- DuckDB の日付型処理やリストバインドの互換性に配慮した実装（_to_date、executemany の空チェック等）。

### Removed
- （該当なし）

---

今後の更新候補（提案）
- strategy / execution / monitoring の実装追加（現状公開されているが詳細モジュールは未提示）。
- より詳細なテストケース・CI の追加（OpenAI モック、DuckDB テストフィクスチャ）。
- ドキュメント（使用例・API 仕様・テーブルスキーマ）の整備。