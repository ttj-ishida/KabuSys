CHANGELOG
=========

本ドキュメントは "Keep a Changelog" の形式に準拠しています。  
互換性のあるバージョニング（SemVer）を意図しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-03
--------------------

初回公開リリース。本リポジトリのコード構成と主要機能を基に以下を実装・提供します。

Added
- パッケージ基本構成
  - kabusys パッケージ（__version__ = 0.1.0）。 main export: data, strategy, execution, monitoring（strategy/execution/monitoring は参照名として公開）。
- 設定・環境変数管理 (kabusys.config)
  - .env ファイル（.env/.env.local）からの自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - 独自の .env パーサ（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応）。
  - override 保護機能: OS 環境変数を保護する protected セットを使用した上書き制御。
  - Settings クラスを提供し、J-Quants / kabu ステーション / LINE / DB / 監視 / システム関連設定をプロパティ経由で取得。
  - 必須環境変数のチェック（_require）、KABUSYS_ENV と LOG_LEVEL のバリデーション、便利プロパティ（is_live/is_paper/is_dev）。
  - デフォルト値（例: DUCKDB_PATH= data/kabusys.duckdb 等）を設定。

- AI 関連 (kabusys.ai)
  - news_nlp モジュール（kabusys.ai.news_nlp）
    - raw_news と news_symbols から所定ウィンドウのニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）で銘柄別センチメントを算出して ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（JST 基準、UTC に変換）と記事トリム（最大記事数・最大文字数）。
    - バッチ処理（最大 20 銘柄 / API コール）・リトライ（429・ネットワーク断・タイムアウト・5xx に対して指数バックオフ）・レスポンス検証（JSON 抽出、結果スキーマ検証、数値チェック・±1.0 でクリップ）。
    - テスト容易性のため OpenAI 呼び出し箇所をパッチ可能に実装。
  - regime_detector モジュール（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - マクロキーワードによるニュース抽出、LLM 呼び出し（gpt-4o-mini）とリトライ戦略、フェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - レジーム判定結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアス対策（内部で date.today()/datetime.today() を参照しない設計）。
    - OpenAI クライアント呼び出しはパッチ置換可能。

- データ処理・ETL・カレンダー (kabusys.data)
  - ETL インターフェース (kabusys.data.etl) と ETLResult（kabusys.data.pipeline.ETLResult の再エクスポート）。
  - pipeline モジュール（kabusys.data.pipeline）
    - ETLResult データクラス（取得数・保存数・品質チェック結果・エラー等を格納）。
    - 差分更新・バックフィル・品質チェックの方針を反映したユーティリティ（テーブル有無判定、最大日付取得等の下地実装）。
  - calendar_management モジュール（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定とユーティリティ関数（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データ優先で、未登録日は曜日ベースのフォールバック（週末判定）。
    - calendar_update_job: J-Quants API からカレンダー差分を取得し market_calendar を冪等に更新（バックフィル・健全性チェック含む）。
    - DuckDB を前提とした実装（_to_date 等の変換ユーティリティ含む）。

- リサーチ（ファクター計算・特徴量探索） (kabusys.research)
  - factor_research モジュール
    - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比）、バリュー（PER/ROE）を計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - DuckDB SQL とウィンドウ関数を活用し、営業日ベースでのスキャン範囲やカウントによる欠損ハンドリングを実装。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns、複数ホライズンを一度に取得）、IC（スピアマン順位相関）計算（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）。
    - pandas 等に依存せず標準ライブラリで実装。
  - research パッケージの __all__ で主要APIを公開。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- .env の自動ロードにおいて、既存の OS 環境変数は protected として上書きされない挙動を採用。テストで自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。

Notes / Usage / Migration
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
  - KABU_API_PASSWORD（kabuステーション API 用）
  - OPENAI_API_KEY（AI モジュールの利用時）
  - .env.example を参考に .env を用意すること（設定未完了時は Settings が例外を投げる箇所あり）。
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- OpenAI 呼び出し箇所はテスト用にパッチ差し替え可能（kabusys.ai.news_nlp._call_openai_api 等）。
- DuckDB の executemany に関する注意（空リストは不可）や、レスポンスパース失敗時のフォールバック設計など、実運用での堅牢性を考慮した実装が行われている。
- market_calendar が未取得の環境でも曜日フォールバックにより基本機能は利用可能。

Known issues / TODO
- strategy / execution / monitoring パッケージは __all__ で公開されているが、この差分では内部実装のファイルが提示されていない（将来的に売買ロジックや実行エンジンが追加される想定）。
- 一部の外部 API 呼び出し（J-Quants / OpenAI）はネットワークに依存するため、運用時は API キー管理・レート制限対策を行ってください。

Authors
- コードベース（本リリース）に基づき CHANGELOG を作成

-----

（注）本 CHANGELOG は提供されたコードスナップショットの内容をもとに推測して作成しています。追加の変更履歴や過去バージョン情報がある場合は、その差分を反映して更新してください。