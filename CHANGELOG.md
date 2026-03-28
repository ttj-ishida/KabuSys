CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

- （なし）


[0.1.0] - 2026-03-28
--------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージ概要: 日本株の自動売買・リサーチ・データ基盤向けユーティリティ群を提供。

- 環境設定 / 設定管理
  - kabusys.config:
    - .env / .env.local ファイルおよび OS 環境変数からの設定自動読み込み機能を実装。
    - プロジェクトルート探索は __file__ を基点に .git または pyproject.toml を検出（CWD 非依存）。
    - .env パーサは export 形式、クォート、エスケープ、コメント処理等に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグを追加（テスト支援）。
    - Settings クラスを公開 (settings): 必須キー取得時は例外送出、env/log level のバリデーション、DB パスの Path 化などを実装。

- AI（LLM）関連
  - kabusys.ai.news_nlp:
    - score_news(conn, target_date, api_key=None): ニュース記事を銘柄毎に集約して OpenAI に送信し、センチメントスコアを ai_scores テーブルへ書き込むバッチ処理を実装。
    - タイムウィンドウ計算（JST基準→UTC変換）、記事トリム（記事数/文字数上限）、バッチ（最大20銘柄）処理、JSON mode レスポンスバリデーション、スコア ±1.0 クリップ、部分書き換え（DELETE→INSERT）による冪等化を実装。
    - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで処理。テスト容易化のため _call_openai_api を patch 可能に設計。
  - kabusys.ai.regime_detector:
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離 (重み 70%) とマクロニュースの LLM センチメント (重み 30%) を合成して market_regime テーブルへ保存。
    - ma200_ratio 計算、マクロキーワードによる raw_news フィルタ、OpenAI 呼び出し、失敗時のフェイルセーフ（macro_sentiment=0.0）、冪等な DB 書き込みを実装。
    - モデル: gpt-4o-mini を想定。API のステータスコードに応じたリトライ判定を実装。

- データ基盤（ETL / カレンダー）
  - kabusys.data.pipeline / kabusys.data.etl:
    - ETLResult データクラスを公開。ETL 実行結果 (取得数・保存数・品質問題・エラー) を集約し to_dict メソッドで整形可能。
    - 差分更新・バックフィル・品質チェックの方針をコード上に実装（J-Quants クライアントを介した取得・idempotent 保存を想定）。
  - kabusys.data.calendar_management:
    - JPX カレンダー管理（market_calendar）および営業日判定ユーティリティを実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - market_calendar 未取得時は曜日ベース（土日非営業）でフォールバックする一貫した挙動を実装。
    - calendar_update_job による夜間差分取得・バックフィル・健全性チェック・J-Quants クライアント経由の保存ロジックを実装。
    - 最大探索日数やバックフィル日数等の安全パラメータを定義。

- リサーチ / ファクター
  - kabusys.research.factor_research:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility(conn, target_date): 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): raw_financials を使用した PER / ROE を計算（EPS 欠損や 0 の取り扱いを考慮）。
    - DuckDB SQL を活用して効率的に計算。データ不足時は None を返す挙動を明記。
  - kabusys.research.feature_exploration:
    - calc_forward_returns(conn, target_date, horizons): 指定ホライズン（営業日）ごとの将来リターンを一括取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を実装（同順位は平均ランク）。
    - rank(values): 同順位処理（平均ランク）を含むランク変換ユーティリティ。
    - factor_summary(records, columns): count/mean/std/min/max/median の基本統計サマリーを算出。
  - kabusys.research.__init__ にて主要関数群を再エクスポート。

- 共通 / 実装設計上の注意点（ドキュメント化）
  - すべての解析・スコアリング関数で datetime.today() や date.today() を直接参照しない方針（ルックアヘッドバイアス回避）。target_date を明示的に受け取る設計。
  - DuckDB を主要なデータストアとして想定。SQL + Python の組合せで処理。
  - DB 書き込みは冪等性を意識（DELETE→INSERT、ON CONFLICT を想定）し、トランザクション（BEGIN/COMMIT/ROLLBACK）を使用して一貫性を確保。
  - OpenAI 呼び出し部分は外部依存としつつ、応答パース失敗時はフェイルセーフ（スコア 0 やスキップ）で継続する設計。
  - テスト容易性: 環境読み込みの無効化フラグ、OpenAI 呼び出しの差し替えポイント（_call_openai_api）を用意。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 実装上の制約
- OpenAI SDK/API の互換性（status_code の有無等）を考慮した defensive な実装を行っています。将来の SDK 変更時はエラー判定ロジックの見直しが必要です。
- DuckDB のバージョン依存（executemany の空リスト制約など）に対応するため、空チェックや個別 DELETE を採用しています。環境差異がある場合は動作確認を推奨します。
- J-Quants クライアント（kabusys.data.jquants_client）はコード内で参照していますが、外部依存実装により動作が異なる可能性があります。API キーやエンドポイント設定は Settings を使用して注入してください。

--- 

今後のリリースで追加したいこと（TODO）
- ai モジュールでのモデル切替やロギング強化（レスポンスメタ情報の保存など）。
- ai_scores / market_regime のスキーマバージョン管理・マイグレーションユーティリティ。
- ETL のスケジューリング統合サポート（ジョブ制御・監視）。
- 単体テスト・統合テストの充実（モッククライアントを用いた CI 実行）。