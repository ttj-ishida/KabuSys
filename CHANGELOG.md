Keep a Changelog
=================

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは "Keep a Changelog" の規約に従います。

フォーマット: https://keepachangelog.com/ (日本語)

[Unreleased]

0.1.0 - 2026-03-27
------------------

初回リリース。日本株自動売買システム "KabuSys" の基礎モジュール群を実装しました。
主な追加点・設計方針は以下の通りです。

Added
- パッケージ基本情報
  - kabusys パッケージ初期化。__version__ = "0.1.0"、主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定
  - kabusys.config: .env ファイルおよび環境変数の読み込み・管理機能を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を上位ディレクトリから探索）。
    - 自動ロード順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化。
    - .env パーサを独自実装（export 形式、クォート／エスケープ、インラインコメントの取り扱いに対応）。
    - Settings クラスを提供し、各種必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）やパス設定（DUCKDB_PATH, SQLITE_PATH）、環境種別（development/paper_trading/live）とログレベル検証をラップ。

- AI モジュール
  - kabusys.ai.news_nlp:
    - raw_news / news_symbols から記事を集約し、OpenAI（gpt-4o-mini）により銘柄ごとのセンチメント（ai_score）を算出して ai_scores に書き込む処理を実装。
    - タイムウィンドウ計算（JST基準）と記事トリム（最大件数／文字数）を実装。
    - バッチ処理（デフォルト 20 銘柄/チャンク）、JSON Mode レスポンス検証、リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を実装。
    - レスポンスバリデーション：results 配列・銘柄コード整合・スコア数値検証・±1.0 クリップ。
    - DB 書き込みは部分置換（該当コードのみ DELETE → INSERT）で冪等性と部分失敗保護を実現。
    - テスト容易性のため _call_openai_api を patch 可能。

  - kabusys.ai.regime_detector:
    - ETF 1321（225連動）の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - news_nlp の calc_news_window を利用してニュースウィンドウを決定し、OpenAI（gpt-4o-mini）でマクロセンチメントを算出。
    - API リトライ/バックオフとフェイルセーフ（失敗時 macro_sentiment=0.0）を実装。
    - 計算結果を market_regime テーブルへトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等書き込み。
    - 日付の扱いはルックアヘッドバイアス対策済み（datetime.today()/date.today() を直接参照しない）。

- データプラットフォーム（Data）
  - kabusys.data.calendar_management:
    - JPX マーケットカレンダー管理、営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - market_calendar の有無に応じて DB 値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、保存）。
  - kabusys.data.pipeline / etl:
    - ETLResult データクラスを公開（ETL 実行結果の集約：取得数、保存数、品質問題、エラー等）。
    - ETL パイプライン設計（差分更新、バックフィル、品質チェックの方針）を実装（jquants_client / quality を利用）。

- リサーチ（Research）
  - kabusys.research.factor_research:
    - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB データから計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 欠損／データ不足時の扱い（None）を明示。
  - kabusys.research.feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、各種統計サマリー（factor_summary）を実装。
    - pandas 等外部依存を避け、標準ライブラリと DuckDB SQL で実装。

Changed
- 設計方針（全体）
  - ルックアヘッドバイアス防止のため、全ての日付処理で datetime.today()/date.today() を直接参照しないよう設計（関数の引数で基準日を渡す方式）。
  - OpenAI API 呼び出しに対して堅牢なエラーハンドリング（リトライ、5xx 分岐、フェイルセーフ）を標準実装。
  - DuckDB への書き込みは冪等性・部分失敗保護を重視（DELETE→INSERT、executemany の空リスト回避等）。

Fixed
- N/A（初回リリースのため既存バグ修正は無し）

Security
- 環境変数の扱いに注意:
  - Settings._require により必須環境変数未設定時は ValueError を送出し明示的に失敗させる。
  - .env 自動ロード時に OS の既存環境変数を保護する仕組み（protected set）を導入。

Notes / Developer hints
- OpenAI API
  - gpt-4o-mini を JSON mode（response_format={"type": "json_object"}）で使用する設計。テスト時は各モジュールの _call_openai_api を patch して外部呼び出しをモックできます。
  - API キーは関数引数で注入可能。None の場合は環境変数 OPENAI_API_KEY を参照します。

- DuckDB
  - 一部処理で executemany に空リストを渡すと互換性問題が生じるため、空リストチェックを入れています（DuckDB 0.10 対応）。

- ETL / calendar_update_job
  - calendar_update_job は最新チェック・バックフィル・健全性チェックを行い、J-Quants クライアント呼び出し失敗時は 0 を返す安全設計。

Breaking Changes
- なし（初回リリース）

今後の予定（抜粋）
- strategy / execution / monitoring サブパッケージの実装と統合テスト
- 継続的な品質チェック拡張（quality モジュールの強化）
- モデル改善（LLM プロンプト、バッチ戦略の最適化）

Acknowledgements
- 本実装は J-Quants API、kabuステーション API、OpenAI API 等との連携を前提とした構成になっています。実行にはそれぞれの認証情報・外部サービスが必要です。

-----

注: 本 CHANGELOG は、提示されたコードベースの内容・ドキュメント文字列から推測して作成しています。実際のリリースノート作成時は追加の変更点・既知の問題・依存関係情報を追記してください。