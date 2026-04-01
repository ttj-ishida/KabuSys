Keep a Changelog
=================

すべての正当な変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」仕様に従ってバージョニングしています。

[Unreleased]
------------

（現時点で未リリースの差分はありません。）

[0.1.0] - 2026-04-01
--------------------

Added
- 初回公開: 基本的な日本株自動売買／リサーチ基盤を実装。
  - パッケージ構成:
    - kabusys.config: 環境変数／.env 読み込みおよび Settings クラスの提供。
    - kabusys.ai: ニュースNLP と市場レジーム判定モジュールの実装。
    - kabusys.research: ファクター計算・特徴量探索ユーティリティ群の実装。
    - kabusys.data: カレンダー管理、ETL パイプライン等のデータ基盤ユーティリティ。
  - パッケージ初期化にバージョン定義 __version__ = "0.1.0" を追加。

- 環境設定（src/kabusys/config.py）
  - プロジェクトルート検出: .git または pyproject.toml を起点に自動でプロジェクトルートを特定し .env をロード。
  - .env パーサ実装:
    - コメント行／空行の無視、export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い（クォート有無で挙動を区別）。
  - .env ロード順序: OS 環境 > .env.local > .env。既存 OS 環境は保護（protected）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラス:
    - J-Quants、kabu ステーション、Slack、データベースパス、監視閾値、実行環境（development/paper_trading/live）等のプロパティを提供。
    - env / log_level の検証を実装。
    - Path 型プロパティは expanduser 対応。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - score_news(conn, target_date, api_key=None):
    - 指定ウィンドウ（前日15:00 JST ～ 当日08:30 JST）に基づく記事集約（銘柄ごと、件数・文字数上限でトリム）。
    - 銘柄を最大 20 件ずつチャンクし、OpenAI (gpt-4o-mini, JSON モード) へバッチ送信。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ実装。
    - レスポンスの厳密な JSON バリデーションとスコア ±1.0 でのクリップ。
    - idempotent な DB 書き込み（対象コードの DELETE → INSERT）で部分失敗時の既存データ保護。
  - calc_news_window(target_date): JST→UTC のウィンドウ計算ユーティリティを提供。
  - テストしやすさのため、OpenAI 呼び出し箇所をパッチ可能に設計（_call_openai_api）。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - score_regime(conn, target_date, api_key=None):
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース（LLM 評価、重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - ma200_ratio は target_date 未満のデータのみを使用（ルックアヘッド防止）。
    - マクロニュースは raw_news からキーワードでフィルタして抽出、記事なしや API 失敗時は macro_sentiment=0.0 のフォールバック。
    - OpenAI への呼び出しは独立実装でモジュール結合を避ける。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。エラー時は ROLLBACK を試行し、失敗時は警告ログ出力。

- リサーチ（src/kabusys/research/*）
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials のデータからファクターを算出。
    - ATR、移動平均乖離、出来高・売買代金指標などを計算。
    - データ不足時には None を返す等の堅牢性。
  - feature_exploration:
    - calc_forward_returns: 任意のホライズンで将来リターンを一括取得（SQL の LEAD を利用）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を実装（有効レコード 3 件未満は None）。
    - rank: 同順位は平均ランクで処理（丸めによる ties 回避）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリだけで算出。
  - 依存軽量設計: pandas 等外部ライブラリに依存せず、DuckDB 接続を直接受け取る設計。

- データ基盤（src/kabusys/data/*）
  - calendar_management:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - market_calendar がない場合は曜日ベース（土日除外）でフォールバック。
    - カレンダー更新ジョブ calendar_update_job を実装（J-Quants API 経由で差分取得・バックフィル・健全性チェック）。
    - 最大探索日数やバックフィル日数などの安全策を導入。
  - pipeline / etl:
    - ETLResult データクラスを公開（取得数・保存数・品質チェック結果・エラー一覧等を包含）。
    - ETL の差分更新・品質チェックや id_token 注入によるテスト容易性を想定した設計方針を実装。
    - DuckDB におけるテーブル存在チェック等のユーティリティを提供。
  - jquants_client（参照）との連携を前提とした設計。

Changed
- 設計上の決定・方針を明確化:
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接用いない実装方針を採用（すべての関数は target_date を受け取る）。
  - OpenAI 呼び出し箇所はモジュール間でプライベート関数を共有せず、それぞれ独立にパッチ可能に実装（テストの独立性向上）。
  - DuckDB executemany の互換性を考慮した実装（空リスト渡し回避など）。

Fixed / Robustness
- DB トランザクション周り:
  - DB 書き込み時に例外発生した場合の ROLLBACK 処理を追加。ROLLBACK 自体が失敗した場合は警告ログで報告。
  - 部分失敗時に既存スコアを消さないため、対象コードを限定して DELETE→INSERT を行う実装で安全性を確保。
- OpenAI 呼び出しのフェイルセーフ:
  - 429・タイムアウト・接続エラー・5xx 等は指数バックオフでリトライ、最大試行回数消費後は警告ログを出しスコアをフォールバックして処理継続。

Security
- 環境変数の上書き防止:
  - OS 環境変数は protected として .env による上書きを防止するデフォルト挙動を採用。

Notes / Implementation details / Limitations
- 一部関数・処理は外部サービス（OpenAI, J-Quants, kabu API）に依存。実行時には該当 API キーやサービスの利用設定が必要。
  - OpenAI: OPENAI_API_KEY または各関数の api_key 引数で指定。
  - 環境設定は Settings クラスを通じて参照するのが想定。
- DuckDB を用いる前提で SQL を多用しており、DuckDB のバージョン依存（executemany の空リスト制約等）に配慮した実装がされている。
- ロギングと警告を多用し、障害時も処理継続する設計（フェイルセーフ）になっている。
- 現フェーズでは PBR・配当利回り等の一部バリューメトリクスは未実装。
- コードはテスト可能性を考慮しており、OpenAI 呼び出し等を unittest.mock.patch で差し替え可能。

Authors
- コードベースのコメント・実装から推測して CHANGELOG を作成しました。

---- 

（注）この CHANGELOG は提示されたソースコードの内容から推測して作成しています。実際のコミット履歴がある場合は commit 単位での詳細な変更ログを別途生成することを推奨します。