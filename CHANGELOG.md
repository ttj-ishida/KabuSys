CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。  

0.1.0 - 2026-03-29
------------------

初回リリース。本パッケージは日本株のデータ取得・ETL・研究（リサーチ）・AIベースのニュース解析と市場レジーム判定を包含する自動売買/研究支援ライブラリです。主な追加点は以下の通りです。

Added
- パッケージ基盤
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - 公開サブパッケージ: data, strategy, execution, monitoring。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数読み込み機能を実装。
  - プロジェクトルート探索ロジックを実装（.git または pyproject.toml を基準、CWD に依存しない）。
  - .env / .env.local の自動ロード（OS 環境変数を保護する protected 機構、.env.local は上書きモード）。
  - 複数の .env フォーマットに対応したパーサ（export プレフィックス、クォート文字列、インラインコメント処理、エスケープ対応）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供（J-Quants トークン、kabu API、Slack トークン、データベースパス、環境判定、ログレベルなど）。環境値の検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を実装。

- データ層（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - ETLResult データクラス（実行結果、品質問題、エラーメッセージ等を集約）。
    - 差分取得・バックフィル・品質チェックの設計を反映したユーティリティを実装。
    - DuckDB を利用することを前提としたテーブル存在チェック、最大日付取得ユーティリティ等を実装。
  - calendar_management モジュール
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - データがない場合の曜日ベースのフォールバック、データがまばらなケースへの一貫した動作設計。
    - 夜間バッチ更新 job（calendar_update_job）を実装（J-Quants から差分取得、バックフィル、健全性チェック）。
    - J-Quants クライアント連携（fetch/save の呼び出し）を想定。
  - ETL 公開インターフェース（kabusys.data.etl）で ETLResult を再エクスポート。

- 研究 / リサーチ（kabusys.research）
  - factor_research モジュール
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）などのファクター計算関数を実装。
    - DuckDB SQL を用いた計算（prices_daily / raw_financials のみ参照、外部 API へはアクセスしない設計）。
    - データ不足時の None 処理、結果を (date, code) ベースの dict リストで返すインターフェースを提供。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（Spearman の ρ）およびランク化ユーティリティ（rank）。
    - ファクター統計サマリー（factor_summary）を実装。
    - pandas 等の外部依存を用いず標準ライブラリ + DuckDB で実装。
  - research パッケージの再エクスポートを整理（主要関数群を __all__ で公開）。

- AI（kabusys.ai）
  - news_nlp モジュール
    - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（ai_score）を計算・ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウ計算（JST 基準で前日 15:00 ～ 当日 08:30 を UTC に変換）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄/回）、1 銘柄あたりの記事数と文字数上限（トリム）を実装。
    - JSON Mode を想定したレスポンス検証とパース（冗長テキストからの JSON 抽出を含む）、スコアのクリップ、未知銘柄コードの無視、部分成功時に既存スコアを保護するための DELETE → INSERT ロジックを実装。
    - ネットワーク/429/タイムアウト/5xx に対する指数バックオフリトライ（上限）とフェイルセーフ（失敗時はスキップして継続）。
    - テスト容易性: OpenAI 呼び出し箇所は差し替え可能（unittest.mock.patch でモック可能）。
  - regime_detector モジュール
    - ETF 1321（日経225 連動型）200 日 MA 乖離（重み 70%）と news_nlp によるマクロセンチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を算出・market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し（JSON Mode）、API の再試行とフェイルセーフ（API 失敗時 macro_sentiment=0.0）。
    - レジームスコア合成ロジックとしきい値閾値を実装。
    - テスト容易性: OpenAI 呼び出しを独立実装しており、news_nlp から内部関数を共有しない設計。

- 実装品質 / 設計上の注意点（共通）
  - DuckDB 前提の SQL 実装と互換性配慮（executemany の空リスト回避等）。
  - ルックアヘッドバイアス対策: datetime.today()/date.today() を解析ロジック内部で直接参照しない設計（target_date 引数ベース）。
  - ロギングおよび詳細な WARN/INFO/DEBUG メッセージを多数追加。
  - テスト容易性を考慮した差し替えポイント（API 呼び出しなど）の設計。
  - OpenAI / J-Quants / Kabu 関連の必須環境変数を Settings で管理（未設定時は ValueError を発生させる）。

Fixed
- エラー/例外処理の堅牢化
  - OpenAI API 呼び出し時の 5xx / レート制限 / タイムアウト等に対するリトライと、最終的に失敗した場合のフォールバック（スコア=0.0 など）を実装し、全体処理が例外で停止しないように設計。
  - DuckDB トランザクション周りでの例外発生時に ROLLBACK を試行し、ROLLBACK 自体の失敗も警告ログに記録するようにした。

Security
- 環境変数読み込み時に OS 環境を保護する仕組み（読み込み時の protected set による上書き回避）を追加。
- 必須 API キーは Settings で明示的に要求し、未設定時は ValueError を投げることで誤設定を早期に検出。

Notes / Usage
- 本リリースは DuckDB をデータストアに用いることを想定しています。
- OpenAI API（gpt-4o-mini）を利用する機能を含むため、OPENAI_API_KEY の設定が必要です（関数呼び出し時に api_key を明示的に渡すことも可能）。
- 外部 API 連携箇所（J-Quants / kabu API / Slack）は設定とトークンが必要です。Settings クラスからキーやパスを取得してください。
- ルックアヘッドバイアス防止のため、各スコアリング関数は target_date を引数として受け取ります。実行時には適切な基準日を指定してください。

今後の予定（想定）
- strategy / execution / monitoring の充実（発注ロジック・バックテスト・モニタリング連携）。
- モデル/プロンプトの改善、並列化やバッチ処理の最適化、より詳細な品質チェックの導入。
- CI 向けのモック・テスト群およびサンプルデータ/ドキュメントの整備。

----
（このCHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートは担当者により調整してください。）