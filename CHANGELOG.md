Keep a Changelog準拠 — KabuSys

すべての変更は semver に従って管理されています。  
このファイルはリポジトリのコードから推測して作成した初期リリース向けの変更履歴です。

v0.1.0 — 2026-03-29
================================

Added
-----
- パッケージ基盤
  - kabusys パッケージの公開（__version__ = 0.1.0）。公開サブパッケージ: data, research, ai, execution, strategy, monitoring（__all__ に基づく）。
- 設定/環境変数管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルの堅牢なパーサを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの取り扱い等）。
  - OS 環境変数を保護する protected 機構（.env.local は既存の OS 環境変数を上書きしない等）。
  - Settings クラス実装：J-Quants / kabuステーション / Slack / DB パス等のプロパティ提供。環境変数の必須チェック（_require）と値検証（KABUSYS_ENV, LOG_LEVEL の妥当性チェック）。
  - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）を提供。
- AI ユーティリティ (kabusys.ai)
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI Chat (gpt-4o-mini / JSON mode) で銘柄ごとのセンチメント（-1.0〜1.0）を評価。
    - バッチ処理（最大20銘柄/コール）、1銘柄あたり記事数・文字数上限でトークン肥大化を抑制。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）で指数バックオフ、レスポンスの厳密なバリデーションとスコアのクリップ処理。
    - DuckDB への冪等的書き込み（対象コードのみ DELETE → INSERT）を実装。部分失敗時に既存データを保護。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（内部関数 _call_openai_api を patch できる）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定。
    - マクロ記事の抽出にはマクロキーワードリストを使用。記事がない場合は LLM 呼び出しを行わず macro_sentiment=0.0 を採用。
    - OpenAI 呼び出しに対してリトライ/バックオフ・フェイルセーフ（API エラー時は macro_sentiment=0.0）を実装。
    - 結果を market_regime テーブルへ冪等的に保存（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
- データ基盤 (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルに基づく営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（週末の除外）を採用。DB 登録が不完全な場合でも一貫した判定を行う設計。
    - JPX カレンダーの夜間差分更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得、バックフィル / 健全性チェックを行い冪等保存）。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを導入して ETL 結果（取得数、保存数、品質問題、エラー等）を一元管理。
    - 差分取得・バックフィル・品質チェック・冪等保存（jquants_client の save_* 利用）を実現するための基盤を実装（設計に関する注記あり）。
    - DuckDB の互換性考慮（executemany に空リストを渡さない等）を反映。
  - jquants_client / quality など外部モジュール（参照）の利用を想定した実装。
- リサーチ機能 (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）等を DuckDB の SQL と Python 組合せで計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 過不足データに対する None の取り扱いやログ出力。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（スピアマンランク相関）計算（calc_ic）、ランク化ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず純粋に標準ライブラリ + DuckDB で実装。
- 実装/設計上の注意点（ドキュメント）
  - ルックアヘッドバイアス回避の方針を各所で採用（datetime.today()/date.today() を直接参照しない、クエリに date < target_date 等の排他条件を使用）。
  - OpenAI リクエストは JSON mode（response_format={"type":"json_object"}）を利用し、厳密な JSON パースとフォールバック処理を用意。
  - 外部 API 失敗時のフェイルセーフ：多くの箇所で API 失敗は全体処理を停止させずデフォルト値／スキップで継続する設計。

Changed
-------
- 初版リリースのため該当なし（初回導入）。

Fixed
-----
- 初版リリースのため該当なし（初回導入）。

Removed
-------
- 初版リリースのため該当なし（初回導入）。

Security
--------
- 初回リリースのため該当なし。API キーやトークンは環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, SLACK_BOT_TOKEN など）で扱うことを想定。機密情報は .env ファイル / OS 環境変数で管理。

既知の制限・注意事項
-------------------
- OpenAI を利用する一連の処理は外部 API に依存するため、実行環境で OPENAI_API_KEY（または関数引数で api_key）を設定する必要があります。設定がない場合は ValueError を送出します（一部処理は記事が無ければ API 呼び出しを行わず 0.0 を採用する等のフェイルセーフあり）。
- DuckDB バインド/バージョン差異（例: executemany に空リストを渡せない等）をコード内で考慮しているため、古い/新しい DuckDB での挙動差に注意してください。
- 本コードベースはデータ取得・解析・スコアリング等のロジックを提供しますが、発注やライブ取引（kabu ステーション等実際の注文発行）は本バージョンで実行しない（execution モジュールはエクスポートに含まれるが、この変更履歴は実装の存在を示すに留めます）。

今後の予定（想定）
-----------------
- モニタリング/実行モジュールの拡充（Slack 通知や実行パラメータ管理等）。
- テストカバレッジの拡大と CI ワークフロー整備。
- J-Quants / kabu API クライアントのさらなる堅牢化とリトライ戦略の一貫化。

この CHANGELOG はコード内容から推測して作成したものです。実際のリリースノート作成時はコミット履歴やリリース方針に従って追記・修正してください。