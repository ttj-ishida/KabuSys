CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従い、セマンティック バージョニング (SEMVER) を採用しています。
https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-03
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ表記: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 環境変数 / 設定管理 (kabusys.config)
  - .env/.env.local 自動ロード機能を実装（プロジェクトルート判定: .git / pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサを独自実装。export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを考慮。
  - OS 環境変数を保護する protected 機能（.env.local での上書き制御）。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム設定等のプロパティを公開。
  - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）を実装。
  - 必須環境変数未設定時の明確なエラーメッセージ（_require）。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - score_news(conn, target_date, api_key=None)：raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores テーブルへ書き込み。
    - ニュース収集ウィンドウを JST 基準で定義（前日 15:00 JST ～ 当日 08:30 JST、UTC に変換）。
    - バッチ処理（最大 20 銘柄/リクエスト）、1銘柄あたりの記事数・文字数上限のトリム実装。
    - JSON Mode の応答を想定した厳格なバリデーションと復元ロジック（余計な前後テキストの抽出対応）。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。
    - API 呼び出し部分を _call_openai_api で抽象化し、テスト時の差し替えを容易化。
    - DuckDB に対する冪等書き込み（DELETE→INSERT）および DuckDB executemany の空リスト制約を考慮。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - score_regime(conn, target_date, api_key=None)：ETF(1321) の 200 日移動平均乖離 (重み 70%) とマクロニュース LLM センチメント (重み 30%) を合成して日次の市場レジーム（bull/neutral/bear）を market_regime テーブルへ保存。
    - ma200_ratio の計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。
    - マクロニュース抽出はニュースタイトルのキーワードマッチ（リスト化されたマクロキーワード）で行い、記事がなければ LLM コールをスキップして macro_sentiment=0.0 を採用（フェイルセーフ）。
    - OpenAI 呼び出し時のリトライ、JSON パースの堅牢化、API 失敗時のフォールバックを実装。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の順で行い、例外時は ROLLBACK を試行して上位へ伝播。

- データプラットフォーム / ETL (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを用いた営業日判定 API を提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にカレンダーデータがない場合は曜日（平日）ベースでフォールバックする一貫したロジックを実装。
    - calendar_update_job により J-Quants からの差分取得・バックフィル・保存（jq.fetch_market_calendar / jq.save_market_calendar を利用）を実装。保存は冪等性を考慮。
    - 最大探索日数や健全性チェック（未来日付の異常検出）等の保護処理を実装。

  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラー等を格納）。
    - ETL の差分取得方針、バックフィル、品質チェックの設計方針を実装に反映（jquants_client と quality モジュールを利用する想定）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得などの関数を提供。

- リサーチ / ファクター (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。
    - DuckDB を用いた SQL ベースの実装で外部 API にアクセスしない設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを一度のクエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位は平均ランクとするランク関数実装（丸めで ties を検出）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。
  - research パッケージで必要な関数を __all__ で再エクスポート。

- 共通設計/運用上の配慮
  - すべての分析・スコアリング関数は datetime.today()/date.today() を内部で直接参照しない設計（ルックアヘッドバイアス防止）。
  - DuckDB を主要な永続化層として採用し、SQL と Python を組み合わせた実装。
  - API 呼び出し失敗時はフェイルセーフ（スキップ、デフォルト値）で処理を継続する方針を採用。
  - テスト容易性のために外部 API 呼び出しは _call_openai_api のように差し替え可能に実装。

Changed
- 初版のため該当なし

Fixed
- 初版のため該当なし

Security
- OpenAI API キーおよび各種トークンは Settings 経由で扱うことを想定しており、明示的に未設定の場合は ValueError を発生させる等の保護を導入。

Notes / Migration
- OpenAI を利用する関数 (score_news, score_regime) は api_key 引数または環境変数 OPENAI_API_KEY が必須。未設定時は ValueError を送出します。
- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。パッケージを別場所で利用する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを抑制し、明示的に環境変数を注入してください。
- DuckDB executemany に空リストを渡すとエラーとなるバージョンへ配慮した実装（空チェックあり）。

今後の予定（参考）
- モニタリング / 実行（execution, monitoring）モジュールの具体的な実装と監視用 UI /アラートの統合
- ETL のより詳細な品質チェックルールと自動修復フローの追加
- モデル精度検証用のシミュレーション・バックテスト機能の追加

---