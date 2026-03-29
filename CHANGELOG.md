CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマットや記載方針の詳細は https://keepachangelog.com/ja/ を参照してください。

なお、本 CHANGELOG はコードベースの内容から機能・設計意図を推測して作成しています。

[Unreleased]
------------

- 現時点で未リリースの変更はありません。

[0.1.0] - 2026-03-29
-------------------

初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。
主要な機能群・モジュール、設計上の注意点、API の振る舞いを以下にまとめます。

Added
- パッケージ初期化
  - kabusys パッケージの初期化（__version__ = "0.1.0"）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に設定。

- 環境設定 / ロード
  - kabusys.config モジュールを追加。
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動ロードする仕組みを実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env 解析は export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - OS 環境変数を保護するため protected セットを用いた上書き制御を実装。
    - Settings クラスを追加し、アプリケーション設定（J-Quants / kabu / Slack / DB パス / 環境モード / ログレベル等）をプロパティ経由で取得可能。
    - 環境変数の必須チェックで未設定時は ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（有効な値セットを定義）。

- AI モジュール
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を用いたニュースの銘柄別センチメントスコア算出機能を実装。
    - OpenAI（gpt-4o-mini）を JSON Mode で呼び出し、結果を ai_scores テーブルへ書き込み。
    - タイムウィンドウは target_date に対して前日 15:00 JST ～ 当日 08:30 JST（UTC に変換）を使用（ルックアヘッドバイアス対策）。
    - 1チャンクあたり最大20銘柄、記事長トリム、最大記事数制限を実装。
    - リトライ（429/ネットワーク/タイムアウト/5xx）、指数バックオフを実装。API 失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - レスポンス検証（JSON 抽出、results 配列、code の検証、スコア数値チェック、±1.0 クリップ）を実装。
    - テスト容易性のため _call_openai_api をモック差し替え可能に設計。
    - DuckDB への置換（DELETE → INSERT）を書き込み単位として実装し、部分失敗時に既存スコアを保護。

  - kabusys.ai.regime_detector
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出はニュースタイトルのキーワードフィルタリングを実施し、存在する場合にのみ LLM 呼び出しを行う（記事無しなら LLM コールをスキップして macro_sentiment=0.0）。
    - LLM 呼び出しは gpt-4o-mini、JSON モード、リトライ・バックオフ・フェイルセーフ（全リトライ消費時は macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止のため、DB クエリは target_date 未満のみを参照し、datetime.today() を直接使用しない。

- Data モジュール
  - kabusys.data.calendar_management
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB にカレンダーがない場合は曜日ベース（平日のみ営業）でフォールバック。
    - next/prev/get_trading_days は DB 値優先・未登録日は曜日フォールバックで一貫した結果を返す実装。
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、保存）。
    - _MAX_SEARCH_DAYS, _CALENDAR_LOOKAHEAD_DAYS, _BACKFILL_DAYS 等の運用向け定数を定義。

  - kabusys.data.pipeline / etl / quality 関連（ETL の土台実装）
    - ETLResult データクラスを提供（ETL の取得件数・保存件数・品質チェック結果・エラー等を集約）。
    - 差分取得、backfill、品質チェック結果を保持するためのインターフェースとユーティリティ関数を追加。
    - DuckDB のテーブル存在チェック、最大日付取得等のユーティリティを実装。
    - ETL は J-Quants クライアント（jquants_client）を利用して idempotent 保存を前提に設計。
    - DuckDB executemany の仕様（空リスト不可）に配慮した書き込み処理を実装。

- Research モジュール
  - kabusys.research.factor_research
    - モメンタム（1/3/6 ヶ月）、200日移動平均乖離、ATR（20日）、流動性（20日平均売買代金・出来高比）などのファクター計算を実装。
    - raw_financials から PER / ROE を算出するバリューファクターを実装（EPS がゼロ/欠損の際の取り扱いを明示）。
    - DuckDB を用いた SQL ベース実装で、外部 API には依存しない。
    - データ不足時は None を返す設計。

  - kabusys.research.feature_exploration
    - 将来リターンの計算（任意ホライズン）、IC（Spearman の ρ）計算、ランク変換、ファクター統計サマリを実装。
    - pandas 等に依存しない純標準ライブラリ実装。
    - rank() は同順位を平均ランクで扱い、丸め処理で浮動小数の ties 検出漏れを防止。
    - calc_forward_returns はホライズンの検証（正の整数で <= 252）を実施。

- その他
  - 多数のロギング（logger）を追加し、処理の進捗・警告・失敗ケースを記録。
  - 各所でルックアヘッドバイアス防止設計を徹底（datetime.today()/date.today() の不適切参照を排除）。
  - DuckDB を前提としたトランザクション（BEGIN/COMMIT/ROLLBACK）処理を多くの書き込み処理で採用し、失敗時の整合性を確保。

Changed
- N/A（初回リリースのため変更履歴はなし）。

Fixed
- N/A（初回リリースのため修正履歴はなし）。

Deprecated
- N/A

Removed
- N/A

Security
- セキュリティ考慮点（実装上の注意）
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を投げるため、運用環境でのキー管理が必要。
  - .env 自動ロードはプロジェクトルート検出に依存する。自動ロードを抑制する環境変数を提供（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - OS 環境変数の保護のため、.env 読み込み時に既存 os.environ のキーを保護する仕組みを導入。

Notes / Migration
- .env の自動読み込み
  - パッケージはプロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動で読み込みます。CI/テスト環境で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI API の利用
  - AI モジュールは gpt-4o-mini（JSON mode）を想定しています。API レスポンスの形式は厳密な JSON を期待しており、レスポンスパースに失敗した場合はフェイルセーフ動作（スコア 0 またはチャンクスキップ）になります。
  - テストでは kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api をモックすることで外部依存を排除できます。

- DuckDB とトランザクション
  - 書き込み処理は BEGIN / DELETE / INSERT / COMMIT の冪等パターンを多用しています。例外発生時は ROLLBACK を試行し、ROLLBACK 自体の失敗は警告ログに記録します。
  - DuckDB executemany は空リストを受け付けないバージョンの互換性へ配慮した処理を行っています（書き込みパラメータが空の場合は実行をスキップ）。

- ルックアヘッドバイアス対策
  - 全ての分析/AI スコアリング処理は target_date を明示的に受け取り、過去データのみを参照するよう設計されています。運用時に誤って現在時刻依存のロジックを組み込まないよう注意してください。

Contributors
- 本リリースのコードから推測して作成（自動生成ドキュメントのため実際の貢献者情報はソース管理履歴を参照してください）。

---
この CHANGELOG はソースコードの内容から想定される仕様・振る舞いに基づいて作成しています。実際のリリースノート作成時にはコミット履歴やリリース差分に基づいて適宜調整してください。